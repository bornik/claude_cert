# Module 07 — Agent Architecture

**Note:** this module's structure is reconstructed from general course-page/documentation descriptions, not a verified screen-by-screen syllabus. Update as real course screens confirm or correct the details.

## Files

### 1️⃣ `1_workflow_vs_agent.py` — Who Decides the Steps?
**What:** The same support-ticket task (classify → look up account → escalate if warranted), implemented twice: once as a **workflow** where our Python code decides every step, and once as an **agent** where Claude decides which tools to call, in what order, and when it's done.

**Key concepts:**
- Workflow: fixed control flow, predictable, but can't handle a case the code didn't anticipate
- Agent: Claude drives the loop; you keep calling the API and executing whatever tool it asks for until `stop_reason` is no longer `tool_use`
- The agent version genuinely chose its own sequence live — verified by running it (see the script's own printed narration of which turn called what)
- Tradeoff: flexibility vs. predictability — pick the one whose failure mode you'd rather deal with

```bash
uv run 07-agent-architecture/1_workflow_vs_agent.py
```

### 2️⃣ `2_over_tooling.py` — Does a Bigger Tool Surface Degrade Selection?
**What:** The same query sent against a minimal 3-tool set and a bloated 15-tool set with several deliberately overlapping, vague descriptions (`get_order_details` vs `track_shipment` vs `check_order` — all plausible near-duplicates of the correct tool).

**Key concepts:**
- "Over-tooling is the more common problem in production agents" — teams register tools "just in case" without pruning
- Tested live: on this run `claude-haiku-4-5` picked correctly even at 15 tools — the script explains why that doesn't disprove the mechanism and how to push the example further toward failure
- The fix is discipline (minimum viable tool set, prune/merge overlaps), not a smarter model

```bash
uv run 07-agent-architecture/2_over_tooling.py
```

### 3️⃣ `3_exit_conditions.py` — Don't Rely on Claude to Volunteer to Stop
**What:** An investigation loop where every "ticket" points to another related ticket, so there's no natural stopping point in the data. Scenario A relies purely on Claude deciding to stop (`stop_reason != "tool_use"`). Scenario B adds an explicit exit condition: a stated turn budget plus a `finish_investigation` tool your code can check for.

**Key concepts:**
- "Without explicit exit conditions, the agent will continue requesting tool calls beyond what the task requires" — reproduced live: Scenario A never stopped on its own within 6 turns
- A designed exit condition turns "is it done?" into a fact your code can test (a specific tool call), not an inference from tone or `stop_reason`
- Even when both scenarios hit their turn limit, Scenario B's code *knows* the investigation is incomplete — Scenario A's code has no such signal

```bash
uv run 07-agent-architecture/3_exit_conditions.py
```
