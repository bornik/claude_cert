"""
Tool-Use Examples for Claude API
Demonstrates how to build tool-use loops, define schemas, and handle tool selection.
"""

import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()
# ============================================================================
# EXAMPLE 1: Simple Tool-Use Loop
# ============================================================================

def example_1_simple_loop():
    """
    Demonstrates the basic tool-use loop:
    1. Define tool schemas
    2. Send message with tools
    3. Handle tool_use blocks in a loop
    4. Return tool_result
    5. Claude continues
    """

    print("\n" + "="*70)
    print("EXAMPLE 1: Simple Tool-Use Loop")
    print("="*70)

    # Step 1: Define tools
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

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    print(f"\n1️⃣  Claude's decision: {response.stop_reason}")

    # Step 3-5: Handle tool calls
    while response.stop_reason == "tool_use":
        # Find tool_use block
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None
        )

        if not tool_use_block:
            break

        print(f"\n2️⃣  Claude called tool: {tool_use_block.name}")
        print(f"   Input: {tool_use_block.input}")

        # Step 4: Execute tool (simulated)
        if tool_use_block.name == "get_weather":
            result = f"🌤️ {tool_use_block.input['location']}: 18°C, partly cloudy"

        print(f"3️⃣  Tool result: {result}")

        # Step 5: Send result back to Claude
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": result
                }
            ]
        })

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
    print(f"\n4️⃣  Claude's final response:\n   {final_text}")


# ============================================================================
# EXAMPLE 2: Parallel Tool Calls
# ============================================================================

def example_2_parallel_calls():
    """
    Claude can make multiple tool_use calls in a single turn.
    Both need tool_result blocks in the next user turn.
    """

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
                    "location": {"type": "string"}
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
                    "timezone": {"type": "string"}
                },
                "required": ["timezone"]
            }
        }
    ]

    messages = [
        {"role": "user", "content": "What's the weather in London and what time is it in UTC?"}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    print(f"\n✓ Claude made {len([b for b in response.content if b.type == 'tool_use'])} tool calls")

    # Collect all tool calls
    tool_calls = [b for b in response.content if b.type == "tool_use"]

    if not tool_calls:
        print("No tool calls made (this might happen with some prompts)")
        return

    # Execute all tools and collect results
    results = []
    for tool in tool_calls:
        print(f"\n  → {tool.name}: {tool.input}")

        if tool.name == "get_weather":
            result = "15°C, rainy"
        elif tool.name == "get_time":
            result = "14:30 UTC"
        else:
            result = "Unknown tool"

        results.append({
            "type": "tool_result",
            "tool_use_id": tool.id,
            "content": result
        })
        print(f"    Result: {result}")

    # Send all results back in one message
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": results
    })

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    final_text = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "No response"
    )
    print(f"\n✓ Final response: {final_text}")


# ============================================================================
# EXAMPLE 3: Schema Design - Good vs Bad
# ============================================================================

def example_3_schema_design():
    """
    Compare good and bad schema design.
    Same task, different schema quality.
    """

    print("\n" + "="*70)
    print("EXAMPLE 3: Schema Design - Good vs Bad")
    print("="*70)

    # ❌ BAD: Overlapping descriptions
    bad_tools = [
        {
            "name": "search_kb",
            "description": "Use this to find information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        },
        {
            "name": "get_cache",
            "description": "Use this to find information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }
    ]

    # ✓ GOOD: Clear distinction
    good_tools = [
        {
            "name": "search_kb",
            "description": "Search the knowledge base for current information. Use when the user asks a question that requires looking up new data. Do not use if a prior search in this session already covered the question.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_cache",
            "description": "Retrieve a result that was already fetched during this session. Use only if search_kb was called earlier for the same query. Do not use to find new information.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query key to retrieve from cache"
                    }
                },
                "required": ["query"]
            }
        }
    ]

    print("\n❌ BAD SCHEMA:")
    for tool in bad_tools:
        print(f"  {tool['name']}: {tool['description']}")
    print("\n  Problem: Both descriptions say 'find information' — Claude can't tell them apart!")

    print("\n✓ GOOD SCHEMA:")
    for tool in good_tools:
        print(f"  {tool['name']}: {tool['description'][:60]}...")
    print("\n  Benefit: Each has a 'do not use' clause that makes the difference clear!")

    # Show the required field difference
    print("\n\n📋 REQUIRED FIELDS EXAMPLE:")
    print("\nBad (too many required):")
    print(json.dumps({
        "properties": {
            "user_id": {"type": "string"},
            "filter": {"type": "string"},
            "sort": {"type": "string"}
        },
        "required": ["user_id", "filter", "sort"]  # Forces Claude to invent filter & sort
    }, indent=2))

    print("\nGood (only essentials):")
    print(json.dumps({
        "properties": {
            "user_id": {"type": "string"},
            "filter": {"type": "string"},
            "sort": {"type": "string"}
        },
        "required": ["user_id"]  # Let Claude omit optional params
    }, indent=2))


# ============================================================================
# EXAMPLE 4: Real-World Support Ticket Processor
# ============================================================================

def example_4_ticket_processor():
    """
    Matches your project: classify tickets and escalate if critical.
    Shows dependent tool calls (classify → then escalate if needed).
    """

    print("\n" + "="*70)
    print("EXAMPLE 4: Support Ticket Processor (Your Project)")
    print("="*70)

    tools = [
        {
            "name": "classify_ticket",
            "description": "Analyze a support ticket and classify it by category (billing, technical, escalation) and urgency (low, medium, high, critical). Use this when raw ticket text is provided. Returns a classification object. Do not use if the ticket is already classified.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticket_text": {
                        "type": "string",
                        "description": "The full support ticket text"
                    },
                    "ticket_id": {
                        "type": "string",
                        "description": "Optional ticket identifier"
                    }
                },
                "required": ["ticket_text"]
            }
        },
        {
            "name": "escalate_ticket",
            "description": "Escalate a ticket to the urgent queue. Use only if classify_ticket determined urgency is 'critical'. Do not use for any other urgency levels.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The ticket ID"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this ticket is critical"
                    }
                },
                "required": ["ticket_id", "reason"]
            }
        }
    ]

    tickets = [
        {
            "id": "T001",
            "text": "My API key stopped working after I rotated it. Production is failing. This needs to be fixed immediately."
        },
        {
            "id": "T002",
            "text": "I was charged twice this month. Can you refund the duplicate charge?"
        }
    ]

    for ticket in tickets:
        print(f"\n📨 Processing ticket {ticket['id']}:")
        print(f"   {ticket['text'][:60]}...")

        messages = [
            {"role": "user", "content": f"Process this ticket:\n{ticket['text']}"}
        ]

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        # Handle classification
        while response.stop_reason == "tool_use":
            tool = next(
                (b for b in response.content if b.type == "tool_use"),
                None
            )

            if not tool:
                break

            print(f"\n   ✓ Called: {tool.name}")

            # Simulate tool execution
            if tool.name == "classify_ticket":
                result = json.dumps({
                    "category": "technical" if "API" in tool.input["ticket_text"] else "billing",
                    "urgency": "critical" if "immediately" in tool.input["ticket_text"] else "medium",
                    "summary": "Production issue" if "immediately" in tool.input["ticket_text"] else "Billing issue"
                })
            elif tool.name == "escalate_ticket":
                result = json.dumps({"status": "escalated", "queue": "urgent"})

            print(f"   Result: {result}")

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool.id,
                        "content": result
                    }
                ]
            })

            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                tools=tools,
                messages=messages
            )


# ============================================================================
# EXAMPLE 5: Error Handling
# ============================================================================

def example_5_error_handling():
    """
    Show how to handle tool errors with is_error flag.
    """

    print("\n" + "="*70)
    print("EXAMPLE 5: Error Handling in Tool Results")
    print("="*70)

    tools = [
        {
            "name": "fetch_user",
            "description": "Get user information by ID.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"}
                },
                "required": ["user_id"]
            }
        }
    ]

    messages = [
        {"role": "user", "content": "Get user information for ID xyz"}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )

    tool = next(
        (b for b in response.content if b.type == "tool_use"),
        None
    )

    if tool:
        print(f"\nClaude called: {tool.name}")
        print(f"Input: {tool.input}")

        # Simulate a tool error
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": "User not found",
                    "is_error": True  # ← Mark as error
                }
            ]
        })

        print("\n✓ Sent error result:")
        print(json.dumps({
            "type": "tool_result",
            "tool_use_id": tool.id,
            "content": "User not found",
            "is_error": True
        }, indent=2))

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        final_text = next(
            (block.text for block in response.content if hasattr(block, "text")),
            "No response"
        )
        print(f"\nClaude's response to error:\n{final_text}")


# ============================================================================
# RUN EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("\n🛠️  CLAUDE TOOL-USE EXAMPLES")
    print("Based on the educational material\n")

    try:
        example_1_simple_loop()
        example_2_parallel_calls()
        example_3_schema_design()
        example_4_ticket_processor()
        example_5_error_handling()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("- ANTHROPIC_API_KEY is set in .env")
        print("- You have internet connection")
        print("- Your API key has quota")
