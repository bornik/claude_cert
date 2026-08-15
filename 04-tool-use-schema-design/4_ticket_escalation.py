"""
EXAMPLE 4: Real-World — Support Ticket Escalation

Scenario:
- User submits a support ticket
- First tool: classify the ticket (category, urgency)
- Second tool: IF urgency is 'critical', escalate to urgent queue

This shows DEPENDENT tool calls:
- The second tool depends on the output of the first
- Claude automatically sequences them correctly
- The schema descriptions make the dependency clear

This is YOUR project's pattern!
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic
from anthropic.types import ToolResultBlockParam

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()


def main():
    print("\n" + "="*70)
    print("EXAMPLE 4: Support Ticket Escalation")
    print("Real-world pattern: classify → then escalate if critical")
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
            "description": "Escalate a ticket to the urgent queue. Use ONLY if classify_ticket determined urgency is 'critical'. Do not use for any other urgency level (low, medium, high).",
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
        },
        {
            "id": "T003",
            "text": "The dashboard loads slowly sometimes. Not a big deal, just wanted to flag it."
        }
    ]

    for ticket in tickets:
        process_ticket(ticket, tools)


def process_ticket(ticket, tools):
    """Process a single ticket through classification and escalation"""

    print(f"\n{'='*70}")
    print(f"📨 Ticket {ticket['id']}")
    print(f"{'='*70}")
    print(f"Text: {ticket['text'][:70]}...")

    messages = [
        {"role": "user", "content": f"Process this support ticket:\n{ticket['text']}"}
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
    print_usage(response)

    # Handle the tool-use loop
    step = 1
    while response.stop_reason == "tool_use":
        tool = next(
            (b for b in response.content if b.type == "tool_use"),
            None
        )

        if not tool:
            break

        print(f"\n  Step {step}: Called {tool.name}")
        print(f"           Input: {json.dumps(tool.input, indent=12)}")

        # Simulate tool execution
        if tool.name == "classify_ticket":
            # Parse the ticket to determine urgency
            urgency = "critical" if "immediately" in ticket['text'] or "production" in ticket['text'].lower() else "medium"
            category = "billing" if "charged" in ticket['text'].lower() else "technical"
            result = json.dumps({
                "ticket_id": ticket['id'],
                "category": category,
                "urgency": urgency,
                "summary": tool.input['ticket_text'][:50]
            })

        elif tool.name == "escalate_ticket":
            result = json.dumps({
                "status": "escalated",
                "queue": "urgent",
                "assigned_to": "senior_support"
            })

        print(f"           Result: {result}")

        # Send result back
        messages.append({"role": "assistant", "content": response.content})
        tool_results: list[ToolResultBlockParam] = [
            ToolResultBlockParam(type="tool_result", tool_use_id=tool.id, content=result)
        ]
        messages.append({"role": "user", "content": tool_results})

        # Continue
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        step += 1

    # Final response
    final_text = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "No response"
    )
    print(f"\n  ✅ Result: {final_text}")


if __name__ == "__main__":
    main()
