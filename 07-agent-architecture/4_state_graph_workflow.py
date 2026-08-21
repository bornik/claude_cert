"""
EXAMPLE 4: State-Graph Workflows — Structure Where You Need It, Discretion
Where It Pays Off

Script 1 gave you two extremes: a workflow (our code decides every step)
and an agent (Claude decides every step). A lot of real systems need
something in between: EXPLICIT transition rules like a workflow, but with
Claude making the one or two judgment calls a fixed if/else can't — plus
three things neither script 1 nor 08's approval gates actually have:

  - DURABLE state: the current step and all data so far survive a process
    restart, not just a paused loop in the same running program.
  - RESUMABLE human approval: pausing for a human doesn't mean blocking
    on input() mid-call — it means writing a checkpoint, exiting, and
    picking back up from that exact node whenever the decision arrives,
    possibly in a completely different process.
  - VISUAL inspection: every possible branch out of every node can be
    listed and printed, because the graph is DATA (nodes + a transition
    table), not "whatever Claude decides live" the way an agent's control
    flow is.

This script hand-rolls a tiny graph engine to show the SHAPE of what a
framework like LangGraph buys you. Production code should reach for a
real one; the mechanism (nodes, an explicit transition table, a
checkpoint file, a human-gate node) is the same either way.
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

MODEL = "claude-haiku-4-5"
CHECKPOINT_FILE = Path(__file__).resolve().parent / "ticket_graph_checkpoint.json"

# Nodes where the graph MUST have a human decision in state before it can
# proceed. Anywhere else, the graph runs straight through untouched.
HUMAN_GATE_NODES = {"await_approval"}


class StateGraph:
    """Nodes are functions that transform state. Transitions are declared
    as (condition_fn, {label: next_node}) so every possible branch is
    known statically, upfront — not just the one branch a given run
    happens to take."""

    def __init__(self):
        self.nodes = {}
        self.transitions = {}

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def add_transition(self, name, condition_fn, mapping):
        self.transitions[name] = (condition_fn, mapping)

    def describe(self):
        print("Graph structure (every declared branch, not just the one taken):")
        for name in self.nodes:
            gate = " [human gate]" if name in HUMAN_GATE_NODES else ""
            print(f"  {name}{gate}")
            if name in self.transitions:
                _, mapping = self.transitions[name]
                for label, dest in mapping.items():
                    print(f"    --[{label}]--> {dest}")

    def _save_checkpoint(self, state):
        CHECKPOINT_FILE.write_text(json.dumps(state, indent=2))

    def run(self, state):
        current = state["_current_node"]
        while current != "END":
            if current in HUMAN_GATE_NODES and "human_decision" not in state:
                state["_current_node"] = current
                self._save_checkpoint(state)
                print(f"⏸  Paused at '{current}' — checkpoint written to {CHECKPOINT_FILE.name}.")
                return state, "PAUSED"

            state = self.nodes[current](state)
            condition_fn, mapping = self.transitions[current]
            label = condition_fn(state)
            current = mapping[label]
            state["_current_node"] = current
            self._save_checkpoint(state)

        print("✅ Reached END.")
        return state, "DONE"


# ---------------------------------------------------------------------------
# Nodes — deterministic Python everywhere except classify(), the one place
# a free-text judgment call actually needs the model.
# ---------------------------------------------------------------------------

def node_classify(state):
    response = client.messages.create(
        model=MODEL,
        max_tokens=10,
        system="Classify this support ticket's severity. Answer with exactly one word: high or low.",
        messages=[{"role": "user", "content": state["ticket_text"]}],
    )
    print_usage(response, model=MODEL)
    severity = "high" if "high" in response.content[0].text.strip().lower() else "low"
    state["severity"] = severity
    print(f"  [classify] model judged severity = {severity!r}")
    return state


def node_lookup_account(state):
    """No model call — a real version would hit a database. Only reached
    for high-severity tickets, since low-severity ones route straight to
    resolve() without needing account context at all."""
    state["account_standing"] = "good_standing"
    print(f"  [lookup_account] account standing = {state['account_standing']!r}")
    return state


def node_await_approval(state):
    """By the time this runs, the human-gate check in run() has already
    guaranteed state['human_decision'] is present."""
    print(f"  [await_approval] resuming with human_decision = {state['human_decision']!r}")
    return state


def node_resolve(state):
    state["result"] = "Resolved automatically, no escalation needed."
    print(f"  [resolve] {state['result']}")
    return state


def node_escalate(state):
    state["result"] = "Escalated to a human agent."
    print(f"  [escalate] {state['result']}")
    return state


def build_ticket_graph() -> StateGraph:
    graph = StateGraph()
    graph.add_node("classify", node_classify)
    graph.add_node("lookup_account", node_lookup_account)
    graph.add_node("await_approval", node_await_approval)
    graph.add_node("resolve", node_resolve)
    graph.add_node("escalate", node_escalate)

    graph.add_transition(
        "classify",
        lambda s: s["severity"],
        {"high": "lookup_account", "low": "resolve"},
    )
    graph.add_transition("lookup_account", lambda s: "next", {"next": "await_approval"})
    graph.add_transition(
        "await_approval",
        lambda s: s["human_decision"],
        {"approved": "resolve", "denied": "escalate"},
    )
    graph.add_transition("resolve", lambda s: "next", {"next": "END"})
    graph.add_transition("escalate", lambda s: "next", {"next": "END"})
    return graph


def get_human_decision(prompt: str) -> str:
    """Same fail-safe rule as 08-human-in-the-loop/1_approval_gate.py: no
    terminal input available means we decline, never silently approve."""
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        print("(no terminal input available — failing safe to 'denied')")
        return "denied"
    return "approved" if answer == "y" else "denied"


def demo_low_severity_skips_the_gate(graph: StateGraph):
    print("\n" + "=" * 70)
    print("1. Low-severity ticket — model discretion used once, then a fixed path")
    print("=" * 70)

    state = {
        "ticket_text": "How do I change the email address on my account?",
        "_current_node": "classify",
    }
    final_state, status = graph.run(state)
    print(f"\nStatus: {status} — result: {final_state['result']}")
    print(
        "Note: this ticket never touched lookup_account or await_approval "
        "at all — classify() routed it straight to resolve(). The model "
        "made exactly one judgment call; every step after that was a "
        "plain lookup in the transition table."
    )


def demo_high_severity_durable_pause_and_resume(graph: StateGraph):
    print("\n" + "=" * 70)
    print("2. High-severity ticket — durable pause, simulated restart, resume")
    print("=" * 70)

    state = {
        "ticket_text": "Production database was just deleted, customers can't log in.",
        "_current_node": "classify",
    }
    paused_state, status = graph.run(state)
    print(f"\nStatus after first run: {status}")

    print(
        "\n--- Simulating a process restart: discarding every in-memory "
        "variable above, reading ONLY the checkpoint file from disk ---"
    )
    del state, paused_state  # prove nothing carries over except the file

    reloaded_state = json.loads(CHECKPOINT_FILE.read_text())
    print(
        f"Reloaded from {CHECKPOINT_FILE.name}: "
        f"current_node={reloaded_state['_current_node']!r}, "
        f"severity={reloaded_state.get('severity')!r}, "
        f"account_standing={reloaded_state.get('account_standing')!r}"
    )

    reloaded_state["human_decision"] = get_human_decision(
        "Approve escalated ticket for auto-resolution? [y/n]: "
    )
    final_state, status = graph.run(reloaded_state)
    print(f"\nStatus after resuming: {status} — result: {final_state['result']}")
    print(
        "Note: the graph resumed exactly at 'await_approval', not from "
        "the top — classify() and lookup_account() did not re-run. The "
        "checkpoint is what made that possible; nothing about the human "
        "decision needed to happen in the same process that started the "
        "ticket, or even the same day."
    )

    CHECKPOINT_FILE.unlink(missing_ok=True)


def main():
    graph = build_ticket_graph()

    print("=" * 70)
    print("Graph structure, printed before running anything")
    print("=" * 70)
    graph.describe()
    print(
        "\nEvery branch above is visible right now, including the ones "
        "today's demo runs won't take (e.g. classify --[low]--> resolve "
        "for demo 2's high-severity ticket). An agent's control flow "
        "can't be listed like this ahead of time — it's whatever Claude "
        "decides, discovered only by watching it run."
    )

    demo_low_severity_skips_the_gate(graph)
    demo_high_severity_durable_pause_and_resume(graph)


if __name__ == "__main__":
    main()
