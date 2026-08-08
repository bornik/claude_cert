"""
Shared helper: print token usage and estimated cost after an API call.

Import from any example script with:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from common.usage import print_usage
"""

# Prices per million tokens (input, output). Update if you switch models.
PRICING = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
}


def print_usage(response, model: str | None = None) -> None:
    """Print input/output token counts and an estimated cost for one API response."""
    usage = response.usage
    model = model or response.model

    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0

    # API responses sometimes return a dated model ID (e.g. "claude-haiku-4-5-20251001")
    price_in, price_out = next(
        ((i, o) for prefix, (i, o) in PRICING.items() if model.startswith(prefix)),
        (None, None),
    )

    print(f"💰 Usage ({model}): {input_tokens} in / {output_tokens} out", end="")
    if cache_read or cache_write:
        print(f" (+{cache_write} cache write, +{cache_read} cache read)", end="")

    if price_in is not None:
        cost = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
        print(f" — ~${cost:.5f}")
    else:
        print(" — (unknown pricing for this model)")
