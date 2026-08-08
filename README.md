# Claude API Learning Project

A hands-on companion for the Anthropic **Production-Grade Prompting, Agents & Tool Use** certification. Each folder maps to a course module — run the code for a module while you're on its lesson screens.

---

## 📖 Course Map

| Module | Course Section | Folder | Status |
|---|---|---|---|
| 01 | MSO Foundations *(separate course track)* | [`01-mso-foundations/`](01-mso-foundations/) | ✅ |
| 02 | Prompting Craft | [`02-prompting-craft/`](02-prompting-craft/) | ✅ |
| 03 | Extended Thinking | [`03-extended-thinking/`](03-extended-thinking/) | ✅ |
| 04 | Tool-use and Schema Design | [`04-tool-use-schema-design/`](04-tool-use-schema-design/) | ✅ |
| 05 | Streaming Responses | [`05-streaming-responses/`](05-streaming-responses/) | ✅ |

As you reach a new module in the course, create `NN-module-name/` and add examples there — folder order should always match the course sidebar order.

Keep a running log of screen-by-screen takeaways in [`NOTES.md`](NOTES.md) as you go — it doubles as a study guide later.

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
│   ├── 1_simple_loop.py
│   ├── 2_parallel_calls.py
│   ├── 3_schema_design.py
│   ├── 4_ticket_escalation.py
│   └── 5_error_handling.py
├── 05-streaming-responses/
│   ├── README.md
│   ├── 1_basic_streaming.py
│   └── 2_streaming_with_progress.py
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
git clone <this-repo-url>
cd "claude cert"
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
uv run 04-tool-use-schema-design/3_schema_design.py      # good vs bad schema (no API calls)
uv run 04-tool-use-schema-design/4_ticket_escalation.py  # real-world: classify → escalate
uv run 04-tool-use-schema-design/5_error_handling.py     # handling tool failures
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
