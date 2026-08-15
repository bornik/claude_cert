# Module 12 — Managed Agents

Managed Agents is the third way to run an agent, alongside the raw Messages
API loop and the Claude Agent SDK covered earlier in this repo. The
distinction that matters:

| | Who writes the loop | Who runs the loop | Where tools execute |
|---|---|---|---|
| Raw Messages API loop | You | Your process | Wherever your code executes them |
| Claude Agent SDK | The SDK | Your process (subprocess) | Wherever your code executes them |
| **Managed Agents** | **Anthropic** | **Anthropic's servers** | **A per-session sandbox container Anthropic hosts** |

You create an **Agent** (model + system prompt + tools — persisted,
versioned, created ONCE) and an **Environment** (a reusable sandbox
template). Every run is a **Session** that references both. Your
application sends/receives JSON events over an SSE stream — it never
executes a tool itself for built-in tools, and even custom tools change
transport (an event, not a content block), not who implements them.

## Files

### 🛠️ `_setup.py` — shared helper, not a runnable example
Caches created agent/environment IDs to `.managed_agents_state.json`
(gitignored) so re-running the scripts below reuses existing resources
instead of creating new ones every time — enforcing the "agent once, not
every run" rule the Managed Agents docs are explicit about. Delete that
file to force fresh resources (e.g. after editing an agent's system prompt).

### 1️⃣ `1_agent_and_session_basics.py` — Agent (once) → Session (every run)
**What:** Creates a minimal agent with the built-in `agent_toolset_20260401`
(bash, read, etc.) and a cloud environment, then starts a session that asks
Claude to run `pwd && whoami && ls /workspace` — proving those commands
execute inside Anthropic's sandbox, not on your machine.

**Key concepts:**
- Mandatory flow: `POST /v1/environments` and `POST /v1/agents` are one-time
  setup; `POST /v1/sessions` is the only thing that happens on every run
- Stream-first: open the event stream *before* sending the kickoff message,
  or early events can be missed
- The correct idle-break gate is `session.status_idle` **with a non-`requires_action`
  stop_reason**, or `session.status_terminated` — not idle alone (idle also
  fires transiently between tool calls)
- Sessions are cheap and disposable (archiving one is routine cleanup) —
  agents and environments are NOT (archiving those is permanent, no
  unarchive)

```bash
uv run 12-managed-agents/1_agent_and_session_basics.py
```

### 2️⃣ `2_custom_tool_managed_agent.py` — Same Weather Task, Third Transport
**What:** The exact "what's the weather in Paris?" task from
`04-tool-use-schema-design/1_simple_loop.py` and `9_agent_sdk_builtin_loop.py`,
run a third way: the custom tool call arrives as an `agent.custom_tool_use`
**event** on the session stream, answered with a `user.custom_tool_result`
event — instead of a `tool_use` content block (raw loop) or a `query()`
callback (Agent SDK).

**Key concepts:**
- Custom tools are the one tool type Managed Agents does *not* execute for
  you — your code still owns `execute_weather_tool`, identical across all
  three paradigms
- What changes is purely the transport: content block → SDK callback →
  session event
- Directly comparable side-by-side with the other two files, same fake tool
  implementation, same prompt

```bash
uv run 12-managed-agents/2_custom_tool_managed_agent.py
```

## Requirements

- Managed Agents beta access on your API key's workspace. Both scripts
  catch a 403/404 and print a friendly note if the beta isn't enabled yet —
  ask your Anthropic contact to turn it on, then re-run.
- Each session provisions a real cloud sandbox container, so these scripts
  take noticeably longer (tens of seconds) and cost a small amount of real
  compute + tokens, unlike the near-instant Messages API examples elsewhere
  in this repo.
