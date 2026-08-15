"""
EXAMPLE 0: Structured Output — Force responses to match a JSON schema

The API can constrain Claude's response to match a JSON schema you provide.
This is different from tool schemas — it controls the response format itself,
not tool inputs.

Use when you need guaranteed structure (extraction, classification, etc.)
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


def main():
    print("\n" + "="*70)
    print("STRUCTURED OUTPUT: Extract data into a guaranteed JSON schema")
    print("="*70)

    # Define the schema Claude MUST follow
    extraction_schema = {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "company": {"type": "string"},
                "interests": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["name", "email", "company", "interests"],
            "additionalProperties": False
        }
    }

    # Unstructured text to extract from
    text = """
    Hey, I'm Alice from TechCorp. My email is alice@techcorp.com.
    I'm really into machine learning, data science, and Python development.
    """

    print(f"\n📝 Input (unstructured):\n   {text.strip()}")
    print(f"\n🎯 Schema constraint: {extraction_schema['schema']['properties'].keys()}")

    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=500,
        output_config={"format": extraction_schema},
        messages=[
            {
                "role": "user",
                "content": f"Extract the following information and return it as JSON:\n\n{text}"
            }
        ]
    )
    print_usage(response)

    # Claude's response is GUARANTEED to be valid JSON matching the schema
    result_text = response.content[0].text
    result = json.loads(result_text)

    print(f"\n✅ Output (structured):")
    print(json.dumps(result, indent=2))

    # Verify it matches the schema
    required_fields = extraction_schema["schema"]["required"]
    print(f"\n✓ Verified: All required fields present: {required_fields}")


if __name__ == "__main__":
    main()
