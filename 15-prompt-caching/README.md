# Module 15 — Prompt Caching: Threshold & TTL

Every request reprocesses its entire input from scratch, including
whatever was identical on the last request. Prompt caching lets a stable
prefix — a system prompt, a tool list, a long reference document — get
processed once and reused on follow-up requests at a fraction of the
cost. You opt a block in with `cache_control: {"type": "ephemeral"}` on
the last block you want cached; everything up to and including that
block is what gets cached.

Two constraints decide whether that actually saves you anything, and
both are easy to trip over silently (no error either way): a **minimum
token threshold** the cached segment must clear, and a **TTL** the
cached entry expires after. This module is one live script that puts
real numbers on both.

## Files

```
15-prompt-caching/
├── README.md
└── 1_cache_threshold_and_ttl.py
```

### 1️⃣ `1_cache_threshold_and_ttl.py` — Threshold, Write/Read, Invalidation, TTL

```bash
uv run 15-prompt-caching/1_cache_threshold_and_ttl.py
```

**What it does**, in order:

1. **Below the threshold:** a ~15-token system prompt with a
   `cache_control` breakpoint on it. `cache_creation_input_tokens` comes
   back `0` — the breakpoint was silently ignored, no error. The lesson's
   1,024-token figure is "for most current models"; some (e.g. Haiku)
   need more, which is exactly why this demo pads generously (~3,000+
   tokens) everywhere else instead of hugging the line.
2. **Write, then read:** the same padded system prompt (a fake "project
   conventions" block standing in for a real `CLAUDE.md` or a stack of
   MCP tool schemas — the lesson's own example of what pushes real
   context past the threshold) sent twice back to back. Call A pays a
   cache **write**; Call B, sent immediately after with an identical
   prefix, gets a cache **read** at a fraction of the cost.
3. **Prefix invalidation:** the same prompt with one letter capitalized
   near the start. Fresh `cache_creation_input_tokens`, not a read — a
   single-character change before the breakpoint is a full miss, not a
   partial one.
4. **1-hour TTL:** the same shape of prompt, this time with
   `cache_control: {"type": "ephemeral", "ttl": "1h"}` and the
   `extended-cache-ttl-2025-04-11` beta header. `response.usage` exposes
   a nested `cache_creation` object with `ephemeral_5m_input_tokens` /
   `ephemeral_1h_input_tokens` — this call lands in the 1h bucket.

**Key concepts:**
- The threshold failure mode is silent: no exception, no warning — the
  only tell is `cache_creation_input_tokens` staying at `0` on something
  you expected to cache. Check usage, don't assume.
- Caching is **content-addressed**, not session-addressed: the cache
  entry from demo 2 is still live (server-side) if you re-run this whole
  script again within 5 minutes, so demo 2's "Call A" will show a
  **read**, not a write, on a quick second run. That's not a bug in the
  script — it's the same sliding-window behavior demo 2 is showing you,
  just visible a run later than you might expect.
- Demo 3 deliberately mutates a letter **near the start** of the block,
  not trailing whitespace at the very end — a trailing-whitespace-only
  change can tokenize identically to the original and still hit the old
  cache, which would make the demo lie about what "prefix stability"
  means. An early, meaningful edit can't be normalized away.
- Demo 4 uses a **different** padded prompt than demos 2–3
  (`PADDED_SYSTEM_1H`), not the same one with `ttl: "1h"` tacked on.
  Caching keys on exact prefix content, not on the ttl you request on a
  given call — asking for `ttl: "1h"` against a prefix already cached
  under the 5-minute default just reads that existing entry; it does not
  retroactively upgrade it. Landing in the 1h bucket at all requires the
  content to be new (or its old cache to have already expired).
- Cost picture from a live run (Haiku, ~5,100-token cached block): a
  cache **write** costs somewhat more than an uncached call over the
  same tokens; a cache **read** on the same tokens costs roughly a tenth
  as much. Multiply that gap by every request in a long session and the
  reason to keep the cacheable prefix first and stable becomes concrete
  rather than theoretical.

**When to reach for `ttl: "1h"` vs. the 5-minute default:** match it to
your reply cadence, not a fixed rule. Rapid back-and-forth (a debugging
loop sending a message every minute or two) never lets the 5-minute
window lapse, so the default is free performance with nothing to
configure. A slower loop — Claude Code produces a large plan or a diff
and you spend 15–30 minutes actually reading it, running it, or manually
tweaking before replying — will blow past 5 minutes on the very first
gap, forcing a full-price rewrite for zero read benefit; that's the case
`ttl: "1h"` is for, at the cost of a pricier write if the prefix goes
unused for the full hour.

## What's *not* re-demonstrated here

- **Where to put the breakpoint** (after tools, before the system
  prompt, before dynamic messages) and the 4-breakpoint limit are config
  choices, not something a script output can show — see the lesson text.
  The practical version of "keep static content first, dynamic content
  last" is already visible in this script: the system block carries the
  breakpoint, the per-call user message never does.
- **The API's MCP Connector** and its own context-cost knobs
  (`defer_loading`, per-tool `enabled`) — covered in
  [`04-tool-use-schema-design/7_mcp_connector.py`](../04-tool-use-schema-design/7_mcp_connector.py).
  That script is itself a good example of the "large tool list" case
  this module's padded prompt stands in for.
