"""
EXAMPLE 1: Non-Determinism — Same Prompt, Different Output

This is exactly the quiz question from the course: "two identical prompts
must return identical text" — false. Claude samples each next token from a
probability distribution, so wording can vary even when both answers are
correct.

Key: this is why you shouldn't rely on exact string matching against model
output — check for the underlying meaning/structure instead (see the JSON
examples in 02-prompting-craft/).
"""

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

PROMPT = "In one sentence, explain why the sky is blue."


def ask():
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[{"role": "user", "content": PROMPT}],
    )
    return response.content[0].text


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Non-Determinism")
    print("=" * 70)
    print(f"\nSame prompt sent 3 times: {PROMPT!r}\n")

    answers = [ask() for _ in range(3)]

    for i, answer in enumerate(answers, 1):
        print(f"Run {i}: {answer}")

    identical = len(set(answers)) == 1
    print(f"\n{'✅ All identical' if identical else '❌ Not identical'} — "
          f"{'try running again, it can happen by chance' if identical else 'this is expected: the model samples tokens, it does not replay a script'}")


if __name__ == "__main__":
    main()
