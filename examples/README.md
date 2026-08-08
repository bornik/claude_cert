# Examples Directory

Each file demonstrates one tool-use concept in isolation.

## Files

### 1️⃣ `1_simple_loop.py` — The Basic Pattern
**What:** Define a tool → Claude calls it → return result → Claude continues

**Key concepts:**
- Tool schemas
- `tool_use` blocks
- `tool_result` blocks
- Message history

**When to use:** First time learning about tools

```bash
uv run examples/1_simple_loop.py
```

---

### 2️⃣ `2_parallel_calls.py` — Multiple Tools at Once
**What:** Claude calls multiple tools in a single turn (faster!)

**Key concepts:**
- Collecting multiple `tool_use` blocks
- Returning all `tool_result` blocks in one message
- Independent tool calls

**When to use:** When tools don't depend on each other's results

```bash
uv run examples/2_parallel_calls.py
```

---

### 3️⃣ `3_schema_design.py` — Good vs Bad Schemas
**What:** Compare schema quality (no API calls)

**Key concepts:**
- Overlapping descriptions (bad)
- Exclusion conditions ("do not use for X")
- Required vs optional fields
- Description length matters

**When to use:** Before writing your own tools

```bash
uv run examples/3_schema_design.py
```

---

### 4️⃣ `4_ticket_escalation.py` — Real-World Pattern
**What:** Your project! Classify a ticket, then escalate if critical

**Key concepts:**
- Dependent tool calls (second depends on first's output)
- Sequential execution
- Schema descriptions that express dependencies

**When to use:** After learning the basics, see a real scenario

```bash
uv run examples/4_ticket_escalation.py
```

---

### 5️⃣ `5_error_handling.py` — Handle Tool Failures
**What:** When a tool fails, mark it with `is_error=True`

**Key concepts:**
- Error results
- `is_error` flag
- Claude's retry behavior
- Graceful degradation

**When to use:** Building production systems

```bash
uv run examples/5_error_handling.py
```

---

## Recommended Learning Path

1. **Start:** `1_simple_loop.py` — understand the loop
2. **Then:** `2_parallel_calls.py` — see why order matters
3. **Then:** `3_schema_design.py` — understand tool selection
4. **Then:** `4_ticket_escalation.py` — real-world flow
5. **Finally:** `5_error_handling.py` — production robustness

---

## Running All Examples

```bash
# Run each individually
uv run examples/1_simple_loop.py
uv run examples/2_parallel_calls.py
uv run examples/3_schema_design.py
uv run examples/4_ticket_escalation.py
uv run examples/5_error_handling.py

# Or run from tool_use_examples.py
uv run tool_use_examples.py
```

---

## Each Example is Self-Contained

- No dependencies between files
- Each can run standalone
- Comments explain every concept
- You can modify any and experiment
