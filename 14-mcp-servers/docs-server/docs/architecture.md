# System Architecture

The ingest pipeline has **three** stages: fetch, transform, and load.

## Fetch

Pulls raw events from the `events` queue. See [the queue config](./queue.md)
for retry settings.

## Transform

Normalizes field names and drops any record missing a `user_id`. Uses
the `normalize()` function:

```python
def normalize(record):
    return {k.lower(): v for k, v in record.items()}
```

## Load

Writes normalized records to the warehouse in batches of 500. Failed
batches retry with *exponential* backoff, up to 5 attempts.
