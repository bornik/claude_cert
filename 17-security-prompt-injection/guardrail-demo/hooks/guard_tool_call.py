#!/usr/bin/env python3
"""PreToolUse hook body: a real hook-based guardrail, not a simulation.

Claude Code invokes this as a subprocess BEFORE a matched tool call
executes, piping the event as JSON on stdin. Unlike the delimiter/system-
prompt defense in ../../1_indirect_prompt_injection.py, this check runs in
the harness itself -- no phrasing of the model's response can skip it,
because the decision is made in this process, not by the model.

Rule priority is Deny > Ask > Allow, checked in that order:
  1. DENY  -- Write outside the module's own output/ directory (least
              privilege: this agent gets one output folder, nothing else)
              or a Bash command that reaches a network tool (curl/wget/nc)
              aimed at a domain that isn't explicitly allow-listed (blocks
              exfiltration even if a poisoned document talked the model
              into trying it).
  2. ASK   -- a Bash command that pushes to a remote (git push): not
              inherently malicious, but irreversible enough to want a
              human to confirm.
  3. ALLOW -- everything else; exit 0 with no JSON means "no decision,"
              which lets the normal permission flow proceed.

Every decision (including allows) is appended to decisions.log next to
this script, so a blocked or escalated attempt is on record even though
nothing about it appears in the model's own transcript.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_NETWORK_DOMAINS = {"api.ourcompany-support.example"}
ALLOWED_OUTPUT_DIR = "17-security-prompt-injection/guardrail-demo/output"

NETWORK_TOOL_RE = re.compile(r"\b(curl|wget|nc)\b")
BARE_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(:\d+)?$")


def extract_domains(command):
    domains = set()
    for token in command.split():
        token = token.strip("'\"")
        if token.startswith("http://") or token.startswith("https://"):
            domains.add(urlparse(token).netloc.split(":")[0])
        elif BARE_DOMAIN_RE.match(token):
            domains.add(token.split(":")[0])
    return domains


def decide(tool_name, tool_input):
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if ALLOWED_OUTPUT_DIR not in file_path:
            return "deny", (
                f"Write is restricted to {ALLOWED_OUTPUT_DIR}/ -- "
                f"{file_path!r} is outside the allowed output folder."
            )

    if tool_name == "Bash":
        command = tool_input.get("command", "")

        if NETWORK_TOOL_RE.search(command):
            domains = extract_domains(command)
            if not domains or not domains.issubset(ALLOWED_NETWORK_DOMAINS):
                return "deny", (
                    f"Network command {command!r} targets a domain outside "
                    f"the allow-list ({', '.join(ALLOWED_NETWORK_DOMAINS)})."
                )

        if re.search(r"\bgit push\b", command):
            return "ask", f"Pushing to a remote ({command!r}) needs a human to confirm."

    return "allow", None


def log_decision(payload, decision, reason):
    log_path = Path(__file__).resolve().parent / "decisions.log"
    entry = {
        "logged_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "session_id": payload.get("session_id"),
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
        "decision": decision,
        "reason": reason,
    }
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    payload = json.load(sys.stdin)
    decision, reason = decide(payload.get("tool_name", ""), payload.get("tool_input", {}))
    log_decision(payload, decision, reason)

    if decision == "allow":
        return  # exit 0, no JSON: no decision, normal permission flow proceeds

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


if __name__ == "__main__":
    main()
