"""
EXAMPLE 1: Extended Thinking — Basic Usage

Extended thinking lets Claude reason step-by-step before answering, in a
separate `thinking` content block you can inspect.

haiku-4-5 uses the classic form: thinking={"type": "enabled", "budget_tokens": N}.
budget_tokens must be less than max_tokens (and at least 1024).

Key: response.content contains both a "thinking" block and a "text" block.
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Extended Thinking — Basic Usage")
    print("=" * 70)

    question = "A train leaves city A at 60mph. Another leaves city B, 300 miles away, at 90mph, heading toward the first. How long until they meet?"

    print(f"\n📨 Question: {question}")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        thinking={"type": "enabled", "budget_tokens": 1024},
        messages=[{"role": "user", "content": question}],
    )

    for block in response.content:
        if block.type == "thinking":
            print("\n🧠 Thinking:")
            print(f"   {block.thinking}")
        elif block.type == "text":
            print("\n✅ Answer:")
            print(f"   {block.text}")

    print(f"\n📊 Stop reason: {response.stop_reason}")


if __name__ == "__main__":
    main()
