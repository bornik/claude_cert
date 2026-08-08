"""
Prompt iteration — the lesson's "prompt that grew longer instead of better"

Same task (classify a support ticket) across progressively more constrained
system prompts. Watch how output shape stabilizes as ambiguity is removed —
and notice how far it takes to get there.

Run:
    uv run 02-prompting-craft/prompt_iteration.py
"""

import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
client = Anthropic()

TICKET = "I was charged twice for the same month."

# Each pass adds one constraint the previous pass was missing.
PASSES = [
    (
        "1. Bare instruction",
        "You are a support classifier. Classify the ticket.",
    ),
    (
        "2. Name the output fields",
        "You are a support classifier. Classify the ticket into a category and urgency.",
    ),
    (
        "3. Constrain the field values",
        "You are a support classifier. Classify the ticket into category "
        "(billing, technical, escalation) and urgency (low, medium, high, critical).",
    ),
    (
        "4. Force structured output",
        "You are a support classifier. Return a JSON object with fields "
        "category (billing, technical, escalation) and urgency (low, medium, high, critical).",
    ),
    (
        "5. Add a required summary field",
        "You are a support classifier. Return a JSON object with exactly these fields: "
        "category (billing, technical, escalation), urgency (low, medium, high, critical), "
        "and summary (one sentence).",
    ),
    (
        "6. Ban prose around the JSON",
        "You are a support ticket processor. Extract the key information from each ticket "
        "and return only a JSON object with exactly these three fields: category (one of: "
        "billing, technical, escalation), urgency (one of: low, medium, high, critical), and "
        "summary (a single sentence describing the issue). Return only the JSON object. "
        "No other text.",
    ),
]


def classify(system_prompt: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": TICKET}],
    )
    print_usage(response, MODEL)
    return response.content[0].text.strip()


def is_clean_json(text: str) -> bool:
    """True only if the output is JSON with nothing else around it (no fences, no prose)."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def is_parseable_json(text: str) -> bool:
    """True if JSON can be recovered even after stripping ```json fences."""
    stripped = text.strip("`").removeprefix("json").strip() if text.startswith("```") else text
    try:
        json.loads(stripped)
        return True
    except json.JSONDecodeError:
        return False


def main():
    print(f"Ticket: {TICKET}\n")
    for label, prompt in PASSES:
        result = classify(prompt)
        if is_clean_json(result):
            verdict = "clean JSON (no fences)"
        elif is_parseable_json(result):
            verdict = "JSON, but wrapped in prose/fences"
        else:
            verdict = "NOT parseable as JSON"
        print(f"--- {label} [{verdict}] ---")
        print(f"Prompt: {prompt}")
        print(f"Output: {result}")
        print()


if __name__ == "__main__":
    main()
