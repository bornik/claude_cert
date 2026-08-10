"""
EXAMPLE 2: Over-Tooling — Does a Bigger Tool Surface Degrade Selection?

"Over-tooling is the more common problem in production agents. Teams
register every tool they might need 'just in case' and discover that
Claude's selection quality degrades as the tool surface grows."

A single run against a bloated tool set can luck into the right answer
even when the tools are genuinely confusing — Claude doesn't have to be
wrong every time for the tool set to be bad, it just has to be
INCONSISTENT. So instead of one call per scenario, this sends the SAME
ambiguous query N times against a minimal tool set and N times against a
bloated one with several tools sharing near-identical wording, and
compares the SPREAD of picks. A stable tool set gives the same answer
every time. A confusing one doesn't — that instability is the failure,
even on runs where any individual pick looks "reasonable."

Two things are stacked to make confusion likely:
1. The query itself is genuinely ambiguous between several plausible
   readings (not just "status" — "what's going on" could mean status,
   history, timeline, or open tickets).
2. Several bloated-set tools share nearly word-for-word descriptions,
   differing only in name — the actual pattern from teams bolting on
   tools without consolidating overlapping ones.
"""

import sys
from collections import Counter
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

# Deliberately ambiguous — a human support agent would also have to ask
# a follow-up question here. Several tools below are equally plausible.
QUERY = "What's going on with order ORD-7823?"

RUNS_PER_SCENARIO = 6

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

# Same base tool, but here it has FOUR near-clones with virtually the same
# description ("current information/status about an order"), plus other
# plausible reads of "what's going on" (timeline, tickets, tracking).
# This is what "just add a tool, don't consolidate" produces in practice.
BLOATED_TOOLS = MINIMAL_TOOLS + [
    {"name": "get_order_details", "description": "Get current information about an order by order ID.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "check_order", "description": "Get current information about an order by order ID.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_order_info", "description": "Get current status information about an order by order ID.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "order_lookup", "description": "Get current status information for an order by order ID.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "track_shipment", "description": "Get shipment tracking information for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_order_timeline", "description": "Get the event timeline for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_support_tickets", "description": "Get open support tickets related to an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_order_history", "description": "Get a customer's past order history.", "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_invoice", "description": "Get the invoice for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_return_status", "description": "Get return status for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_refund_status", "description": "Get refund status for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"name": "get_delivery_estimate", "description": "Get the delivery estimate for an order.", "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}},
]


def sample_picks(tools, label):
    picks = []
    for i in range(1, RUNS_PER_SCENARIO + 1):
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
        picks.append(picked)
        print(f"  Run {i}/{RUNS_PER_SCENARIO}: {picked}")

    counts = Counter(picks)
    print(f"\n{label} ({len(tools)} tools) — distribution across {RUNS_PER_SCENARIO} runs: {dict(counts)}")
    return counts


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Over-Tooling — Consistency vs. Tool Surface Size")
    print("=" * 70)
    print(f"\nAmbiguous query: {QUERY!r}")
    print(f"Running it {RUNS_PER_SCENARIO} times against each tool set to check for CONSISTENCY,")
    print("not just a single pick — a bad tool set shows up as instability across identical calls.\n")

    print("--- Minimal set (3 tools) ---")
    minimal_counts = sample_picks(MINIMAL_TOOLS, "Minimal set")

    print("\n--- Bloated set (15 tools, several near-duplicate) ---")
    bloated_counts = sample_picks(BLOATED_TOOLS, "Bloated set")

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Minimal set distribution: {dict(minimal_counts)} ({len(minimal_counts)} distinct tool(s) picked)")
    print(f"Bloated set distribution: {dict(bloated_counts)} ({len(bloated_counts)} distinct tool(s) picked)")

    if len(bloated_counts) > len(minimal_counts):
        print("""
Reproduced the claim: the minimal set answered the SAME ambiguous query
consistently, while the bloated set's answer varied run to run. That
instability — not a single "wrong" pick — is what over-tooling actually
looks like in production: the same user question routes to a different
tool depending on nothing you control, because several tools are
equally plausible matches for the model to reach for.
""")
    elif len(bloated_counts) == 1:
        print("""
Both sets were consistent on this run — the bloated set's near-duplicate
tools weren't enough to destabilize claude-haiku-4-5 this time. This
doesn't disprove the mechanism: try more near-duplicate tools, more
overlapping names, or a real production tool count (30-50+) to push it
further. Confusion is a matter of degree, not a guaranteed per-run failure.
""")
    else:
        print("\nUnexpected pattern — inspect the per-run picks above.")

    print("""
This is the mechanism the lesson describes: teams register tools "just
in case" without consolidating, several end up with near-identical
descriptions, and the model has more equally-plausible-looking options
to pick between — so its choice becomes less a function of the query and
more a function of noise in a growing tool list. The fix isn't a smarter
model — it's discipline: start with the minimum tool set the task needs,
add a tool only when a specific capability gap is confirmed, and merge
or prune tools whose descriptions overlap rather than letting them pile up.
""")


if __name__ == "__main__":
    main()
