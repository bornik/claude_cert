# Module 06 — Context Engineering

Every `tool_result` Claude gets back is appended to the context window and stays there for the rest of the session — it's never dropped automatically. In a single-turn prompt this is invisible. In a multi-step agent session running many tool calls, the window fills up fast, and once it fills, the agent either compacts (loses detail) or stalls before the task is done.


## Files

### 1️⃣ `1_context_window_growth.py` — Watch the Context Window Fill Up
**What:** Runs a real multi-step tool-use loop (a "search the logs" task across several chunks) and prints `input_tokens` after every turn.

**Key concepts:**
- Every tool_result is appended to `messages` and resent in full on every later API call
- Nothing is dropped automatically — token growth is cumulative, not per-turn
- Live result: input_tokens climbed 615 → 18,617 across 5 turns with ~200-line fake log chunks

```bash
uv run 06-context-engineering/1_context_window_growth.py
```

### 2️⃣ `2_compaction.py` — Summarize Before It Persists
**What:** Same task as example 1, but each tool_result is replaced with a short summary (the one fact the task needs) before being added to history, instead of the raw payload.

**Key concepts:**
- Compaction: decide what a tool_result reduces to *before* it enters context, not after the window is already full
- Live result: same task, same number of tool calls — input_tokens ended at 979 instead of 18,617
- The tradeoff: a summary is only safe if later steps never need what it threw away — compaction is a deliberate choice about what's safe to drop, not a free win

```bash
uv run 06-context-engineering/2_compaction.py
```

### 3️⃣ `3_context_failure_diagnosis.py` — Diagnose the Context Failure (Checkpoint 5)
**What:** Reproduces the certification checkpoint scenario: an agent calls `fetch_policy_document` correctly across several turns, each returning a large result, then needs to call `apply_coverage_rule` — and, per the checkpoint, tool selection can degrade at that point (falling back to a generic `search_knowledge_base`) purely from accumulated context, not a schema problem. Runs the same task with raw accumulation vs. pruned/summarized results side by side.

**Key concepts:**
- Correct tool selection across turns 1-4 rules out a schema/description problem — the failure is turn-specific, not tool-specific
- The mechanism is accumulated raw tool-result context crowding out the current instruction, not `max_tokens` or a vague description
- The fix is pruning/compacting old results before the turn that needs precise selection — same idea as `2_compaction.py`, applied specifically to protect tool-selection accuracy
- Honest result: on this run, `claude-haiku-4-5` picked correctly in both scenarios at this scale — the script explains why that doesn't invalidate the mechanism and how to push the example further toward failure

```bash
uv run 06-context-engineering/3_context_failure_diagnosis.py
```

## Running All Examples

```bash
uv run 06-context-engineering/1_context_window_growth.py
uv run 06-context-engineering/2_compaction.py
uv run 06-context-engineering/3_context_failure_diagnosis.py
```
