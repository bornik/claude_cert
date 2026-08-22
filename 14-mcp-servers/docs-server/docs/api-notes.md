# Internal API Notes

The `/status` endpoint returns **200** for a healthy node and **503**
when the node is draining. Poll it no more than once every 5 seconds —
see [rate limit policy](./rate-limits.md) for why.

Authentication uses a short-lived token, refreshed via `refresh_token()`:

```python
def refresh_token(old_token):
    return auth_client.exchange(old_token)
```

Tokens expire after *15 minutes*; there is no grace period.
