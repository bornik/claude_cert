"""
EXAMPLE 5: Error Handling in Tool Results

When a tool fails (network error, not found, permission denied, etc.),
return a tool_result with is_error=True.

Claude sees the error and can:
- Retry with different arguments
- Ask the user for clarification
- Explain what went wrong

Key: is_error=True tells Claude "this failed, try a different approach"
"""

import json
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
    print("EXAMPLE 5: Error Handling")
    print("="*70)

    tools = [
        {
            "name": "fetch_user",
            "description": "Get user information by user ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The user ID to look up"}
                },
                "required": ["user_id"]
            }
        }
    ]

    # Scenario 1: Tool succeeds
    print("\n📝 Scenario 1: Successful tool call")
    print("-" * 70)
    scenario_successful(tools)

    # Scenario 2: Tool fails
    print("\n\n📝 Scenario 2: Tool fails (user not found)")
    print("-" * 70)
    scenario_error(tools)

    # Scenario 3: Tool fails, Claude retries
    print("\n\n📝 Scenario 3: Tool fails, Claude adapts")
    print("-" * 70)
    scenario_error_with_retry(tools)


def scenario_successful(tools):
    """Show a successful tool call"""

    messages = [
        {"role": "user", "content": "Get information about user ABC123"}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    tool = next(
        (b for b in response.content if b.type == "tool_use"),
        None
    )

    if tool:
        print(f"🔧 Claude called: {tool.name}")
        print(f"   Input: {tool.input}")

        # Simulate successful response
        result = json.dumps({
            "user_id": "ABC123",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "created_at": "2024-01-15"
        })

        print(f"   Result: {result}")
        print(f"\n✅ Tool call succeeded!")


def scenario_error(tools):
    """Show what happens when a tool fails"""

    messages = [
        {"role": "user", "content": "Get information about user XYZ999"}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    tool = next(
        (b for b in response.content if b.type == "tool_use"),
        None
    )

    if tool:
        print(f"🔧 Claude called: {tool.name}")
        print(f"   Input: {tool.input}")

        # Simulate error response
        error_message = "User not found: XYZ999 does not exist in the database"

        print(f"\n❌ Tool execution failed!")
        print(f"   Error: {error_message}")

        # IMPORTANT: Mark as error!
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": error_message,
                    "is_error": True  # ← This is the key!
                }
            ]
        })

        print(f"\n✓ Sent error result with is_error=True")

        # Claude responds to the error
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

        print(f"\n🤖 Claude's response to error:")
        print(f"   {final_text}")


def scenario_error_with_retry(tools):
    """Show Claude retrying when a tool fails"""

    messages = [
        {"role": "user", "content": "Try to get user with ID 'invalid-id', but if that fails, try 'backup-user'"}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    call_count = 0
    while response.stop_reason == "tool_use":
        call_count += 1
        tool = next(
            (b for b in response.content if b.type == "tool_use"),
            None
        )

        if not tool:
            break

        print(f"\n🔧 Call {call_count}: {tool.name}")
        print(f"   Input: {tool.input}")

        # Simulate behavior: first call fails, second succeeds
        if call_count == 1:
            error = True
            result = "User not found: invalid-id"
        else:
            error = False
            result = json.dumps({
                "user_id": "backup-user",
                "name": "Bob Smith",
                "email": "bob@example.com"
            })

        print(f"   Result: {result}")
        if error:
            print(f"   Status: ❌ Error")
        else:
            print(f"   Status: ✅ Success")

        # Send result back
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": result,
                    "is_error": error  # ← Set to True/False based on result
                }
            ]
        })

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

    print(f"\n✅ Claude's final response after {call_count} attempts:")
    print(f"   {final_text}")


if __name__ == "__main__":
    main()
