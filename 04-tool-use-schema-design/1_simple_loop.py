"""
EXAMPLE 1: Simple Tool-Use Loop

The basic pattern:
1. Define a tool schema
2. Send a message with tools available
3. Claude decides to call a tool and returns tool_use block
4. You execute the tool and return tool_result
5. Claude continues conversation with the result

This is the foundation of all tool-use patterns.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic
from anthropic.types import ToolResultBlockParam, MessageParam

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()


def main():
    print("\n" + "="*70)
    print("EXAMPLE 1: Simple Tool-Use Loop")
    print("="*70)

    # Step 1: Define what tools Claude can call
    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather for a location. Use this when the user asks about weather. Do not use for forecasts.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, e.g., 'London' or 'Paris'"
                    }
                },
                "required": ["location"]
            }
        }
    ]

    # Step 2: Send initial message
    messages = [
        {"role": "user", "content": "What's the weather in Paris?"}
    ]

    print(f"\n📨 User: {messages[0]['content']}")

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    print(f"\n🤖 Claude's decision: {response.stop_reason}")

    # Step 3-5: Handle tool calls in a loop
    while response.stop_reason == "tool_use":
        # Find the tool_use block (Claude's decision to call a tool)
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None
        )

        if not tool_use_block:
            break

        print(f"\n🔧 Claude called: {tool_use_block.name}")
        print(f"   Arguments: {tool_use_block.input}")

        # Step 4: Execute the tool (simulated here)
        if tool_use_block.name == "get_weather":
            result = f"🌤️ {tool_use_block.input['location']}: 18°C, partly cloudy"

        print(f"   Result: {result}")

        # Step 5: Send result back to Claude
        # Add Claude's response to messages
        messages.append({"role": "assistant", "content": response.content})

        # Add the tool result
        tool_results: list[ToolResultBlockParam] = [
            ToolResultBlockParam(type="tool_result", tool_use_id=tool_use_block.id, content=result)
        ]
        messages.append({"role": "user", "content": tool_results})

        # Continue conversation
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

    # Final response
    final_text = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "No response"
    )
    print(f"\n✅ Claude's final answer:\n   {final_text}")


if __name__ == "__main__":
    main()
