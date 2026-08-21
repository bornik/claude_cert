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

### 4️⃣ `4_state_graph_workflow.py` — A Third Option: Structure Plus Selective Discretion
**What:** A support-ticket graph with explicit nodes and an explicit transition table (not model-decided control flow), where exactly one node (`classify`) calls Claude and every other node is plain Python. A hand-rolled `StateGraph` class stands in for a framework like LangGraph — same shape, no new dependency. Demo 1 shows a low-severity ticket skip straight from `classify` to `resolve`, never touching the human-approval node at all. Demo 2 shows a high-severity ticket hit `await_approval`, write a checkpoint file, and pause — then simulates a process restart (`del`-ing every in-memory variable) before reloading state from that file alone and resuming exactly where it left off.

**Key concepts:**
- Answers "team needs durable state, explicit transition rules, resumable human approvals, and visual inspection of every branch, with model discretion only where it adds value" — each requirement maps to one piece here: the JSON checkpoint (durable), the transition table (explicit rules), the human-gate check in `run()` (resumable approval, surviving a real discard-and-reload, not just a blocking `input()` inside one function call), and `graph.describe()` (every declared branch printed upfront, including ones a given run never takes)
- This is neither script 1's workflow (no model calls at all) nor its agent (the model decides everything) — `classify` is the only node using model discretion, exactly because free-text severity judgment is the one place a fixed if/else can't do the job
- `graph.describe()` can list every possible transition because the graph *is* data (a transition table) — contrast with an agent's control flow, which only exists at runtime, as whatever Claude happens to decide
- The checkpoint write happens *before* the human is asked anything — the pause is durable from the moment the graph reaches the gate, not just for the duration one `input()` call is blocking

```bash
uv run 07-agent-architecture/4_state_graph_workflow.py
```
