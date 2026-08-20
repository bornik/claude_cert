# Module 04 — Tool-use and Schema Design

Each file demonstrates one tool-use concept in isolation.

**Start here:** open [`tool-use-guide.html`](tool-use-guide.html) in your browser for a visual overview before running the scripts below.

## Files

### 0️⃣ `0_structured_output.py` — Structured Output (Response Format Control)
**What:** Force Claude's response to match a JSON schema you provide

**Key concepts:**
- `response_format` with `json_schema`
- Guaranteed output structure
- Extraction, classification, structured data generation

**When to use:** When you need guaranteed JSON format (before learning about tools)

```bash
uv run 04-tool-use-schema-design/0_structured_output.py
```

---

### 1️⃣ `1_simple_loop.py` — The Basic Pattern
**What:** Define a tool → Claude calls it → return result → Claude continues

**Key concepts:**
- Tool schemas
- `tool_use` blocks
- `tool_result` blocks
- Message history

**When to use:** First time learning about tools

```bash
uv run 04-tool-use-schema-design/1_simple_loop.py
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
uv run 04-tool-use-schema-design/2_parallel_calls.py
```

---

### 3️⃣ `3_schema_design.py` — Good vs Bad Schemas
**What:** Compare schema quality, then prove it with live API calls — same query sent against a bad and a good schema, so you see Claude's actual tool choice / actual invented values instead of just reading a claim about it

**Key concepts:**
- Overlapping descriptions (bad)
- Exclusion conditions ("do not use for X")
- Required vs optional fields
- Description length matters

**When to use:** Before writing your own tools

```bash
uv run 04-tool-use-schema-design/3_schema_design.py
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
uv run 04-tool-use-schema-design/4_ticket_escalation.py
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
uv run 04-tool-use-schema-design/5_error_handling.py
```

---

### 6️⃣ `6_boundary_case_failure.py` — "Why does Claude keep calling the wrong tool?"

**What:** Reproduces the exact diagnostic scenario from the lesson: two overlapping tools (`search_docs` / `get_context_summary`, both described as "find/retrieve information") tested against a **boundary case** — a question whose answer is already sitting in the conversation history.

**Key concepts:**
- A schema can pass every happy-path test and still fail near the boundary between two similar tools
- The fix is one exclusion sentence per tool ("do not use this when...") — not a rewrite
- `tool_choice: "auto"` vs `"any"` — forcing a tool call (common in production agent harnesses) is what actually exposes this failure mode; leaving Claude free to skip tools can mask it
- Real API output can be less dramatic than the story — see the script's own honest note about when this actually reproduces vs. when a capable model shrugs it off

**When to use:** After `3_schema_design.py`, when you want to see this *specific* named failure mode (not just "overlapping descriptions are bad" in the abstract)

```bash
uv run 04-tool-use-schema-design/6_boundary_case_failure.py
```

---

### 7️⃣ `7_mcp_connector.py` — MCP as an Alternative to Manual Schema Authoring

**What:** Everything above assumes you write the tool schema and the execution function yourself. This example connects to a real remote MCP server (DeepWiki) via the API's MCP Connector — no locally-defined `input_schema`, no Python function that executes the call. The server supplies the tool definitions and runs the tool itself.

**Key concepts:**
- `mcp_servers` + a `{"type": "mcp_toolset", "mcp_server_name": ...}` entry in `tools` — requires the `mcp-client-2025-11-20` beta header
- `mcp_tool_use` / `mcp_tool_result` content blocks — the same contract as `tool_use`/`tool_result`, just server-executed
- Context cost controls: `defer_loading` (delay loading a tool def until needed) and per-tool `enabled` (allowlist which of the server's tools are exposed)
- Manual authoring and MCP aren't mutually exclusive — MCP for breadth, hand-tuned descriptions (see `3_schema_design.py`, `6_boundary_case_failure.py`) for precision where it matters
- Only remote (Streamable HTTP) servers work through the API connector — local stdio servers need Claude Code/Desktop as the client

**Cost warning:** this one call pulls a full wiki page into context (~165k input tokens on the run we tested). Don't loop it.

**When to use:** Once you've written a schema by hand and want to see the alternative — when someone else already built and maintains the integration

```bash
uv run 04-tool-use-schema-design/7_mcp_connector.py
```

---

### 8️⃣ `8_id_mismatch_bug.py` — Spot and Fix the Schema Bug (Checkpoint 3)

**What:** Reproduces the certification checkpoint scenario live: the schema is valid, the tool description is specific, the tool result content is correct — and the request still gets rejected. The bug is a mismatched `tool_use_id`.

**Key concepts:**
- `tool_use` and `tool_result` are matched by **id**, not by position in the conversation
- A wrong id isn't "slightly off" — the API treats it as a reference to a `tool_use` that doesn't exist and rejects the whole request
- `tool_result` blocks are sent with `role="user"` even though your application generated the content — `role` marks who is sending the message, not who authored it
- We trigger the real `400 invalid_request_error` first, then show the one-line fix

**When to use:** After `1_simple_loop.py`, once you understand the basic loop and want to see how it breaks when the id plumbing is wrong

```bash
uv run 04-tool-use-schema-design/8_id_mismatch_bug.py
```

---

### 9️⃣ `9_agent_sdk_builtin_loop.py` — The Same Loop, Built Into the Agent SDK

**What:** The exact weather/Paris scenario from `1_simple_loop.py`, run again — but through the **Claude Agent SDK** (`claude-agent-sdk`, a different package from `anthropic`). One `query()` call replaces the entire manual `while response.stop_reason == "tool_use"` loop: the SDK calls the tool, feeds the result back, and keeps going until Claude is done.

**Key concepts:**
- Not the same package as everything else in this repo — spawns the `claude` CLI as a subprocess, so it needs that CLI installed, not just `ANTHROPIC_API_KEY`
- Left at its defaults it registers Claude Code's own built-in tools (Bash, Read, Edit, ...) into every call and can pick up this machine's own default model — this script explicitly passes `tools=[]` and `model=` to keep the comparison fair and the cost predictable
- The tradeoff is the same "workflow vs. agent" one from Module 07, just one level lower: Example 1 gives full visibility/control over every tool-use turn (useful for approval gates, custom retries, logging); the Agent SDK trades that control for not having to write or maintain the loop yourself
- Tools are registered as real async Python functions (`@tool` + `create_sdk_mcp_server`), not a JSON schema plus an `if/elif` dispatching on `tool_use_block.name`

**When to use:** After `1_simple_loop.py`, once you understand the manual loop and want to see what a purpose-built SDK does instead of hand-rolling it

```bash
uv run 04-tool-use-schema-design/9_agent_sdk_builtin_loop.py
```

---

### 🔟 `10_agent_sdk_subagents.py` — Real Subagent Delegation

**What:** The orchestrator is only given the `Task` tool — no direct access to the custom `get_weather` tool at all. The only way it can answer "What's the weather in Paris?" is by delegating to a `weather-checker` subagent (`AgentDefinition`) that alone has the weather tool. This is a genuinely separate Claude turn, not the "second bare API call" stand-in used in Module 09.

**Key concepts:**
- `AgentDefinition(description=..., prompt=..., tools=[...])` — a named subagent with its own system prompt and its own restricted tool list, registered via `ClaudeAgentOptions(agents={"name": AgentDefinition(...)})`
- The orchestrator delegates through a tool_use block named `Agent` carrying `subagent_type` in its input — that ability comes entirely from having the `Task` tool; remove it and delegation is impossible
- Subagents launch in the background by default: the orchestrator's first reply is a placeholder ("I've launched the agent... running in the background") with its own `ResultMessage`, then a second turn — triggered once `TaskNotificationMessage` reports the subagent is done — delivers the real answer with a second `ResultMessage`. Two turns of one `query()` call, not two calls
- Each subagent turn carries its own isolated token usage (visible in `TaskNotificationMessage.usage`), separate from the orchestrator's own accounting
- Scoping tools per-`AgentDefinition` is also how you'd keep an orchestrator away from a capability (Bash, a sensitive MCP tool) that only one specialized subagent should touch

**When to use:** After `9_agent_sdk_builtin_loop.py`, once you've seen one agent drive its own tool loop and want to see it hand off a subtask to a differently-scoped agent instead

```bash
uv run 04-tool-use-schema-design/10_agent_sdk_subagents.py
```

---

## Recommended Learning Path

1. **Start:** `0_structured_output.py` — constrain response format (simplest case)
2. **Then:** `1_simple_loop.py` — understand the tool-use loop
3. **Then:** `2_parallel_calls.py` — see why order matters (parallel vs sequential)
4. **Then:** `3_schema_design.py` — understand tool selection and schema quality
5. **Then:** `6_boundary_case_failure.py` — see the boundary-case failure mode live
6. **Then:** `4_ticket_escalation.py` — real-world flow (dependent tool calls)
7. **Then:** `5_error_handling.py` — production robustness (error handling)
8. **Then:** `7_mcp_connector.py` — see the alternative to writing schemas yourself (MCP)
9. **Then:** `8_id_mismatch_bug.py` — see the id-matching invariant break and get fixed
10. **Then:** `9_agent_sdk_builtin_loop.py` — see the loop run by a purpose-built SDK
11. **Finally:** `10_agent_sdk_subagents.py` — see that same SDK hand a subtask to a real, separately-scoped subagent

---

## Running All Examples

```bash
# Run each individually
uv run 04-tool-use-schema-design/0_structured_output.py
uv run 04-tool-use-schema-design/1_simple_loop.py
uv run 04-tool-use-schema-design/2_parallel_calls.py
uv run 04-tool-use-schema-design/3_schema_design.py
uv run 04-tool-use-schema-design/4_ticket_escalation.py
uv run 04-tool-use-schema-design/5_error_handling.py
uv run 04-tool-use-schema-design/6_boundary_case_failure.py
uv run 04-tool-use-schema-design/7_mcp_connector.py  # expensive (~165k input tokens) — don't loop this one
uv run 04-tool-use-schema-design/8_id_mismatch_bug.py  # triggers and fixes a real tool_use_id mismatch error
uv run 04-tool-use-schema-design/9_agent_sdk_builtin_loop.py  # needs the `claude` CLI installed, not just ANTHROPIC_API_KEY
uv run 04-tool-use-schema-design/10_agent_sdk_subagents.py  # needs the `claude` CLI installed too
```

---

## Each Example is Self-Contained

- No dependencies between files
- Each can run standalone
- Comments explain every concept
- You can modify any and experiment
