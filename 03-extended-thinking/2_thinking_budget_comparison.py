"""
EXAMPLE 2: Extended Thinking — Budget Comparison

budget_tokens controls how much Claude is allowed to "think" before answering.
This runs the same hard question at a small and a large budget so you can
compare thinking depth and answer quality side by side.

Key: budget_tokens must be strictly less than max_tokens.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

QUESTION = (
    "Five suspects — Alice, Bob, Carol, Dave, and Eve — are questioned about a theft. "
    "Exactly one of them is telling the truth; the other four are lying.\n"
    "Alice says: 'Bob did it.'\n"
    "Bob says: 'Alice did it.'\n"
    "Carol says: 'I did not do it.'\n"
    "Dave says: 'Eve did it.'\n"
    "Eve says: 'Bob did it.'\n"
    "Who stole it, and who is the one telling the truth? Check every case carefully "
    "before answering."
)

BUDGETS = [1024, 3072]


def ask_with_budget(budget_tokens):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=budget_tokens + 2048,
        thinking={"type": "enabled", "budget_tokens": budget_tokens},
        messages=[{"role": "user", "content": QUESTION}],
    )
    print_usage(response)
    thinking = next((b.thinking for b in response.content if b.type == "thinking"), "")
    text = next((b.text for b in response.content if b.type == "text"), "")
    return thinking, text


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Thinking Budget Comparison")
    print("=" * 70)
    print(f"\nQuestion: {QUESTION}")

    for budget in BUDGETS:
        thinking, text = ask_with_budget(budget)
        print(f"\n--- budget_tokens={budget} ---")
        print(f"Thinking length: {len(thinking)} chars")
        print(f"Answer: {text}")


if __name__ == "__main__":
    main()
