"""
EXAMPLE 2: Parallel Tool Calls

Claude can call multiple tools in a single turn.
This is FASTER than sequential calls because:
- All tool calls are independent (they don't depend on each other's results)
- You can execute them concurrently
- Return all results in one message

Key: Both need tool_result blocks in the next user turn.
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
    print("\n" + "="*70)
    print("EXAMPLE 2: Parallel Tool Calls")
    print("="*70)

    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"]
            }
        },
        {
            "name": "get_time",
            "description": "Get current time for a timezone.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Timezone like 'UTC' or 'EST'"}
                },
                "required": ["timezone"]
            }
        }
    ]

    messages = [
        {"role": "user", "content": "What's the weather in London and what time is it in UTC?"}
    ]

    print(f"\n📨 User: {messages[0]['content']}")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    # Count how many tools were called
    tool_calls = [b for b in response.content if b.type == "tool_use"]
    print(f"\n✓ Claude made {len(tool_calls)} parallel tool calls")

    if not tool_calls:
        print("No tool calls made (this might happen with some prompts)")
        return

    # Execute all tools and collect results
    results = []
    for tool in tool_calls:
        print(f"\n🔧 {tool.name}: {tool.input}")

        # Simulate tool execution (in parallel in real code)
        if tool.name == "get_weather":
            result = "15°C, rainy"
        elif tool.name == "get_time":
            result = "14:30 UTC"
        else:
            result = "Unknown tool"

        # Collect the result
        results.append({
            "type": "tool_result",
            "tool_use_id": tool.id,
            "content": result
        })
        print(f"   Result: {result}")

    # Send ALL results back in one message (not sequential!)
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": results  # ← All results at once
    })

    print(f"\n✓ Returning {len(results)} results in one message")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    final_text = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "No response"
    )
    print(f"\n✅ Claude's response:\n   {final_text}")


if __name__ == "__main__":
    main()
