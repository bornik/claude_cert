"""
EXAMPLE 3: Define Exit Conditions — Don't Rely on Claude to Volunteer to Stop

"The agent loop runs until it receives a stop condition. Without explicit
exit conditions, the agent will continue requesting tool calls beyond
what the task requires. You should define when done means done."

This runs an agent loop with a tool that can always plausibly be called
again (fetch_related_ticket — every ticket has "related" tickets), and no
natural task boundary. Scenario A relies purely on Claude deciding to
stop (stop_reason != "tool_use") — no cap. Scenario B adds an explicit
exit condition: a hard turn limit AND a `finish_investigation` tool that
Claude must call to signal completion, checked by OUR code, not inferred
from Claude's tone.
"""

import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.usage import print_usage

load_dotenv()
client = Anthropic()

FETCH_TOOL = {
    "name": "fetch_related_ticket",
    "description": "Fetch a ticket related to the current one, by ticket ID.",
    "input_schema": {
        "type": "object",
        "properties": {"ticket_id": {"type": "string"}},
        "required": ["ticket_id"],
    },
}

FINISH_TOOL = {
    "name": "finish_investigation",
    "description": "Call this exactly once you have enough information to summarize the root cause. This ends the investigation.",
    "input_schema": {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    },
}

REQUEST = (
    "Investigate ticket TICKET-1: it references related tickets that might explain "
    "a recurring billing bug. Follow related tickets as far as useful, then summarize "
    "the root cause."
)


def fake_fetch(ticket_id):
    # Every ticket "helpfully" points to another one — there's no natural
    # stopping point baked into the data, which is the point of this demo.
    n = int(ticket_id.split("-")[1]) if "-" in ticket_id else 1
    return f"{ticket_id}: billing retried the charge on failure. See also TICKET-{n + 1}."


def run_without_exit_condition(hard_safety_cap):
    """Scenario A: no finish tool, no real exit condition — just Claude's
    own judgment about when to stop calling fetch_related_ticket. We still
    keep a hard_safety_cap so THIS DEMO can't loop forever, but note that
    this cap is a safety net for the script, not a designed exit condition
    — nothing tells Claude in advance that there's a limit."""
    print("\n" + "=" * 70)
    print("Scenario A: No defined exit condition (relying on Claude to stop)")
    print("=" * 70)

    messages = [{"role": "user", "content": REQUEST}]
    turns_used = 0

    for turn in range(1, hard_safety_cap + 1):
        response = client.messages.create(
            model="claude-haiku-4-5", max_tokens=300, tools=[FETCH_TOOL], messages=messages
        )
        print_usage(response)
        messages.append({"role": "assistant", "content": response.content})
        turns_used = turn

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            text = next((b.text for b in response.content if b.type == "text"), "")
            print(f"Turn {turn}: Claude stopped on its own. Answer: {text[:100]!r}...")
            return turns_used, "stopped_voluntarily"

        print(f"Turn {turn}: called fetch_related_ticket({tool_use.input})")
        result = fake_fetch(tool_use.input["ticket_id"])
        messages.append(
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": result}]}
        )

    print(f"Hit the demo's safety cap ({hard_safety_cap} turns) without Claude ever stopping on its own.")
    return turns_used, "hit_safety_cap"


def run_with_exit_condition(max_turns):
    """Scenario B: a designed exit condition — a turn budget the agent is
    TOLD about up front, plus a finish_investigation tool that makes
    completion an explicit, checkable event rather than an inference from
    stop_reason."""
    print("\n" + "=" * 70)
    print(f"Scenario B: Explicit exit condition (finish tool + {max_turns}-turn budget, told to Claude)")
    print("=" * 70)

    messages = [
        {
            "role": "user",
            "content": (
                REQUEST
                + f" You have a budget of {max_turns} tool calls total. Call "
                "finish_investigation as soon as you have enough to summarize — "
                "do not use the full budget just because it's available."
            ),
        }
    ]

    for turn in range(1, max_turns + 1):
        response = client.messages.create(
            model="claude-haiku-4-5", max_tokens=300, tools=[FETCH_TOOL, FINISH_TOOL], messages=messages
        )
        print_usage(response)
        messages.append({"role": "assistant", "content": response.content})

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            print(f"Turn {turn}: no tool call — treating as incomplete, not a valid exit.")
            break

        if tool_use.name == "finish_investigation":
            print(f"Turn {turn}: called finish_investigation — explicit, checkable completion signal.")
            print(f"Summary: {tool_use.input['summary'][:150]!r}...")
            return turn, "finished_explicitly"

        print(f"Turn {turn}: called fetch_related_ticket({tool_use.input})")
        result = fake_fetch(tool_use.input["ticket_id"])
        messages.append(
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use.id, "content": result}]}
        )

    print(f"Hit the {max_turns}-turn budget without an explicit finish_investigation call — code should")
    print("treat this as an incomplete investigation, not silently accept whatever came last.")
    return max_turns, "hit_defined_budget"


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Define Exit Conditions")
    print("=" * 70)

    turns_a, outcome_a = run_without_exit_condition(hard_safety_cap=6)
    turns_b, outcome_b = run_with_exit_condition(max_turns=6)

    print(f"""
======================================================================
RESULT
======================================================================
Scenario A (no defined exit condition): {turns_a} turns, outcome = {outcome_a}
Scenario B (explicit finish tool + stated budget): {turns_b} turns, outcome = {outcome_b}

📝 Takeaway: in Scenario A, the only thing stopping the loop was a safety
cap WE added defensively to this demo script — nothing in the task or
the tools told Claude in advance that there was a limit, so its stopping
point (if any) is whatever it happens to decide, turn to turn. In
Scenario B, completion is a specific tool call your code can check for
(`tool_use.name == "finish_investigation"`) — "done" is a fact you can
test, not a judgment call inferred from `stop_reason` or from the tone
of the final message. Always design the exit condition; don't discover
it empirically by watching how many turns a particular run happened to take.
""")


if __name__ == "__main__":
    main()
