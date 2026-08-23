# Design Doc — Support Ticket Urgency Classifier

A filled-in example of the four decisions the lesson asks you to write
down *before* implementation, for the feature evaluated in
[`1_eval_pipeline_and_graders.py`](1_eval_pipeline_and_graders.py) demo 1.
Written first, so the eval, the error handling, and the tool permissions
below all check against the same page instead of drifting apart.

## 1. Success criteria

Given the text of one support ticket, classify it as exactly one of
`high`, `medium`, `low`:

- `high` — active money movement, an outage, or a security issue (double
  charge, production auth failure, data exposure).
- `medium` — a real request that isn't time-critical (address change,
  non-urgent account update).
- `low` — feedback, a feature request, or a question with no pending
  action.

This is what `URGENCY_DATASET` in the script's demo 1 encodes as
input/expected pairs, and what `grade_exact_match` checks output against.

## 2. Failure handling

| Failure | Retriable? | User-facing behavior |
|---|---|---|
| API rate limit / 5xx from the model | Yes — retry with backoff, up to 3 attempts | Ticket stays queued as "pending classification"; no visible error |
| Model returns a label outside `{high, medium, low}` | No | Ticket routed to `medium` by default, flagged for human review |
| Ticket text is empty or unreadable | No | Ticket routed to `medium` by default, flagged for human review |
| Model call times out after all retries | No | Ticket routed to `high` by default (fail toward more attention, not less), flagged for human review |

The default-on-terminal-failure is deliberately not uniform: silently
dropping a possibly-urgent ticket to `low` is the one failure mode this
feature cannot have, so unclassifiable tickets bias toward more scrutiny,
not less.

## 3. Cost and latency budget

- **Per-request budget:** ≤ 20 input tokens of ticket text on average, ≤ 5
  output tokens (single-word label) — this is why `CLASSIFY_SYSTEM` in
  the script demands "reply with only that word."
- **Latency target:** classification must complete in under 2 seconds so
  it can run synchronously in the ticket-intake path, not as a background
  job.
- **Monthly cost ceiling:** at an estimated 50,000 tickets/month and
  `claude-haiku-4-5` pricing, this is well under $10/month — the budget
  exists mainly to catch a regression (e.g. an accidental switch to a
  larger model or a verbose system prompt) before it 10x's the bill.
- **Reliability floor:** ≥ 95% exact-match agreement with the eval set in
  `URGENCY_DATASET`, re-checked on every prompt change per the iteration
  loop in demo 5. Below that floor, the feature does not ship regardless
  of how good any individual example looks.

## 4. Trust boundary

- **Untrusted input:** the ticket body is customer-authored text. It is
  read-only input to the classifier — nothing in the ticket body is ever
  treated as an instruction to the model, and the classifier has no
  tools, so there is no action a crafted ticket could trigger even if it
  tried (compare
  [`17-security-prompt-injection/1_indirect_prompt_injection.py`](../17-security-prompt-injection/1_indirect_prompt_injection.py),
  where a similar ticket-reading agent *does* have a `send_email` tool
  and needs a least-privilege allow-list because of it).
- **Smallest set of actions needed:** one read (the ticket text) and one
  write (the urgency label back onto the ticket record). No email, no
  external API calls, no access to other tickets or customer records —
  this classifier's entire footprint is a single label field.
