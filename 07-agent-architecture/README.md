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
