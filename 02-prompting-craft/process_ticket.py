import argparse
import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
EXAMPLES_FILE = BASE_DIR / "examples.json"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")

PROMPT_VERSIONS = {
    "bare": BASE_DIR / "system_prompt_bare.txt",
    "refined": BASE_DIR / "system_prompt.txt",
}

client = Anthropic()


def run_prompt(user_input: str, prompt_version: str = "refined") -> str:
    system_prompt = PROMPT_VERSIONS[prompt_version].read_text().strip()
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


def run_diff(user_input: str):
    """Run the same ticket through both prompt versions so you can compare output quality."""
    for version in ("bare", "refined"):
        print(f"--- {version} ({PROMPT_VERSIONS[version].name}) ---")
        print_result(run_prompt(user_input, version))
        print()


def main():
    parser = argparse.ArgumentParser(description="Classify a support ticket with Claude.")
    parser.add_argument("ticket_text", nargs="?", help="Ticket text to classify (defaults to first example)")
    parser.add_argument("--all", action="store_true", help="Run every example in examples.json")
    parser.add_argument(
        "--prompt-version",
        choices=PROMPT_VERSIONS.keys(),
        default="refined",
        help="Which system prompt to use (see system_prompt_bare.txt vs system_prompt.txt)",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Run bare vs refined prompts on the same input and print both outputs",
    )
    args = parser.parse_args()

    examples = json.loads(EXAMPLES_FILE.read_text())

    if args.diff:
        user_input = args.ticket_text or examples[0]
        print(f"Input: {user_input}\n")
        run_diff(user_input)
        return

    if args.all:
        for example in examples:
            print(f"Input: {example}")
            print_result(run_prompt(example, args.prompt_version))
            print()
        return

    user_input = args.ticket_text or examples[0]
    print_result(run_prompt(user_input, args.prompt_version))


if __name__ == "__main__":
    main()
