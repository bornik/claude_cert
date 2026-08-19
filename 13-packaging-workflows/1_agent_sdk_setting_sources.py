"""
EXAMPLE 1: `setting_sources` — Whether the Agent SDK Sees Your Project's Skills

Module 09's `3_skills_on_demand_vs_always_on.py` showed that a delegated
subagent doesn't automatically inherit a Skill the parent session loaded.
This script shows the sibling case: when you drive Claude through the
Agent SDK (`claude_agent_sdk.query()`) instead of the interactive Claude
Code CLI, does it even discover a project's `.claude/skills/` directory
at all? The answer is controlled by ONE option: `setting_sources`
(verified in `claude_agent_sdk/types.py`, `ClaudeAgentOptions.setting_sources`):

- `None` (the default, i.e. simply omitting it) — every filesystem source
  (user/project/local) loads, matching the interactive CLI's own defaults.
  This is NOT an opt-in you have to request; it's what happens if you say
  nothing.
- `[]` — SDK isolation mode. No `.claude/` directory is read at all,
  from anywhere. A project's Skills, CLAUDE.md, and settings.json all
  become invisible, regardless of how good their descriptions are.
- `["project"]` — an explicit allowlist: only `.claude/` in `cwd` loads
  (not `~/.claude/`, not `.claude/settings.local.json`). The docstring
  notes `"project"` must be present for CLAUDE.md to load too, so this is
  also the minimum needed to pick up project-level Skills.

All three calls below point `cwd` at `sdk_fixture/`, which ships its own
`.claude/skills/changelog-format/SKILL.md` (a standalone copy of the same
skill from Module 09 and this module's `packaging-demo/` plugin — kept
separate so this script runs on its own, independent of whether you've
done the CLI plugin-install walkthrough in this module's README). Every
call asks the same changelog-formatting question; only `setting_sources`
changes between them.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

FIXTURE_CWD = str(Path(__file__).resolve().parent / "sdk_fixture")

REQUEST = "Write a changelog entry: we fixed a bug where billing invoices double-charged annual plans."


async def run(label: str, setting_sources):
    print(f"\n{'=' * 70}\n{label}  (setting_sources={setting_sources!r})\n{'=' * 70}")

    result_text = None
    async for message in query(
        prompt=REQUEST,
        options=ClaudeAgentOptions(
            model="claude-haiku-4-5",
            cwd=FIXTURE_CWD,
            max_turns=4,
            permission_mode="bypassPermissions",
            setting_sources=setting_sources,
        ),
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result
            print(f"💰 Usage: {message.usage['input_tokens']} in / {message.usage['output_tokens']} out — ~${message.total_cost_usd:.5f}")

    print(f"→ {result_text.strip() if result_text else '(no result)'}")
    return result_text


async def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Agent SDK setting_sources — Filesystem Skill Discovery")
    print("=" * 70)

    default_result = await run("DEFAULT (omitted → None)", None)
    isolated_result = await run("ISOLATED (setting_sources=[])", [])
    project_result = await run('EXPLICIT PROJECT (setting_sources=["project"])', ["project"])

    print("""
======================================================================
KEY TAKEAWAY
======================================================================
The default run and the explicit ["project"] run should both follow the
skill's exact format (component tag in brackets, no trailing period,
'(user-facing)' suffix) — the fixture's SKILL.md loaded in both cases.
The isolated ([]) run has no access to that file at all, so it falls back
to whatever generic changelog format Claude produces from general
knowledge — different wording, no guarantee of matching the house style.

This is a different failure mode than Module 09's subagent case: there,
a Skill the PARENT loaded didn't carry over to a fresh delegated call.
Here, nothing ever "loaded" in the parent sense — the Agent SDK simply
never looked at the filesystem unless setting_sources told it to. Any
code driving Claude through the SDK (a backend job, a CI script, a
custom agent) inherits this: skip setting_sources and you get the CLI's
full defaults; pass [] for a clean-room run with zero project state;
pass a specific list to load exactly what you intend and nothing more.
""")


if __name__ == "__main__":
    asyncio.run(main())
