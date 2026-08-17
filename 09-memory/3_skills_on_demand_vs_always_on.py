"""
EXAMPLE 3: On-Demand Skill Loading vs. Always-On Instructions

Skills and CLAUDE.md solve a different problem than the memory scopes in
example 2: not "what state survives a session boundary" but "how do we
carry repeatable instructions across tasks without paying to inject them
into every session." The Claude Code CLI and Agent SDK load a real
SKILL.md file automatically when a request matches its description, and
never inject the full content otherwise.

demo_always_on() and demo_on_demand() below are a SIMULATION built on the
bare Messages API, which has no SKILL.md matcher of its own — the
"on-demand" version hand-rolls a MATCH/NOMATCH classification call to
stand in for what Claude Code's harness does natively. That contrast is
still the right way to see the token-cost tradeoff.

demo_real_agent_skills() is NOT a simulation. It calls Anthropic's actual
"Agent Skills" feature on the Messages API (`container={"skills": [...]}`,
the code-execution tool, beta headers `code-execution-2025-08-25` +
`skills-2025-10-02`). No matcher is written here at all — Claude decides
server-side whether the skill applies. It's a narrower feature than
Claude Code's filesystem SKILL.md discovery (scoped to Anthropic-hosted
or uploaded skills, invoked through the code-execution sandbox), but it
is real, first-party, on-demand skill loading — not an emulation.

This script sends the SAME two requests (one that needs the instructions,
one that doesn't) through both approaches and compares input_tokens.

It also reproduces the subagent constraint from the lesson: a delegated
subagent starts with a clean context and does NOT automatically inherit a
Skill loaded in the parent session — demonstrated by calling a fresh
"subagent" messages[] list with no system prompt carried over.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"

SKILL_NAME = "changelog-entry-format"
SKILL_DESCRIPTION = (
    "Use when the user asks to write or format a CHANGELOG entry. Not relevant "
    "for general questions, code review, or anything unrelated to changelog formatting."
)
# The "full instructions" — deliberately long-ish so the always-on cost is visible.
SKILL_CONTENT = (
    "CHANGELOG ENTRY FORMAT:\n"
    "- One line per entry, starting with a past-tense verb (Added, Fixed, Changed, Removed).\n"
    "- Reference the affected component in brackets, e.g. '[auth]', '[billing]'.\n"
    "- No period at the end of the line.\n"
    "- If the change is user-facing, add '(user-facing)' at the end.\n"
    "- Group entries under a '## [Unreleased]' heading if none exists yet.\n"
    "- Never mention internal ticket numbers or PR numbers in the entry itself."
)

RELEVANT_REQUEST = "Write a changelog entry: we fixed a bug where billing invoices double-charged annual plans."
IRRELEVANT_REQUEST = "What's a good analogy for explaining REST APIs to a non-technical stakeholder?"


def demo_always_on():
    """CLAUDE.md shape: the instruction block rides in the system prompt
    on every single call, whether the request needs it or not."""
    print("\n" + "=" * 70)
    print("ALWAYS-ON (CLAUDE.md shape): instructions included on every call")
    print("=" * 70)

    for label, request in [("Relevant request", RELEVANT_REQUEST), ("Irrelevant request", IRRELEVANT_REQUEST)]:
        response = client.messages.create(
            model=MODEL,
            max_tokens=150,
            system=SKILL_CONTENT,  # always injected, regardless of fit
            messages=[{"role": "user", "content": request}],
        )
        print(f"\n{label}:")
        print_usage(response)
        print(f"  → {response.content[0].text.strip()[:100]}...")

    print("\n📝 Both calls paid the full instruction-block token cost — including")
    print("   the irrelevant request, which never needed changelog formatting rules.")


def demo_on_demand():
    """Skill shape: a cheap match check runs first using ONLY the name and
    description. Full SKILL_CONTENT is injected into the real call only
    when that check matches — an irrelevant request never sees it."""
    print("\n" + "=" * 70)
    print("ON-DEMAND (Skill shape): name+description resident, full content on match")
    print("=" * 70)

    for label, request in [("Relevant request", RELEVANT_REQUEST), ("Irrelevant request", IRRELEVANT_REQUEST)]:
        print(f"\n{label}:")

        # Step 1 — cheap match check against name+description ONLY.
        match_check = client.messages.create(
            model=MODEL,
            max_tokens=10,
            system=(
                f"Available skill: '{SKILL_NAME}' — {SKILL_DESCRIPTION} "
                "Answer with exactly one word: MATCH or NOMATCH."
            ),
            messages=[{"role": "user", "content": request}],
        )
        print_usage(match_check)
        verdict = match_check.content[0].text.strip().upper()
        matched = "NOMATCH" not in verdict and "MATCH" in verdict
        print(f"  Skill match check: {verdict} → {'loading skill' if matched else 'skipping skill'}")

        # Step 2 — the real call. Full content injected ONLY on a match.
        extra_kwargs = {"system": SKILL_CONTENT} if matched else {}
        response = client.messages.create(
            model=MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": request}],
            **extra_kwargs,
        )
        print_usage(response)
        print(f"  → {response.content[0].text.strip()[:100]}...")

    print("\n📝 The irrelevant request paid only the small match-check cost — the")
    print("   full instruction block never entered its context at all. The relevant")
    print("   request paid the match-check PLUS the full block, same as always-on.")
    print("   On-demand costs more when it matches (two calls, not one) and less")
    print("   when it doesn't — the savings show up on the requests that DON'T need it.")


def demo_real_agent_skills():
    """The Messages API's ACTUAL Agent Skills feature — not a simulation.

    Unlike demo_always_on() and demo_on_demand() above, there is no
    hand-rolled matcher here. Claude decides server-side whether the
    'pptx' skill applies to each request; we just make it available via
    the `container` parameter. Skills on the Messages API always run
    through the code-execution sandbox, so declaring one always requires
    the code-execution tool plus two beta headers on EVERY call. That
    declaration is itself a real, non-trivial token tax, paid whether the
    skill is used or not — bigger than our ~80-token toy classifier prompt.

    A skill only actually "loads" when Claude opens/reads its files inside
    the sandbox — that's a real tool call, visible in the response content
    as a code-execution block. Telling Claude "don't run any code" (an
    earlier version of this demo did) suppresses that entirely, so nothing
    ever gets consulted and relevant/irrelevant end up costing the same —
    which looks like the mechanism doing nothing, when really we disabled
    it ourselves. This version instead asks something only the skill's
    OWN guidance would answer correctly (not general knowledge), so Claude
    has a real reason to open the file — and we check the response for an
    actual code-execution block instead of assuming it happened.
    """
    print("\n" + "=" * 70)
    print("REAL AGENT SKILLS (Messages API): server-side discovery, no matcher written")
    print("=" * 70)

    skill_relevant_request = (
        "Check your available PowerPoint-building skill's own guidance (not "
        "general knowledge) and tell me, in one sentence: what slide aspect "
        "ratio does it recommend by default? Don't create any files."
    )

    for label, request in [("Relevant request", skill_relevant_request), ("Irrelevant request", IRRELEVANT_REQUEST)]:
        print(f"\n{label}:")
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=300,
            betas=["code-execution-2025-08-25", "skills-2025-10-02"],
            container={"skills": [{"type": "anthropic", "skill_id": "pptx", "version": "latest"}]},
            tools=[{"type": "code_execution_20260521", "name": "code_execution"}],
            messages=[{"role": "user", "content": request}],
        )
        print_usage(response)

        # Don't assume the skill fired just because we asked a "relevant"
        # question — check the actual response for a code-execution block,
        # which is the only real evidence Claude opened the skill's files.
        code_exec_types = {
            "server_tool_use",
            "bash_code_execution_tool_result",
            "text_editor_code_execution_tool_result",
        }
        skill_consulted = any(b.type in code_exec_types for b in response.content)
        print(f"  Skill actually consulted (code-execution block present)? {skill_consulted}")

        text_block = next((b for b in response.content if b.type == "text"), None)
        if text_block:
            print(f"  → {text_block.text.strip()[:100]}...")

    print("\n📝 Three things to take from this:")
    print("   1. We wrote no MATCH/NOMATCH check this time — Claude decided on its own")
    print("      whether to open the skill's files. That decision is the 'on-demand' part.")
    print("   2. Trust the 'Skill actually consulted' line, not the token counts, to know")
    print("      whether it actually happened — a prompt LOOKING relevant doesn't guarantee")
    print("      Claude opened the file; only a code-execution block in the response proves it.")
    print("   3. Either way, declaring a real skill costs far more up front than")
    print("      demo_on_demand()'s hand-rolled classifier did — that fixed tax is paid")
    print("      on every call, whether or not Claude ends up consulting the skill.")


def demo_subagent_does_not_inherit_skill():
    """A delegated subagent starts with a clean context. Even though the
    parent session 'loaded' the skill (matched + injected it), a fresh
    subagent call with no system prompt carried over has no access to it
    unless the calling code explicitly passes it along."""
    print("\n" + "=" * 70)
    print("SUBAGENT CONSTRAINT: Skills don't automatically carry over to a subagent")
    print("=" * 70)

    print("\nParent session: skill matched and injected for this request.")
    parent_response = client.messages.create(
        model=MODEL,
        max_tokens=150,
        system=SKILL_CONTENT,
        messages=[{"role": "user", "content": RELEVANT_REQUEST}],
    )
    print_usage(parent_response)
    print(f"Parent output: {parent_response.content[0].text.strip()[:100]}...")

    print("\nDelegating the SAME request to a 'subagent' — fresh messages[], no system prompt:")
    subagent_response = client.messages.create(
        model=MODEL,
        max_tokens=150,
        # No system prompt passed — this is the default unless the caller
        # explicitly registers the skill against the subagent's config.
        messages=[{"role": "user", "content": RELEVANT_REQUEST}],
    )
    print_usage(subagent_response)
    print(f"Subagent output (no skill instructions): {subagent_response.content[0].text.strip()[:100]}...")

    print("\n📝 The subagent answered from general knowledge, not the changelog format")
    print("   rules the parent had loaded — nothing carried over automatically. If a")
    print("   subagent's task depends on a Skill, that Skill must be registered")
    print("   against the SUBAGENT's own configuration, not assumed to be inherited.")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 3: On-Demand Skill Loading vs. Always-On Instructions")
    print("=" * 70)

    demo_always_on()
    demo_on_demand()
    demo_real_agent_skills()
    demo_subagent_does_not_inherit_skill()

    print("""
======================================================================
KEY TAKEAWAY
======================================================================
CLAUDE.md-shaped instructions are a fixed cost every session pays,
whether or not the current task needs them — fine for standards that
truly apply to everything. A Skill keeps only a name+description
resident and loads full content on demand, which trades a small
per-request match check for skipping the full cost entirely on requests
that don't need it. Neither is "memory" in the session-scope sense from
example 2 — this is about not re-paying for instructions the current
task doesn't use, not about what survives a session boundary.

demo_always_on() and demo_on_demand() simulate that tradeoff on the bare
Messages API, which has no skill matcher of its own. demo_real_agent_skills()
is the real thing: Anthropic's Messages API "Agent Skills" feature
(`container={"skills": [...]}` + the code-execution tool + two beta
headers) does on-demand skill loading server-side, with no matcher code
to write. It's narrower than Claude Code's filesystem SKILL.md discovery —
scoped to Anthropic-hosted or uploaded skills run through the
code-execution sandbox — but it is not an emulation.

Subagents make this concrete: delegation starts a clean context, so a
Skill (or any instruction set) has to be explicitly wired to the
subagent's own configuration — it is never assumed to carry over from
whoever did the delegating.
""")


if __name__ == "__main__":
    main()
