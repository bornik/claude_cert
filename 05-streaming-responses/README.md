# Module 05 — Streaming Responses

Course section: *Production-Grade Prompting, Agents & Tool Use → Streaming Responses*

## Files

| File | Purpose |
|---|---|
| `1_basic_streaming.py` | The `client.messages.stream()` helper — print text as it arrives, get the final message after |
| `2_streaming_with_progress.py` | Raw stream events (`content_block_delta`, `message_delta`, ...) and tracking token usage live |

## Run it

```bash
uv run 05-streaming-responses/1_basic_streaming.py
uv run 05-streaming-responses/2_streaming_with_progress.py
```

## Key concepts

- `client.messages.stream(...)` used as a context manager gives you `stream.text_stream` — iterate it to print tokens as Claude generates them, instead of waiting for the whole response.
- `stream.get_final_message()` returns the complete `Message` once streaming finishes (including `usage`) — you don't need to manually concatenate the streamed chunks yourself.
- Under the hood, streaming sends a sequence of typed events: `message_start` → `content_block_start` → repeated `content_block_delta` → `content_block_stop` → `message_delta` → `message_stop`. `2_streaming_with_progress.py` iterates these directly instead of using `text_stream`.
- Streaming is required (or at least strongly recommended) once `max_tokens` gets large, since long non-streaming requests can hit HTTP timeouts.

## Try this while studying

- Compare wall-clock time: run the same prompt through `05-streaming-responses/1_basic_streaming.py` vs. a non-streaming `client.messages.create()` call — streaming won't finish faster overall, but the *first token* appears much sooner.
- In `2_streaming_with_progress.py`, print every event's `.type` as it arrives to see the full event sequence for a real request.
- Log your takeaway in [`NOTES.md`](../NOTES.md).
