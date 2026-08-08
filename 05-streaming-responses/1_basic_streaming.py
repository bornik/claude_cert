"""
EXAMPLE 1: Streaming Responses — Basic Usage

Instead of waiting for the full response, stream tokens as Claude generates
them. Use client.messages.stream() as a context manager and iterate
stream.text_stream to print text as it arrives.

Key: stream.get_final_message() gives you the complete Message afterward,
including usage stats — no need to accumulate text yourself.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Streaming")
    print("=" * 70)

    print("\n📨 Prompt: Write a 3-sentence story about a lighthouse keeper.\n")
    print("🤖 Streaming response:\n")

    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[
            {"role": "user", "content": "Write a 3-sentence story about a lighthouse keeper."}
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

        final_message = stream.get_final_message()

    print(f"\n\n📊 Tokens used: {final_message.usage.output_tokens}")
    print_usage(final_message)


if __name__ == "__main__":
    main()
