"""
EXAMPLE 2: Prompting Modes — System Prompt vs. Plain User Turn vs. Multi-Turn

Three ways to shape a conversation with the Messages API:
1. No system prompt — Claude answers with its default persona/behavior
2. A system prompt — sets persistent behavior for the whole conversation
3. Multi-turn — prior messages become context for later ones

Key: `system` is a separate top-level parameter, not a message in the
`messages` list. Conversation history (multi-turn) is just prior
user/assistant messages sent back on every request — the API is stateless.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

QUESTION = "What's the best way to learn a new programming language?"


def mode_1_no_system():
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=150,
        messages=[{"role": "user", "content": QUESTION}],
    )
    print_usage(response)
    return response.content[0].text


def mode_2_with_system():
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=150,
        system="You are a blunt, no-nonsense senior engineer. Answer in exactly one short paragraph, no pleasantries.",
        messages=[{"role": "user", "content": QUESTION}],
    )
    print_usage(response)
    return response.content[0].text


def mode_3_multi_turn():
    messages = [
        {"role": "user", "content": "I already know Python well."},
        {"role": "assistant", "content": "Good to know — that gives you a strong base for control flow, functions, and OOP concepts."},
        {"role": "user", "content": QUESTION},
    ]
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=150,
        messages=messages,
    )
    print_usage(response)
    return response.content[0].text


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Prompting Modes")
    print("=" * 70)
    print(f"\nQuestion: {QUESTION}")

    print("\n--- Mode 1: No system prompt ---")
    print(mode_1_no_system())

    print("\n--- Mode 2: With a system prompt (persona + constraints) ---")
    print(mode_2_with_system())

    print("\n--- Mode 3: Multi-turn (Claude already knows I know Python) ---")
    print(mode_3_multi_turn())


if __name__ == "__main__":
    main()
