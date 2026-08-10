"""
EXAMPLE 2: Over-Tooling — Does a Bigger Tool Surface Degrade Selection?

"Over-tooling is the more common problem in production agents. Teams
register every tool they might need 'just in case' and discover that
Claude's selection quality degrades as the tool surface grows."

This tests that claim directly: the same request, sent once against a
minimal 3-tool set, and once against a bloated 15-tool set where several
tools have deliberately overlapping, vague descriptions (the kind that
accumulate when a team keeps adding tools "just in case" without pruning
or tightening descriptions). We check whether Claude still picks the one
correct tool once the surface is much larger and noisier.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

QUERY = "What is the current status of order ORD-7823?"

MINIMAL_TOOLS = [
    {
        "name": "get_order_status",
        "description": "Look up the current status (pending, shipped, delivered, cancelled) of an order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "get_customer_profile",
        "description": "Look up a customer's profile information by customer ID.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "search_products",
        "description": "Search the product catalog by keyword.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

# Same 3 tools, plus 12 more that teams tend to accumulate "just in case" —
# several with descriptions that overlap heavily with get_order_status,
# the correct tool for this query.
BLOATED_TOOLS = MINIMAL_TOOLS + [
    {"name": "get_order_details", "description": "Get information about an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_order_history", "description": "Get information about a customer's past orders.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "track_shipment", "description": "Get information about a shipment.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_order_timeline", "description": "Get information about the timeline of an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "check_order", "description": "Check on an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_invoice", "description": "Get the invoice for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_return_status", "description": "Get information about a return.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_refund_status", "description": "Get information about a refund.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_warehouse_info", "description": "Get information about warehouse inventory for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_delivery_estimate", "description": "Get information about when an order will arrive.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_payment_status", "description": "Get information about payment for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_support_tickets", "description": "Get information about support tickets for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
]


def ask(tools, label):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        tools=tools,
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": QUERY}],
    )
    print_usage(response)
    tool_use = next((b for b in response.content if b.type == "tool_use"), None)
    picked = tool_use.name if tool_use else "(no tool called)"
    print(f"{label} ({len(tools)} tools): Claude picked → {picked}")
    return picked


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Over-Tooling — Selection Quality vs. Tool Surface Size")
    print("=" * 70)
    print(f"\nQuery: {QUERY!r}")
    print("Correct tool: get_order_status\n")

    minimal_pick = ask(MINIMAL_TOOLS, "Minimal set")
    bloated_pick = ask(BLOATED_TOOLS, "Bloated set")

    print(f"""
📝 Result: minimal set picked {minimal_pick!r}, bloated set picked {bloated_pick!r}.
""")
    if minimal_pick == "get_order_status" and bloated_pick != "get_order_status":
        print("Reproduced the claim: same query, correct pick shrinks once 12 overlapping,")
        print("vaguely-described tools are added to the surface.")
    elif minimal_pick == bloated_pick == "get_order_status":
        print("Both picked correctly on this run. claude-haiku-4-5 handled 15 tools fine")
        print("here — this doesn't disprove the claim, it means this particular set of")
        print("overlapping descriptions and this model weren't enough to break it. Try a")
        print("more ambiguous query, more tools, or near-duplicate names to push further.")
    else:
        print("Unexpected pattern — inspect both picks above.")

    print("""
This is exactly the mechanism the lesson describes: teams register tools
"just in case" without pruning, descriptions drift into near-duplicates
(get_order_details vs track_shipment vs check_order — all plausible for
this query), and the model has more plausible-looking but wrong options
to choose between. The fix isn't a smarter model — it's discipline:
start with the minimum tool set the task needs, add a tool only when a
specific capability gap is confirmed, and prune or merge overlapping
tools rather than letting them accumulate.
""")


if __name__ == "__main__":
    main()
