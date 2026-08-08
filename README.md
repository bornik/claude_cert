# Claude API Learning Project

A hands-on project for learning Claude API features: prompt engineering, tool-use loops, schema design, and structured output.

---

## 📁 Project Structure

### Core Files

| File | Purpose | Edit to... |
|------|---------|-----------|
| **`process_ticket.py`** | Prompt runner — support ticket classifier | Test different system prompts and examples |
| **`system_prompt.txt`** | System prompt for ticket classification | Change the task (extraction, translation, etc.) |
| **`examples.json`** | Sample inputs for `process_ticket.py` | Add your own test cases |

### Learning Files

| File | Purpose | What to learn |
|------|---------|---------------|
| **`docs/tool-use-guide.html`** | Interactive visual guide | Overview of tool-use concepts (open in browser) |
| **`examples/`** | Individual example scripts (1-5) | Each tool-use concept in isolation |

### Configuration

| File | Purpose |
|------|---------|
| **`.env`** | API key (create from `.env.example`) |
| **`pyproject.toml`** | Dependencies (Python, Anthropic SDK) |

---

## 🚀 Setup

### 1. Install dependencies
```bash
uv sync
```

### 2. Configure API key
Copy `.env.example` to `.env` and add your key:
```bash
cp .env.example .env
# Then edit .env:
# ANTHROPIC_API_KEY=sk-ant-...
```

---

## 📚 Usage

### Quick Start: Prompt Runner

Run the support ticket classifier on example inputs:

```bash
# Run first example
uv run process_ticket.py

# Run custom input
uv run process_ticket.py "My API key stopped working"

# Run all examples
uv run process_ticket.py --all
```

**What it does:** Loads a system prompt, sends it with your input to Claude, pretty-prints JSON results.

---

### Learning Tool-Use

Explore how Claude calls tools, not just generates text:

```bash
# Run individual examples (one concept per file)
uv run examples/1_simple_loop.py        # Basic tool-use loop
uv run examples/2_parallel_calls.py     # Multiple tools in one turn
uv run examples/3_schema_design.py      # Good vs bad schema (no API calls)
uv run examples/4_ticket_escalation.py  # Real-world: classify → escalate
uv run examples/5_error_handling.py     # Handling tool failures
```

---

## 🧪 Examples Explained

### `process_ticket.py` — Support Ticket Classifier
- **What:** Reads a support ticket, outputs JSON with category + urgency
- **System prompt:** `system_prompt.txt`
- **Test cases:** `examples.json`
- **How to modify:** Change the system prompt to classify emails, extract data, translate, etc.

**Example run:**
```bash
$ uv run process_ticket.py "Our team is locked out and demo is in 20 minutes"
{
  "category": "technical",
  "urgency": "critical",
  "summary": "Team account lockout blocking client demo"
}
```

---

### `examples/` Directory — One Concept Per File

Five progressively advanced examples, each file is standalone and runnable:

```
examples/
├── 1_simple_loop.py          # Basic: define tool → call → result
├── 2_parallel_calls.py       # Multiple tools in one response
├── 3_schema_design.py        # Good vs bad schema comparison
├── 4_ticket_escalation.py    # Dependent tool calls (classify → escalate)
└── 5_error_handling.py       # is_error flag and retries
```

Run any individually to understand one pattern:
```bash
uv run examples/1_simple_loop.py
```

---

## 🔧 Common Tasks

### Try a different model
Edit `.env`:
```
CLAUDE_MODEL=claude-opus-5      # Best quality, slower
CLAUDE_MODEL=claude-sonnet-5    # Balanced
CLAUDE_MODEL=claude-haiku-4-5   # Fast, cheaper (default)
```

### Change the task
Edit `system_prompt.txt` and add test cases to `examples.json`:

```bash
# Example: change from ticket classification to email summarization
nano system_prompt.txt
nano examples.json
uv run process_ticket.py --all
```

### Compare prompt versions
Keep multiple versions:
```bash
cp system_prompt.txt system_prompt_v1.txt
# Edit system_prompt.txt
uv run process_ticket.py --all
# Compare results
```

### Use structured output (no tool-use)
```python
# Instead of relying on prompt + parsing, use Claude's built-in JSON mode
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    system="You are a ticket classifier",
    messages=[...],
    # Add this for strict JSON:
    response_format={"type": "json_object"}
)
```

---

## 📖 Learning Path

1. **Start here:** Open `docs/tool-use-guide.html` in your browser — visual overview of all concepts
2. **Then:** `uv run process_ticket.py --all` — see prompts in action
3. **Then:** `uv run examples/1_simple_loop.py` — understand the tool-use loop
4. **Then:** `uv run examples/2_parallel_calls.py` — see why schemas matter
5. **Then:** `uv run examples/4_ticket_escalation.py` — real multi-step flow
6. **Finally:** Read comments in `examples/` code — understand why design choices matter

---

## 🎯 Key Concepts

| Concept | File | Example |
|---------|------|---------|
| System prompts | `system_prompt.txt` | "You are a support ticket processor..." |
| Structured input | `examples.json` | Array of test cases |
| Tool schemas | `examples/3_schema_design.py` | How Claude picks tools |
| Tool-use loops | `examples/1_simple_loop.py` | Request → tool call → result → continue |
| Error handling | `examples/5_error_handling.py` | `is_error: True` |

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

- Write your own system prompt for a different task
- Add more examples to `examples.json`
- Modify a tool schema in `examples/3_schema_design.py` and see if Claude still picks it correctly
- Read the [Claude API docs](https://docs.anthropic.com) for more advanced patterns
