# Claude API practice — prompt runner

A small, generic harness for practicing prompt design against the Claude API: define a system prompt, throw example inputs at it, see the JSON (or plain text) result.

## Files

- `process_ticket.py` — the runner. Loads `system_prompt.txt`, sends it plus a user input to Claude, prints the result. Pretty-prints if the response is JSON.
- `system_prompt.txt` — the system prompt. Edit this to try different tasks.
- `examples.json` — a list of example user inputs to run against the current system prompt. Add your own.
- `.env` — your API key (not committed to git).

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (see `pyproject.toml`):

```bash
uv sync
```

Edit `.env` and set your key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
uv run process_ticket.py                # runs the first example in examples.json
uv run process_ticket.py "some input"    # runs your own input
uv run process_ticket.py --all           # runs every example in examples.json
```

## Things to try

- Rewrite `system_prompt.txt` for a completely different task (classification, extraction, rewriting, translation) and add matching examples to `examples.json`.
- Swap the model via `CLAUDE_MODEL` in `.env` (`claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`) and compare speed/quality/cost.
- Swap `client.messages.create` for `client.messages.parse` with a JSON schema (`output_config.format`) to enforce strict structured output instead of relying on prompt instructions alone.
