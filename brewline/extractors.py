"""Format-based bronze extractors. These do ONLY mechanical parsing —
no cleaning, no type-fixing, no business logic. Bronze must stay a
faithful copy of whatever the source handed over."""
import json
import pandas as pd
from pathlib import Path


def extract_csv(path: Path) -> pd.DataFrame:
    # dtype=str is deliberate: pandas' type inference is itself a transformation
    # decision (e.g. it will silently guess a long digit-string like a tracking
    # number is an integer, which can overflow). Bronze should stay untyped and
    # faithful; casting to real types happens explicitly in silver.
    return pd.read_csv(path, dtype=str)


def extract_json(path: Path) -> pd.DataFrame:
    with open(path) as f:
        data = json.load(f)
    # Nested fields (Shopify's line_items/refunds) are kept as-is inside
    # each cell — flattening them is a silver-layer decision, not bronze's.
    return pd.DataFrame(data)


EXTRACTORS = {
    "csv": extract_csv,
    "json": extract_json,
}
