import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
SYSTEM_PROMPT_FILE = BASE_DIR / "system_prompt.txt"
EXAMPLES_FILE = BASE_DIR / "examples.json"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")

client = Anthropic()


def run_prompt(user_input: str) -> str:
    system_prompt = SYSTEM_PROMPT_FILE.read_text().strip()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}],
    )
    return response.content[0].text


def print_result(result: str):
    text = result.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        print(json.dumps(json.loads(text), indent=2))
    except json.JSONDecodeError:
        print(result)


def main():
    examples = json.loads(EXAMPLES_FILE.read_text())

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        for example in examples:
            print(f"Input: {example}")
            print_result(run_prompt(example))
            print()
        return

    user_input = sys.argv[1] if len(sys.argv) > 1 else examples[0]
    print_result(run_prompt(user_input))


if __name__ == "__main__":
    main()
