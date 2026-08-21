# Module 05 — Streaming Responses

Course section: *Production-Grade Prompting, Agents & Tool Use → Streaming Responses*

## Files

| File | Purpose |
|---|---|
| `1_basic_streaming.py` | The `client.messages.stream()` helper — print text as it arrives, get the final message after |
| `2_streaming_with_progress.py` | Raw stream events (`content_block_delta`, `message_delta`, ...) and tracking token usage live |
| `3_streaming_tool_use_json_deltas.py` | Reconstructing a streamed tool call's input from `input_json_delta` fragments — the naive per-fragment parse that fails vs. the concatenate-then-parse fix |

## Run it

```bash
uv run 05-streaming-responses/1_basic_streaming.py
uv run 05-streaming-responses/2_streaming_with_progress.py
uv run 05-streaming-responses/3_streaming_tool_use_json_deltas.py
```

## Key concepts

- `client.messages.stream(...)` used as a context manager gives you `stream.text_stream` — iterate it to print tokens as Claude generates them, instead of waiting for the whole response.
- `stream.get_final_message()` returns the complete `Message` once streaming finishes (including `usage`) — you don't need to manually concatenate the streamed chunks yourself.
- Under the hood, streaming sends a sequence of typed events: `message_start` → `content_block_start` → repeated `content_block_delta` → `content_block_stop` → `message_delta` → `message_stop`. `2_streaming_with_progress.py` iterates these directly instead of using `text_stream`.
- Streaming is required (or at least strongly recommended) once `max_tokens` gets large, since long non-streaming requests can hit HTTP timeouts.
- When Claude streams a tool call, its input arrives as a `tool_use` content block built up from `content_block_delta` events with `delta.type == "input_json_delta"` — each carrying a `partial_json` **string fragment**, not a standalone JSON value. A fragment can end mid-string (e.g. `'{"city":"San'`). Parsing each fragment on its own throws; the fix is to concatenate fragments per content-block index in arrival order and parse once, at `content_block_stop` — or just use `client.messages.stream()`'s `get_final_message()`, which does exactly that internally and hands back a `tool_use` block with `.input` already a parsed dict. `3_streaming_tool_use_json_deltas.py` reproduces the failure live, then shows both the manual and SDK-helper fixes.

## Try this while studying

- Compare wall-clock time: run the same prompt through `05-streaming-responses/1_basic_streaming.py` vs. a non-streaming `client.messages.create()` call — streaming won't finish faster overall, but the *first token* appears much sooner.
- In `2_streaming_with_progress.py`, print every event's `.type` as it arrives to see the full event sequence for a real request.
- In `3_streaming_tool_use_json_deltas.py`, try a tool argument likely to land entirely in one chunk (a one-word city) vs. one likely to split (a long address) — chunking isn't guaranteed to break mid-string on every call, which is exactly why per-fragment parsing is unsafe even when it happens not to fail on a given run.
- Log your takeaway in [`NOTES.md`](../NOTES.md).
