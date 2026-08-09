"""
EXAMPLE 1: Session Memory vs. Persistent Memory

Session memory lives only in the current conversation's `messages` list —
it disappears the moment the process exits or a new conversation starts.
Persistent memory is written to storage OUTSIDE the context window (here,
a JSON file) so it survives across separate sessions, without needing to
resend the entire prior conversation as context every time.

This example shows both: a fact learned mid-conversation (session memory,
gone once we start a fresh `messages` list) vs. a fact explicitly written
to a memory file that a brand new conversation can read back.
"""

import json
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

MEMORY_FILE = Path(__file__).resolve().parent / "memory_store.json"


def demo_session_memory():
    """A fact Claude learns mid-conversation is available for the REST of
    that conversation (it's just earlier text in `messages`), but a brand
    new conversation has no access to it at all."""
    print("\n" + "=" * 70)
    print("SESSION MEMORY: available only within one messages[] list")
    print("=" * 70)

    messages = [
        {"role": "user", "content": "Remember this for our conversation: my preferred deploy environment is staging, not production."},
    ]
    r1 = client.messages.create(model="claude-haiku-4-5", max_tokens=100, messages=messages)
    print_usage(r1)
    messages.append({"role": "assistant", "content": r1.content})
    print(f"Turn 1: {r1.content[0].text}")

    messages.append({"role": "user", "content": "Where should I deploy my next change?"})
    r2 = client.messages.create(model="claude-haiku-4-5", max_tokens=100, messages=messages)
    print_usage(r2)
    print(f"Turn 2 (same conversation): {r2.content[0].text}")

    print("\n--- Starting a BRAND NEW conversation (fresh messages[]) ---")
    fresh_messages = [{"role": "user", "content": "Where should I deploy my next change?"}]
    r3 = client.messages.create(model="claude-haiku-4-5", max_tokens=100, messages=fresh_messages)
    print_usage(r3)
    print(f"Fresh conversation: {r3.content[0].text}")
    print("\n📝 The preference is gone — it only ever existed as text inside the old messages[] list.")


def demo_persistent_memory():
    """A fact is written to a file (outside the context window entirely).
    A brand new conversation can read the file and inject it as context —
    the model didn't 'remember' anything; OUR code re-supplied the fact."""
    print("\n" + "=" * 70)
    print("PERSISTENT MEMORY: written to storage, survives new sessions")
    print("=" * 70)

    # "Session A": learn a fact, write it to persistent storage ourselves.
    memory = {"preferred_deploy_environment": "staging"}
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))
    print(f"Wrote to {MEMORY_FILE.name}: {memory}")

    # "Session B": a brand new conversation, but our code reads the memory
    # file first and puts it into the system prompt before the first turn.
    print("\n--- Starting a BRAND NEW conversation, but loading memory_store.json first ---")
    stored = json.loads(MEMORY_FILE.read_text())
    system_prompt = f"Known user preferences (from persistent memory): {json.dumps(stored)}"

    r = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        system=system_prompt,
        messages=[{"role": "user", "content": "Where should I deploy my next change?"}],
    )
    print_usage(r)
    print(f"Fresh conversation + injected memory: {r.content[0].text}")
    print("\n📝 The model has no memory of its own — our code re-read the file and put the")
    print("   fact back into context via the system prompt. That's the entire mechanism.")

    MEMORY_FILE.unlink(missing_ok=True)


def main():
    demo_session_memory()
    demo_persistent_memory()

    print("""
======================================================================
KEY TAKEAWAY
======================================================================
Claude has no memory between separate API calls or conversations by
itself — every "memory" is actually just text that ends up back in the
context window somehow:
  - Session memory: earlier turns in the SAME `messages[]` list.
  - Persistent memory: facts your application stores outside the context
    window (file, database, key-value store) and re-injects — usually via
    the system prompt or an early user turn — the next time it's relevant.

The design question is never "how does Claude remember" — it's "what do
we store, where, and how do we decide what to re-inject and when."
""")


if __name__ == "__main__":
    main()
