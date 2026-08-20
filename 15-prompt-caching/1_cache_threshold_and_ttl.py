"""
EXAMPLE 1: Prompt Caching — the 1,024-Token Threshold and the TTL Trap

Prompt caching exists to stop you from paying to reprocess the same
static prefix on every request. You opt a block into caching by adding
cache_control: {"type": "ephemeral"} to it; everything up to and
including that block gets cached. But two constraints decide whether you
actually see savings:

  1. THRESHOLD — the cached segment must exceed a minimum token count
     (1,024 tokens for most current models; some models require more,
     e.g. Haiku needs ~2,048). Below it, the breakpoint is silently a
     no-op: no error, no cache_creation_input_tokens, full price every
     time.
  2. TTL — a cache hit only happens within the cache's lifetime. The
     default is 5 minutes, reset on every read (sliding window). An
     opt-in ttl: "1h" survives longer gaps (e.g. reading a generated
     plan, running local tests) at a higher write cost.

This script demonstrates both with live calls, using response.usage's
cache_creation_input_tokens / cache_read_input_tokens fields as the
ground truth for whether a hit actually happened — printed via
common.usage.print_usage.

Cost note: every call below reuses the same padded system prompt
(~3,000 tokens) so it's comfortably above every model's threshold. Total
cost for a full run is a fraction of a cent on Haiku.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5"

# A short system prompt: comfortably under the 1,024-token threshold.
BELOW_THRESHOLD_SYSTEM = (
    "You are a terse assistant. Answer every question in one sentence."
)

# A padded system prompt standing in for a "solid CLAUDE.md" or a stack of
# MCP tool schemas — the lesson's own example of what pushes real-world
# context past the threshold. Repeated on purpose to comfortably clear
# ~3,000 tokens regardless of which model's threshold applies.
_CONVENTION = (
    "- Prefer editing existing files to creating new ones; do not add "
    "speculative abstractions or config flags for cases that cannot "
    "currently happen; keep functions small and name them for what they "
    "return, not how they compute it; write no comments unless a WHY is "
    "genuinely non-obvious, since well-named identifiers already say "
    "what the code does; validate only at system boundaries and trust "
    "internal invariants elsewhere.\n"
)
PADDED_SYSTEM = "Project conventions:\n" + (_CONVENTION * 60)

# A distinct padded prompt for the 1h-TTL demo. Caching keys on exact
# content, not on the ttl you request — reusing PADDED_SYSTEM here would
# just read the 5m-bucket entry demo 2 already wrote instead of writing a
# fresh 1h-bucket one, which would hide the thing this demo is showing.
PADDED_SYSTEM_1H = "Project conventions (1h-ttl variant):\n" + (_CONVENTION * 60)


def demo_below_threshold():
    print("\n" + "=" * 70)
    print("1. Below the 1,024-token threshold: the breakpoint is a no-op")
    print("=" * 70)
    print(f"System prompt length: {len(BELOW_THRESHOLD_SYSTEM)} chars (well under 1,024 tokens)")

    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=[
            {
                "type": "text",
                "text": BELOW_THRESHOLD_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": "What is 2+2?"}],
    )
    print_usage(response, model=MODEL)
    print(
        "Note: cache_creation_input_tokens is 0 (or absent) above — Claude "
        "never cached this block. No error was raised; the breakpoint was "
        "just too small to matter."
    )


def demo_write_then_read():
    print("\n" + "=" * 70)
    print("2. Above the threshold: write once, read on the next identical call")
    print("=" * 70)
    print(f"System prompt length: {len(PADDED_SYSTEM)} chars (~3,000+ tokens)")

    print("\n-- Call A (expect a cache WRITE) --")
    response_a = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=[
            {
                "type": "text",
                "text": PADDED_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": "Summarize the conventions in one sentence."}],
    )
    print_usage(response_a, model=MODEL)

    print("\n-- Call B, same prefix, sent right away (expect a cache READ) --")
    response_b = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=[
            {
                "type": "text",
                "text": PADDED_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": "Now summarize them in exactly five words."}],
    )
    print_usage(response_b, model=MODEL)
    print(
        "\nNote: Call B's cache_read_input_tokens should roughly match Call "
        "A's cache_creation_input_tokens, at a fraction of the cost. Every "
        "read like this also resets the 5-minute TTL clock — that's the "
        "'sliding window' the lesson describes: as long as consecutive "
        "requests stay under 5 minutes apart, the cache never goes cold."
    )


def demo_prefix_invalidation():
    print("\n" + "=" * 70)
    print("3. Prefix stability: one changed character before the breakpoint")
    print("=" * 70)

    # Mutate one character in the middle of the block, not at the very end:
    # a trailing whitespace change can get normalized away during
    # tokenization and still hit the old cache, which would defeat the
    # point of this demo. An early, meaningful character change can't.
    mutated_system = PADDED_SYSTEM.replace("Project conventions:", "Project Conventions:", 1)
    print("Capitalizing one letter near the start of the cached system block...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=[
            {
                "type": "text",
                "text": mutated_system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": "Summarize the conventions in one sentence."}],
    )
    print_usage(response, model=MODEL)
    print(
        "Note: this should show a fresh cache WRITE, not a read, even "
        "though the content is functionally identical to demo 2's prompt "
        "and was sent moments later. Caching matches bytes up to the "
        "breakpoint exactly — it does not know the change was trivial."
    )


def demo_1h_ttl():
    print("\n" + "=" * 70)
    print("4. Opting into a 1-hour TTL for slow review loops")
    print("=" * 70)
    print(
        "Requires the 'extended-cache-ttl-2025-04-11' beta header — check "
        "current docs, this may have graduated out of beta by the time "
        "you read this."
    )

    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=100,
        betas=["extended-cache-ttl-2025-04-11"],
        system=[
            {
                "type": "text",
                "text": PADDED_SYSTEM_1H,
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            }
        ],
        messages=[{"role": "user", "content": "Summarize the conventions in one sentence."}],
    )
    print_usage(response, model=MODEL)

    cache_creation = getattr(response.usage, "cache_creation", None)
    if cache_creation:
        print(
            f"cache_creation breakdown: "
            f"{getattr(cache_creation, 'ephemeral_5m_input_tokens', 0)} tokens "
            f"in the 5m bucket, "
            f"{getattr(cache_creation, 'ephemeral_1h_input_tokens', 0)} tokens "
            f"in the 1h bucket."
        )
    print(
        "\nWhy this matters: a 5-minute default would evict this same "
        "prefix during a 15-30 minute pause to read a generated plan or "
        "run local tests — the next message pays a full write for no read "
        "benefit. ttl: '1h' survives that gap. It costs more to write "
        "(higher than the already-higher 5m write premium), so reserve it "
        "for prefixes you expect to actually still be reading from later, "
        "not every request by default."
    )
    print(
        "\nWhy this demo uses PADDED_SYSTEM_1H instead of PADDED_SYSTEM: "
        "the cache is keyed on exact prefix content, not on the ttl you "
        "declare on a given call. Requesting ttl: '1h' against a prefix "
        "already cached (from demo 2/3, under the 5m default) just reads "
        "that existing entry — it does not retroactively upgrade it to "
        "1h. To actually land in the 1h bucket, the content has to be new "
        "or its cache must have already expired."
    )


def main():
    demo_below_threshold()
    demo_write_then_read()
    demo_prefix_invalidation()
    demo_1h_ttl()


if __name__ == "__main__":
    main()
