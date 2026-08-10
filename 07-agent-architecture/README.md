# Module 07 — Agent Architecture

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
**What:** A deliberately ambiguous query ("What's going on with order ORD-7823?") sent 6 times each against a minimal 3-tool set and a bloated 15-tool set with several near-identical descriptions — comparing the *spread* of picks, not just one call, since a bad tool set shows up as inconsistency rather than being wrong every single time.

**Key concepts:**
- "Over-tooling is the more common problem in production agents" — teams register tools "just in case" without consolidating overlapping ones
- Live result: the minimal set picked `get_order_status` all 6/6 times; the bloated set split across 3 different tools (`get_order_details`, `get_order_info`, `order_lookup`) for the exact same query — reproduced live, not simulated
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
