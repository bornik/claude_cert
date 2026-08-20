# Claude API Learning Project

A hands-on companion for the Anthropic **Production-Grade Prompting, Agents & Tool Use** certification. Each folder maps to a course module — run the code for a module while you're on its lesson screens.

---

## 📖 Course Map

| Module | Course Section | Folder |
|---|---|---|
| 01 | MSO Foundations *(separate course track)* | [`01-mso-foundations/`](01-mso-foundations/) |
| 02 | Prompting Craft | [`02-prompting-craft/`](02-prompting-craft/) |
| 03 | Extended Thinking | [`03-extended-thinking/`](03-extended-thinking/) |
| 04 | Tool-use and Schema Design | [`04-tool-use-schema-design/`](04-tool-use-schema-design/) |
| 05 | Streaming Responses | [`05-streaming-responses/`](05-streaming-responses/) |
| 06 | Context Engineering | [`06-context-engineering/`](06-context-engineering/) |
| 07 | Agent Architecture | [`07-agent-architecture/`](07-agent-architecture/) |
| 08 | Human-in-the-loop | [`08-human-in-the-loop/`](08-human-in-the-loop/) |
| 09 | Memory | [`09-memory/`](09-memory/) |
| 10 | Files API | [`10-files-api/`](10-files-api/) |
| 11 | Message Batches API | [`11-message-batches/`](11-message-batches/) |
| 12 | Managed Agents | [`12-managed-agents/`](12-managed-agents/) |
| 13 | Packaging Workflows | [`13-packaging-workflows/`](13-packaging-workflows/) |
| 14 | MCP Servers & Access Auditing | [`14-mcp-servers/`](14-mcp-servers/) |
| 15 | Prompt Caching | [`15-prompt-caching/`](15-prompt-caching/) |

As you reach a new module in the course, create `NN-module-name/` and add examples there — folder order should always match the course sidebar order.

Keep a running log of screen-by-screen takeaways in [`NOTES.md`](NOTES.md) as you go — it doubles as a study guide later.

Every example prints a `💰 Usage (...)` line after each API call — input/output token counts and an estimated cost, via [`common/usage.py`](common/usage.py). Update the `PRICING` dict there if you switch to a different model.

---

## 📁 Project Structure

```
claude-cert/
├── README.md                        ← you are here
├── NOTES.md                         ← your screen-by-screen study log
├── 01-mso-foundations/
│   ├── README.md
│   ├── 1_non_determinism.py
│   └── 2_prompting_modes.py
├── 02-prompting-craft/
│   ├── README.md
│   ├── process_ticket.py            ← prompt runner (support ticket classifier)
│   ├── prompt_iteration.py          ← 6-pass "bare → refined" prompt walkthrough
│   ├── system_prompt.txt            ← refined prompt
│   ├── system_prompt_bare.txt       ← bare/unconstrained prompt, for comparison
│   └── examples.json
├── 03-extended-thinking/
│   ├── README.md
│   ├── 1_basic_thinking.py
│   └── 2_thinking_budget_comparison.py
├── 04-tool-use-schema-design/
│   ├── README.md
│   ├── tool-use-guide.html          ← visual overview, open in browser
│   ├── 0_structured_output.py       ← response format control (JSON schema)
│   ├── 1_simple_loop.py
│   ├── 2_parallel_calls.py
│   ├── 3_schema_design.py
│   ├── 4_ticket_escalation.py       ← real-world: classify then escalate
│   ├── 5_error_handling.py
│   ├── 6_boundary_case_failure.py
│   ├── 7_mcp_connector.py           ← MCP as an alternative to manual schemas
│   ├── 8_id_mismatch_bug.py         ← reproduces + fixes tool_use_id mismatch error
│   └── 9_agent_sdk_builtin_loop.py  ← same loop as #1, via claude-agent-sdk
├── 05-streaming-responses/
│   ├── README.md
│   ├── 1_basic_streaming.py
│   └── 2_streaming_with_progress.py
├── 06-context-engineering/
│   ├── README.md
│   ├── 1_context_window_growth.py
│   ├── 2_compaction.py
│   └── 3_context_failure_diagnosis.py
├── 07-agent-architecture/
│   ├── README.md
│   ├── 1_workflow_vs_agent.py
│   ├── 2_over_tooling.py
│   └── 3_exit_conditions.py
├── 08-human-in-the-loop/
│   ├── README.md
│   ├── 1_approval_gate.py
│   └── 2_hitl_insertion_points.py
├── 09-memory/
│   ├── README.md
│   ├── 1_session_vs_persistent_memory.py
│   ├── 2_memory_scope_comparison.py
│   └── 3_skills_on_demand_vs_always_on.py
├── 10-files-api/
│   ├── README.md
│   ├── sample.txt
│   └── 1_files_api_basics.py
├── 11-message-batches/
│   ├── README.md
│   └── 1_message_batches.py
├── 12-managed-agents/
│   ├── README.md
│   ├── _setup.py                     ← guarded agent/environment creation, not a runnable example
│   ├── 1_agent_and_session_basics.py
│   └── 2_custom_tool_managed_agent.py  ← same weather task as 04-module #1 and #9, a third transport
├── 13-packaging-workflows/
│   ├── README.md
│   ├── packaging-demo/                       ← real plugin: 2 skills + a PreToolUse hook
│   ├── local-marketplace/                    ← catalogs packaging-demo via a local path
│   ├── sdk_fixture/                          ← standalone project fixture for the SDK script
│   └── 1_agent_sdk_setting_sources.py
├── 14-mcp-servers/
│   ├── README.md
│   ├── access-audit-demo/                    ← real plugin: PostToolUse hook, audits every tool call
│   └── local-marketplace/                    ← catalogs access-audit-demo via a local path
├── 15-prompt-caching/
│   ├── README.md
│   └── 1_cache_threshold_and_ttl.py
├── common/
│   └── usage.py                     ← print_usage() — token count + est. cost after every API call
├── pyproject.toml / uv.lock         ← dependencies
└── .env / .env.example              ← API key config
```

Root holds only project setup (dependencies, env config, top-level docs). Everything module-specific lives in its own `NN-module-name/` folder with its own README.

---

## 🚀 Setup (from scratch)

New machine, nothing installed yet? Follow these in order.

### 1. Install Homebrew (if you don't have it)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Check it worked: `brew --version`

### 2. Install `uv` (Python package/version manager — replaces pip + pyenv)
```bash
brew install uv
```
Check it worked: `uv --version`

You don't need to separately install Python — `uv` will download and manage the exact version this project needs (`3.11`, see `.python-version`) automatically on first run.

### 3. Get the project and install dependencies
```bash
git clone git@github.com:bornik/claude_cert.git
cd claude_cert
uv sync
```
`uv sync` reads `pyproject.toml` / `uv.lock`, installs Python 3.11 if missing, and creates an isolated virtual environment with the `anthropic` SDK etc. — no manual `venv` steps needed.

### 4. Get an Anthropic API key
Sign up / log in at [console.anthropic.com](https://console.anthropic.com), create an API key under **API Keys**.

### 5. Configure your API key
```bash
cp .env.example .env
```
Open `.env` in any editor and set:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 6. Verify it works
```bash
uv run 02-prompting-craft/process_ticket.py
```
If you see a JSON classification result printed, you're set up correctly.

### 7. (Optional) Install the Claude Code CLI for the Agent SDK example
Every script above uses the `anthropic` package directly. One exception —
`04-tool-use-schema-design/9_agent_sdk_builtin_loop.py` — uses the separate
`claude-agent-sdk` package, which spawns the `claude` CLI as a subprocess.
It needs the CLI installed in addition to your `.env` API key:
```bash
npm install -g @anthropic-ai/claude-code
```
Skip this if you don't plan to run that one script — nothing else in the repo needs it.

---

## 📚 Usage

### Module 01 — MSO Foundations

```bash
uv run 01-mso-foundations/1_non_determinism.py    # same prompt, different valid outputs
uv run 01-mso-foundations/2_prompting_modes.py    # no-system vs system vs multi-turn
```

Details: see [`01-mso-foundations/README.md`](01-mso-foundations/README.md).

### Module 02 — Prompting Craft

```bash
uv run 02-prompting-craft/process_ticket.py                       # run first example
uv run 02-prompting-craft/process_ticket.py "My API key stopped working"
uv run 02-prompting-craft/process_ticket.py --all                 # run all examples
uv run 02-prompting-craft/process_ticket.py --diff "Мене двічі списали гроші за підписку"  # bare vs refined prompt, side by side
uv run 02-prompting-craft/prompt_iteration.py                     # the lesson's 6 revision passes, live
```

Details, sample output, and how to iterate on the prompt: see [`02-prompting-craft/README.md`](02-prompting-craft/README.md).

### Module 04 — Tool-use and Schema Design

```bash
uv run 04-tool-use-schema-design/1_simple_loop.py        # basic tool-use loop
uv run 04-tool-use-schema-design/2_parallel_calls.py     # multiple tools in one turn
uv run 04-tool-use-schema-design/3_schema_design.py      # good vs bad schema, proven with live calls
uv run 04-tool-use-schema-design/4_ticket_escalation.py  # real-world: classify → escalate
uv run 04-tool-use-schema-design/5_error_handling.py     # handling tool failures
uv run 04-tool-use-schema-design/6_boundary_case_failure.py  # named failure mode: overlapping descriptions at a boundary
uv run 04-tool-use-schema-design/7_mcp_connector.py      # MCP Connector — schemas written by someone else (expensive, don't loop)
uv run 04-tool-use-schema-design/8_id_mismatch_bug.py    # triggers + fixes a real mismatched tool_use_id error
uv run 04-tool-use-schema-design/9_agent_sdk_builtin_loop.py  # claude-agent-sdk's built-in loop vs. #1's manual loop — needs the `claude` CLI installed too
```

Details per example: see [`04-tool-use-schema-design/README.md`](04-tool-use-schema-design/README.md).

### Module 03 — Extended Thinking

```bash
uv run 03-extended-thinking/1_basic_thinking.py              # thinking block + final answer
uv run 03-extended-thinking/2_thinking_budget_comparison.py  # small vs large budget_tokens
```

Details: see [`03-extended-thinking/README.md`](03-extended-thinking/README.md).

### Module 05 — Streaming Responses

```bash
uv run 05-streaming-responses/1_basic_streaming.py           # text_stream helper
uv run 05-streaming-responses/2_streaming_with_progress.py   # raw events + token tracking
```

Details: see [`05-streaming-responses/README.md`](05-streaming-responses/README.md).

### Module 06 — Context Engineering

```bash
uv run 06-context-engineering/1_context_window_growth.py     # watch input_tokens climb turn over turn
uv run 06-context-engineering/2_compaction.py                 # same task, summarized tool results
uv run 06-context-engineering/3_context_failure_diagnosis.py  # checkpoint 5: degrading tool selection from context bloat
```

Details: see [`06-context-engineering/README.md`](06-context-engineering/README.md).

### Module 07 — Agent Architecture

```bash
uv run 07-agent-architecture/1_workflow_vs_agent.py  # fixed workflow vs. Claude-driven agent loop
uv run 07-agent-architecture/2_over_tooling.py       # tool selection quality vs. tool surface size
uv run 07-agent-architecture/3_exit_conditions.py    # relying on Claude to stop vs. a designed exit condition
```

Details: see [`07-agent-architecture/README.md`](07-agent-architecture/README.md).

### Module 08 — Human-in-the-Loop

```bash
uv run 08-human-in-the-loop/1_approval_gate.py         # dangerous tool calls pause for approval
uv run 08-human-in-the-loop/2_hitl_insertion_points.py # plan review + unexpected-output checkpoints
```

Details: see [`08-human-in-the-loop/README.md`](08-human-in-the-loop/README.md).

### Module 09 — Memory

```bash
uv run 09-memory/1_session_vs_persistent_memory.py     # session memory vs. file-backed persistent memory
uv run 09-memory/2_memory_scope_comparison.py          # matching use case to memory scope, token growth measured live
uv run 09-memory/3_skills_on_demand_vs_always_on.py    # on-demand Skill loading vs. always-on CLAUDE.md-style instructions
```

Details: see [`09-memory/README.md`](09-memory/README.md).

### Module 10 — Files API

```bash
uv run 10-files-api/1_files_api_basics.py  # upload once, reference by file_id across requests
```

Details: see [`10-files-api/README.md`](10-files-api/README.md).

### Module 11 — Message Batches API

```bash
uv run 11-message-batches/1_message_batches.py  # submit, poll, and retrieve an async batch
```

Details: see [`11-message-batches/README.md`](11-message-batches/README.md).

### Module 12 — Managed Agents

```bash
uv run 12-managed-agents/1_agent_and_session_basics.py     # agent (once) -> session (every run); bash runs in Anthropic's sandbox
uv run 12-managed-agents/2_custom_tool_managed_agent.py     # same weather task, third transport: session events instead of tool_use blocks
```

Requires Managed Agents beta access on your workspace — both scripts catch a 403/404 and print a note if it isn't enabled yet. Each session provisions a real sandbox container, so these take longer and cost a bit more than the other examples in this repo.

Details: see [`12-managed-agents/README.md`](12-managed-agents/README.md).

---

## 🔧 Common Tasks

### Try a different model
Edit `.env`:
```
CLAUDE_MODEL=claude-opus-5      # Best quality, slower
CLAUDE_MODEL=claude-sonnet-5    # Balanced
CLAUDE_MODEL=claude-haiku-4-5   # Fast, cheaper (default)
```

### Starting a new module
```bash
mkdir 05-streaming-responses
# add a README.md with the lesson's key takeaways + screen reference
# add example scripts as you go
```

---

## 🐛 Troubleshooting

**API key not found:**
```
Error: "Could not resolve authentication method"
```
→ Check `.env` exists and `ANTHROPIC_API_KEY=sk-ant-...` is set

**Module not found:**
```
ModuleNotFoundError: No module named 'anthropic'
```
→ Run `uv sync` first

**Tool examples fail:**
→ Make sure you have API quota and internet connection

---

## 📝 What to Try Next

- Write your own system prompt for a different task in `02-prompting-craft/`
- Add more test cases to `02-prompting-craft/examples.json`
- Modify a tool schema in `04-tool-use-schema-design/3_schema_design.py` and see if Claude still picks it correctly
- Read the [Claude API docs](https://docs.anthropic.com) for more advanced patterns
