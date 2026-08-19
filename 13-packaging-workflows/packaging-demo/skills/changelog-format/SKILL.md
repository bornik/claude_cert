---
name: changelog-format
description: Use when the user asks to write or format a CHANGELOG entry. Not relevant for general questions, code review, or anything unrelated to changelog formatting.
---

CHANGELOG ENTRY FORMAT:
- One line per entry, starting with a past-tense verb (Added, Fixed, Changed, Removed).
- Reference the affected component in brackets, e.g. '[auth]', '[billing]'.
- No period at the end of the line.
- If the change is user-facing, add '(user-facing)' at the end.
- Group entries under a '## [Unreleased]' heading if none exists yet.
- Never mention internal ticket numbers or PR numbers in the entry itself.
