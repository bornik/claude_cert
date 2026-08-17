# Module 09 — Memory

## Files

### 1️⃣ `1_session_vs_persistent_memory.py` — Where "Memory" Actually Lives
**What:** A fact learned mid-conversation (session memory) disappears the instant a fresh `messages[]` list starts. A fact written to a file (persistent memory) can be read back and re-injected into a brand new conversation's system prompt.

**Key concepts:**
- Claude has no memory of its own between separate API calls — "memory" is always just text re-entering the context window somehow
- Session memory = earlier turns in the same `messages[]` list
- Persistent memory = storage outside the context window (file/DB) that your code reads and re-injects — proven live: a fresh conversation with no injected memory forgot the preference; the same fresh conversation with `memory_store.json` read into the system prompt recalled it correctly
- The real design question is what to store, where, and when to re-inject it — not "how Claude remembers"

```bash
uv run 09-memory/1_session_vs_persistent_memory.py
```

### 2️⃣ `2_memory_scope_comparison.py` — Matching Use Case to Memory Scope
**What:** Reproduces the certification checkpoint's three use cases live: a support agent across daily sessions, an independent document formatter, and a single-session coding assistant. Runs the daily-checkin use case two ways — naive in-context (full history resent every "session") vs. external storage (only a condensed state string re-injected) — and measures `input_tokens` for both, plus a stateless run showing the cost it accepts (a follow-up job has zero knowledge of the prior one).

**Key concepts:**
- In-context isn't inherently right or wrong — it's wrong when state must survive a session boundary (use case 1) and right when there isn't one (use case 3)
- Live result: naive in-context `input_tokens` climbed 34 → 222 → 409 → 604 across 4 sessions; external storage held roughly flat (~70-85) across the same 4 sessions by re-injecting only a condensed state string
- Stateless is the right scope when jobs are genuinely independent — the cost is real (a follow-up referencing a prior job gets nothing) but it's a cost this use case never needed to pay for
- The "session four" failure from the postmortem is exactly the in-context growth reproduced here, just at a larger scale (real system prompts + tool schemas + many more turns)

```bash
uv run 09-memory/2_memory_scope_comparison.py
```

### 3️⃣ `3_skills_on_demand_vs_always_on.py` — On-Demand Skill Loading vs. Always-On Instructions
**What:** Simulates the Skill-loading mechanism (Claude Code / Agent SDK load a SKILL.md's full content only on a description match, never otherwise) against an always-on CLAUDE.md-style approach, using the same two requests — one that needs changelog-formatting instructions, one that doesn't — through both. Then calls Anthropic's *actual* Agent Skills feature on the Messages API (`container={"skills": [...]}` + code execution + beta headers) — no matcher written, Claude decides server-side. Also reproduces the subagent constraint: a delegated "subagent" call with a fresh `messages[]` and no system prompt carried over has no access to a Skill the parent session loaded.

**Key concepts:**
- Always-on pays the full instruction-block token cost on every call, relevant or not — live result: the irrelevant request paid 146 input tokens for changelog rules it never used
- On-demand runs a cheap match check first (82/81 input tokens) and only injects the full block when it matches — the irrelevant request skipped the block entirely; the relevant request paid the match check *plus* the full block (more total calls, but the savings show up on requests that don't match)
- The first two demos are a **simulation** built on the bare Messages API, which has no SKILL.md matcher of its own — useful for seeing the cost tradeoff, but not the real mechanism
- `demo_real_agent_skills()` is **not** a simulation: it's Anthropic's actual Agent Skills feature (Anthropic-hosted skills like `pptx`/`xlsx`/`docx`/`pdf`, or your own uploaded skills via the Skills API), invoked through the code-execution sandbox with no hand-written matcher — narrower in scope than Claude Code's filesystem SKILL.md discovery, but genuinely on-demand and server-side
- The real mechanism still costs meaningfully more than the toy simulation, and that's the honest lesson, not a flaw: declaring `container.skills` requires the code-execution tool plus two beta headers on *every* call — a bigger fixed tax than the ~80-token hand-rolled classifier prompt, paid whether or not the skill actually applies. The demo keeps this cheap by explicitly telling Claude not to write or run any code — actually invoking the skill to produce a real file (writing and running Python in the sandbox) costs substantially more still, since that's genuine sandboxed work, not text generation
- This is a different problem than memory scope in example 2 — it's about not re-paying for instructions the current task doesn't use, not about what survives a session boundary
- Subagents don't automatically inherit a Skill from the parent session — live result: the same request answered with real changelog-format rules from the parent, but generically (no format rules) from a fresh subagent call with no system prompt passed. A Skill a subagent needs must be registered against its own configuration.

```bash
uv run 09-memory/3_skills_on_demand_vs_always_on.py
```
