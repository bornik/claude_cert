"""
EXAMPLE 1: Message Batches API — Async Bulk Processing

For a handful of prompts, calling messages.create() one at a time is
fine. For thousands of independent prompts (classify every ticket from
last week, summarize every document in a batch job), the Batches API
submits them all as ONE request and processes them asynchronously,
usually at a lower cost than the same calls made synchronously.

This example submits a small batch (3 independent classification
requests), polls until it finishes, and streams back each result by its
custom_id — the same id you supplied, so you can match a result back to
the request that produced it without relying on response order.
"""

import sys
import time
from pathlib import Path

from anthropic import Anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()
client = Anthropic()

TICKETS = {
    "ticket-1": "My card was charged twice for the same order.",
    "ticket-2": "The app crashes every time I open the settings page.",
    "ticket-3": "Can you tell me more about your enterprise pricing tiers?",
}

POLL_INTERVAL_SECONDS = 5
MAX_POLLS = 24  # ~2 minutes of polling before we give up and just report status


def submit_batch():
    print("\n" + "=" * 70)
    print("Step 1: Submit all requests as ONE batch")
    print("=" * 70)

    requests = [
        Request(
            custom_id=custom_id,
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5",
                max_tokens=50,
                messages=[
                    {
                        "role": "user",
                        "content": f"In one word (billing/bug/sales), classify this ticket: {text}",
                    }
                ],
            ),
        )
        for custom_id, text in TICKETS.items()
    ]

    batch = client.messages.batches.create(requests=requests)
    print(f"Batch id: {batch.id}")
    print(f"Initial status: {batch.processing_status}")
    print(f"Request counts: {batch.request_counts}")
    return batch.id


def poll_until_done(batch_id):
    print("\n" + "=" * 70)
    print("Step 2: Poll until processing finishes (or we give up)")
    print("=" * 70)

    for attempt in range(1, MAX_POLLS + 1):
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Poll {attempt}: status={batch.processing_status}, counts={batch.request_counts}")
        if batch.processing_status == "ended":
            return batch
        time.sleep(POLL_INTERVAL_SECONDS)

    print(f"Still not done after {MAX_POLLS * POLL_INTERVAL_SECONDS}s — batches can take much "
          "longer for large workloads. Returning current (incomplete) status.")
    return batch


def show_results(batch):
    if batch.processing_status != "ended":
        print("\n(Batch hasn't ended yet — no results to stream. This is normal; batches "
              "are designed to be checked back on later, not waited on synchronously.)")
        return

    print("\n" + "=" * 70)
    print("Step 3: Stream results, matched back to requests by custom_id")
    print("=" * 70)
    for result in client.messages.batches.results(batch.id):
        original_ticket = TICKETS.get(result.custom_id, "(unknown)")
        if result.result.type == "succeeded":
            text = next((b.text for b in result.result.message.content if b.type == "text"), "")
            print(f"{result.custom_id} ({original_ticket!r}) -> {text.strip()}")
        else:
            print(f"{result.custom_id}: {result.result.type} (not a normal success)")


def main():
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Message Batches API")
    print("=" * 70)

    batch_id = submit_batch()
    batch = poll_until_done(batch_id)
    show_results(batch)

    print("""
📝 Takeaway: one `batches.create()` call queued 3 independent requests;
we polled `batches.retrieve()` for status instead of blocking on 3
separate synchronous calls. `custom_id` is what lets you map a result
back to its original request — results can come back in ANY order, so
never assume result[i] corresponds to request[i]. Batches are built for
large volumes processed asynchronously (often cheaper per-request), not
for latency-sensitive single requests — don't reach for this when you
need an answer back in the same request/response cycle.
""")


if __name__ == "__main__":
    main()
