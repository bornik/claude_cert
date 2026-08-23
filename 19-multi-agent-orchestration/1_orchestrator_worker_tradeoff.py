"""
EXAMPLE 1: Multi-Agent Orchestration as a Deliberate Tradeoff

An orchestrator-worker pattern is a hiring decision, not a free upgrade:
a lead agent decomposes a task, several subagents research their slice
in parallel (each spending its own tokens in its own context), and the
lead compiles their results.

    async def orchestrate(task):
        plan = await lead.plan(task)              # lead decomposes
        results = await gather(*[                 # subagents run in parallel
            worker.run(subtask) for subtask in plan.subtasks
        ])
        return await lead.synthesize(results)     # lead compiles

Anthropic's own research system reported roughly 15x the tokens of a
single chat turn for a lead + 4-subagent setup, because you're paying for
N+2 contexts (plan, N workers, synthesis) instead of one. This script
makes that multiplier concrete with real API calls and measured token
counts, across four demos:

  1. GENUINE PARALLEL TASK  — a broad survey question that actually splits
     into independent subtopics. Single agent vs. orchestrator-worker,
     same model throughout, isolating the architecture's cost from any
     model-choice decision.
  2. WASTED MULTIPLIER      — the same architecture forced onto a single
     factual lookup that never needed decomposition. Same cost shape,
     no quality gained for it.
  3. MODEL TIERING          — the genuine task again, comparing an
     all-top-tier assignment against a stronger lead + cheaper workers,
     to show the multiplier can be reduced without touching the
     coordination-sensitive calls (planning, synthesis).
  4. FAILURE HANDLING UNDER FAN-OUT — one subagent simulates hitting a
     transient rate limit. A naive gather() has no per-task handling and
     the whole compilation step never runs, even though the other
     subagents already succeeded. A resilient version retries with
     backoff and falls back to a placeholder finding, so the lead can
     still synthesize from partial results.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import PRICING, print_usage

load_dotenv()

LEAD_MODEL = "claude-sonnet-5"
WORKER_MODEL = "claude-haiku-4-5"
SINGLE_AGENT_MODEL = "claude-haiku-4-5"

RESEARCH_TASK = (
    "Survey the operational tradeoffs of four backend scaling techniques "
    "for a growing API: response caching, message queues for async "
    "background work, database read replicas, and per-client rate "
    "limiting."
)

TRIVIAL_TASK = "What year was HTTP/2 published as an RFC?"

# Fixed decomposition used by demo 4, so the failure-handling demo isn't
# also paying for (and depending on) a live planning call.
FIXED_SUBTOPICS = [
    "What operational tradeoff does response caching introduce for a growing API?",
    "What operational tradeoff do message queues introduce for async background work?",
    "What operational tradeoff do database read replicas introduce?",
    "What operational tradeoff does per-client rate limiting introduce?",
]


class SimulatedRateLimitError(Exception):
    """Stands in for a real 429 from a subagent's own tool/search call —
    injected in code so the failure is deterministic and reproducible,
    the same way 04-tool-use-schema-design/5_error_handling.py hardcodes
    a failed tool result instead of relying on one happening for real."""


def strip_fences(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = next(
        ((i, o) for prefix, (i, o) in PRICING.items() if model.startswith(prefix)),
        (0.0, 0.0),
    )
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def summarize(meter: list) -> tuple:
    total_tokens = sum(m["input"] + m["output"] for m in meter)
    total_cost = sum(estimate_cost(m["model"], m["input"], m["output"]) for m in meter)
    return total_tokens, total_cost


# ---------------------------------------------------------------------------
# The orchestrator-worker primitives — plan, run, synthesize
# ---------------------------------------------------------------------------

async def call_model(client: AsyncAnthropic, prompt: str, *, system: str, model: str, max_tokens: int) -> tuple:
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    print_usage(response, model=model)
    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    usage = {"model": model, "input": response.usage.input_tokens, "output": response.usage.output_tokens}
    return text, usage


async def lead_plan(client: AsyncAnthropic, task: str, model: str) -> tuple:
    system = (
        "Decompose the research task into exactly 4 independent subtopics "
        "that could each be researched in parallel without depending on "
        "each other's findings. A subagent will receive ONLY the subtopic "
        "question you write, with no other context — so each question "
        "must be SELF-CONTAINED, naming the specific technique or topic it "
        "covers. Never use a pronoun like 'these' or 'the four' that "
        "assumes the reader has seen the other subtopics or the original "
        "task. Reply with ONLY a JSON array of 4 such questions, no prose, "
        "no markdown fences."
    )
    text, usage = await call_model(client, task, system=system, model=model, max_tokens=200)
    try:
        subtasks = json.loads(strip_fences(text))
        assert isinstance(subtasks, list) and subtasks
    except (json.JSONDecodeError, AssertionError):
        subtasks = FIXED_SUBTOPICS
    return subtasks, usage


async def worker_run(client: AsyncAnthropic, subtask: str, model: str) -> tuple:
    system = "Answer the research question in 2-3 sentences, focused on the operational tradeoff."
    return await call_model(client, subtask, system=system, model=model, max_tokens=150)


async def worker_run_grounded(client: AsyncAnthropic, task: str, subtask: str, model: str) -> tuple:
    """Same as worker_run, but grounds the subagent in the overall task —
    a subagent that gets only a decomposed question, with no view of what
    it's a PART of, can silently answer the wrong question (see the
    module README's note on demo 1's ungrounded run)."""
    system = "Answer the research question in 2-3 sentences, focused on the operational tradeoff."
    prompt = f"This question is one part of researching: {task}\n\nSpecific question: {subtask}"
    return await call_model(client, prompt, system=system, model=model, max_tokens=150)


async def lead_synthesize(client: AsyncAnthropic, task: str, findings: list, model: str) -> tuple:
    prompt = f"Original task: {task}\n\nFindings from parallel research:\n" + "\n".join(f"- {f}" for f in findings)
    system = "Synthesize these findings into one cohesive paragraph directly answering the original task."
    return await call_model(client, prompt, system=system, model=model, max_tokens=250)


async def orchestrate(client: AsyncAnthropic, task: str, lead_model: str, worker_model: str) -> tuple:
    meter = []

    subtasks, plan_usage = await lead_plan(client, task, lead_model)
    meter.append(plan_usage)

    worker_results = await asyncio.gather(*[worker_run_grounded(client, task, st, worker_model) for st in subtasks])
    findings = [text for text, _ in worker_results]
    meter.extend(usage for _, usage in worker_results)

    final_text, synth_usage = await lead_synthesize(client, task, findings, lead_model)
    meter.append(synth_usage)

    return final_text, subtasks, findings, meter


async def single_agent(client: AsyncAnthropic, task: str, model: str) -> tuple:
    system = "Answer directly and thoroughly, covering every aspect of the question."
    text, usage = await call_model(client, task, system=system, model=model, max_tokens=400)
    return text, [usage]


# ---------------------------------------------------------------------------
# Demo 1 — a task that genuinely splits into independent parts
# ---------------------------------------------------------------------------

async def demo_genuine_parallel_task(client: AsyncAnthropic):
    print("\n" + "=" * 70)
    print("1. Genuine parallel task — same model everywhere, architecture only")
    print("=" * 70)
    print(f"\nTask: {RESEARCH_TASK}")

    print("\n-- Single agent --")
    single_text, single_meter = await single_agent(client, RESEARCH_TASK, SINGLE_AGENT_MODEL)
    print(f"Answer: {single_text}")
    single_tokens, single_cost = summarize(single_meter)

    print("\n-- Orchestrator-worker (lead decomposes, subagents run in parallel, lead synthesizes) --")
    final_text, subtasks, findings, meter = await orchestrate(client, RESEARCH_TASK, SINGLE_AGENT_MODEL, SINGLE_AGENT_MODEL)
    for st, f in zip(subtasks, findings):
        print(f"  • {st}\n    -> {f}")
    print(f"\nSynthesized answer: {final_text}")
    multi_tokens, multi_cost = summarize(meter)

    ratio = multi_tokens / single_tokens
    print(f"\nSingle agent:        {single_tokens:>6} tokens (~${single_cost:.5f})")
    print(f"Orchestrator-worker: {multi_tokens:>6} tokens across {len(meter)} calls (~${multi_cost:.5f})")
    print(
        f"Multiplier: {ratio:.1f}x. Anthropic's internal eval reported ~15x for a "
        "lead + 4-subagent setup on their research benchmark — the exact number "
        "here depends on prompt and response sizes, but the mechanism is the "
        "same: you pay for N+2 contexts (plan, N workers, synthesis) instead of one."
    )


# ---------------------------------------------------------------------------
# Demo 2 — the same architecture forced onto a task that didn't need it
# ---------------------------------------------------------------------------

async def demo_wasted_multiplier(client: AsyncAnthropic):
    print("\n" + "=" * 70)
    print("2. Wasted multiplier — a single lookup dressed up as research")
    print("=" * 70)
    print(f"\nTask: {TRIVIAL_TASK!r} — a single factual lookup, not a survey.")

    single_text, single_meter = await single_agent(client, TRIVIAL_TASK, SINGLE_AGENT_MODEL)
    single_tokens, single_cost = summarize(single_meter)
    print(f"\nSingle agent answer: {single_text}")

    final_text, subtasks, findings, meter = await orchestrate(client, TRIVIAL_TASK, SINGLE_AGENT_MODEL, SINGLE_AGENT_MODEL)
    multi_tokens, multi_cost = summarize(meter)
    print(f"\nOrchestrator-worker forced this into {len(subtasks)} 'independent subtopics':")
    for st in subtasks:
        print(f"  • {st}")
    print(f"\nSynthesized answer: {final_text}")

    ratio = multi_tokens / single_tokens
    print(f"\nSingle agent:        {single_tokens:>6} tokens (~${single_cost:.5f})")
    print(f"Orchestrator-worker: {multi_tokens:>6} tokens (~${multi_cost:.5f}) — {ratio:.1f}x more")
    print(
        "for an answer that is no more correct than the single call. This is "
        "the failure mode the lesson warns about: most of those contexts did "
        "work the task never needed."
    )


# ---------------------------------------------------------------------------
# Demo 3 — model tiering: keep the strong model where coordination matters
# ---------------------------------------------------------------------------

async def demo_model_tiering(client: AsyncAnthropic):
    print("\n" + "=" * 70)
    print("3. Model tiering — same task, two model-assignment strategies")
    print("=" * 70)

    print(f"\n-- All top-tier: lead={LEAD_MODEL}, workers={LEAD_MODEL} --")
    _, _, _, meter_all_top = await orchestrate(client, RESEARCH_TASK, LEAD_MODEL, LEAD_MODEL)
    tokens_all_top, cost_all_top = summarize(meter_all_top)

    print(f"\n-- Tiered: lead={LEAD_MODEL}, workers={WORKER_MODEL} --")
    _, _, _, meter_tiered = await orchestrate(client, RESEARCH_TASK, LEAD_MODEL, WORKER_MODEL)
    tokens_tiered, cost_tiered = summarize(meter_tiered)

    savings = (1 - cost_tiered / cost_all_top) * 100 if cost_all_top else 0
    print(f"\nAll top-tier: {tokens_all_top:>6} tokens, ~${cost_all_top:.5f}")
    print(f"Tiered:       {tokens_tiered:>6} tokens, ~${cost_tiered:.5f}")
    print(
        f"Cost reduction from tiering: {savings:.0f}%. The coordination-"
        "sensitive calls — decomposing the task and synthesizing the "
        f"results — kept {LEAD_MODEL}; the parallel lookups, which don't "
        f"need frontier-level reasoning, moved to {WORKER_MODEL}. This "
        "reduces the multiplier without touching the calls where "
        "coordination quality actually matters."
    )


# ---------------------------------------------------------------------------
# Demo 4 — failure handling multiplies with the fan-out
# ---------------------------------------------------------------------------

FLAKY_INDEX = 2  # the read-replicas subtopic simulates a transient rate limit


async def worker_run_flaky(client: AsyncAnthropic, subtask: str, model: str, attempts: dict, index: int) -> tuple:
    attempts[index] = attempts.get(index, 0) + 1
    if index == FLAKY_INDEX and attempts[index] == 1:
        raise SimulatedRateLimitError(f"simulated 429 while researching {subtask!r}")
    return await worker_run(client, subtask, model)


async def safe_worker(client: AsyncAnthropic, subtask: str, model: str, index: int, attempts: dict, max_attempts: int = 2):
    for attempt in range(1, max_attempts + 1):
        try:
            return await worker_run_flaky(client, subtask, model, attempts, index)
        except SimulatedRateLimitError as e:
            if attempt == max_attempts:
                print(f"  ⚠️  subagent {index + 1} exhausted {max_attempts} attempts ({e}) — falling back to a placeholder finding.")
                return f"[no data — subagent {index + 1} failed after retries on: {subtask}]", {"model": model, "input": 0, "output": 0}
            backoff = 0.5 * attempt
            print(f"  ↻ subagent {index + 1} hit a retriable error — backing off {backoff}s before attempt {attempt + 1}/{max_attempts}.")
            await asyncio.sleep(backoff)


async def demo_failure_handling(client: AsyncAnthropic):
    print("\n" + "=" * 70)
    print("4. Failure handling under fan-out — one subagent hits a rate limit")
    print("=" * 70)
    subtasks = FIXED_SUBTOPICS
    print(f"\nSubagent {FLAKY_INDEX + 1} of {len(subtasks)} simulates a transient rate limit on its first attempt.")

    print("\n-- Naive fan-out: asyncio.gather() with no per-task handling --")
    naive_attempts = {}
    tasks = [
        asyncio.create_task(worker_run_flaky(client, st, WORKER_MODEL, naive_attempts, i))
        for i, st in enumerate(subtasks)
    ]
    try:
        await asyncio.gather(*tasks)
        print("(unexpected: no failure was raised)")
    except SimulatedRateLimitError as e:
        print(f"❌ gather() raised before the fan-out completed: {e}")
        # gather() doesn't cancel sibling tasks on failure -- they keep
        # running. Drain them here so their cost is visible, instead of
        # letting their usage lines print later, out of context.
        leftover = await asyncio.gather(*[t for t in tasks if not t.done()], return_exceptions=True)
        wasted = sum(1 for r in leftover if not isinstance(r, Exception))
        print(
            f"{wasted} of the other {len(tasks) - 1} subagents finished successfully AFTER "
            "the exception had already propagated — their tokens were spent, "
            "but the compilation step never runs to use the results. The lead "
            "has nothing to synthesize."
        )

    print("\n-- Resilient fan-out: each subagent retries with backoff, then falls back --")
    resilient_attempts = {}
    results = await asyncio.gather(*[
        safe_worker(client, st, WORKER_MODEL, i, resilient_attempts) for i, st in enumerate(subtasks)
    ])
    findings = [text for text, _ in results]
    for st, f in zip(subtasks, findings):
        print(f"  • {st}\n    -> {f}")

    final_text, _ = await lead_synthesize(client, RESEARCH_TASK, findings, LEAD_MODEL)
    print(f"\nLead still synthesized, using 3 real findings plus 1 recovered-after-retry finding:\n{final_text}")
    print(
        "\nSame simulated failure, two outcomes: without per-subagent "
        "retry/backoff/fallback, one rate limit blocks the entire "
        "synthesis step; with it, the fan-out survives and the lead "
        "compiles from whatever came back. Spreading work across N "
        "subagents means N places this handling has to be applied, not one."
    )


async def main():
    client = AsyncAnthropic()
    await demo_genuine_parallel_task(client)
    await demo_wasted_multiplier(client)
    await demo_model_tiering(client)
    await demo_failure_handling(client)

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(
        "Orchestrator-worker is a hiring decision: it buys parallel "
        "exploration at a real, measured token multiplier, worth paying "
        "only when the task genuinely splits into independent parts (demo "
        "1) and wasted when it doesn't (demo 2). The multiplier itself is "
        "a lever, not a fixed cost — routing the coordination-sensitive "
        "calls to a stronger model and the parallel lookups to a cheaper "
        "one reduces it without touching quality where it matters (demo "
        "3). And fanning work out across subagents doesn't just multiply "
        "tokens, it multiplies the places a failure can occur — the same "
        "retry/backoff/fallback discipline a single agent needs has to be "
        "applied at every subagent independently, or one stuck call stalls "
        "the whole compilation step (demo 4)."
    )


if __name__ == "__main__":
    asyncio.run(main())
