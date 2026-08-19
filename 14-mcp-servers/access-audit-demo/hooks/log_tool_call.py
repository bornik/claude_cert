#!/usr/bin/env python3
"""PostToolUse hook body: append one audit-log line per completed tool call.

Claude Code invokes this as a subprocess after every tool call finishes and
pipes the event as JSON on stdin. It runs whether or not the model mentions
the tool call in its reply, and there is no prompt-level instruction that
can suppress it -- that's the whole point of enforcing audit logging as a
hook instead of asking the model to self-report.
"""
import json
import sys
import time
from pathlib import Path


def main():
    payload = json.load(sys.stdin)

    cwd = payload.get("cwd", ".")
    log_path = Path(cwd) / "14-mcp-servers" / "access-audit-demo" / "audit.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "logged_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "session_id": payload.get("session_id"),
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
    }
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    main()
