# pipelines/bronze/schemas.py
"""
Canonical bronze schemas, one definition per source, used consistently for
BOTH BigQuery table creation and pyarrow/parquet writing. This is the fix
for schema drift: every load job uses this exact schema explicitly --
nothing is ever inferred from a single day's data again, anywhere.

CSV sources are declared entirely as STRING, matching bronze's existing
principle of staying untyped for anything read via pandas' dtype=str
(established earlier to avoid pandas mis-inferring large digit-strings as
overflowing integers). JSON sources keep their source-native types, since
JSON itself is typed.
"""
from google.cloud import bigquery
import pandas as pd
import pyarrow as pa
from decimal import Decimal
from datetime import datetime, date

LINEAGE_FIELDS = [
    ("_source_system", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
    ("_run_date", "DATE"),
]

SCHEMAS = {
    "shopify_orders": [
        ("order_id", "STRING"),
        ("customer_email", "STRING"),
        ("created_at", "STRING"),
        ("currency", "STRING"),
        ("total_price", "NUMERIC"),
        ("source_name", "STRING"),
        ("financial_status", "STRING"),
        ("cancelled_at", "STRING"),
        ("refunds", "RECORD_REPEATED", [
            ("refund_id", "STRING"), ("amount", "NUMERIC"),
            ("created_at", "STRING"), ("reason", "STRING"),
        ]),
        ("line_items", "RECORD_REPEATED", [
            ("sku", "STRING"), ("name", "STRING"),
            ("qty", "INT64"), ("price", "NUMERIC"),
        ]),
    ] + LINEAGE_FIELDS,

    "recharge_subscriptions": [
        ("subscription_id", "STRING"),
        ("customer_email", "STRING"),
        ("status", "STRING"),
        ("frequency_days", "INT64"),
        ("created_at", "STRING"),
        ("next_charge_date", "STRING"),
        ("cancelled_at", "STRING"),
        ("cancellation_reason", "STRING"),
        ("linked_shopify_order_id", "STRING"),
    ] + LINEAGE_FIELDS,

    "square_transactions": [
        ("transaction_id", "STRING"), ("location_id", "STRING"), ("item_sku", "STRING"),
        ("item_name", "STRING"), ("qty", "STRING"), ("unit_price", "STRING"),
        ("discount", "STRING"), ("payment_type", "STRING"), ("employee_id", "STRING"),
        ("created_at_local", "STRING"), ("customer_phone", "STRING"),
    ] + LINEAGE_FIELDS,

    "zendesk_tickets": [
        ("ticket_id", "STRING"), ("requester_email", "STRING"), ("subject", "STRING"),
        ("created_at", "STRING"), ("tags", "STRING"), ("related_order_id", "STRING"),
    ] + LINEAGE_FIELDS,

    "shipstation_shipments": [
        ("shipment_id", "STRING"), ("shopify_order_id", "STRING"), ("tracking_number", "STRING"),
        ("carrier", "STRING"), ("ship_date", "STRING"), ("status", "STRING"), ("last_scan_at", "STRING"),
    ] + LINEAGE_FIELDS,
}


def to_bigquery_schema(source_name: str) -> list[bigquery.SchemaField]:
    fields = []
    for spec in SCHEMAS[source_name]:
        if len(spec) == 3 and spec[1] == "RECORD_REPEATED":
            name, _, subfields = spec
            sub = [bigquery.SchemaField(n, t) for n, t in subfields]
            fields.append(bigquery.SchemaField(name, "RECORD", mode="REPEATED", fields=sub))
        else:
            name, bq_type = spec
            fields.append(bigquery.SchemaField(name, bq_type))
    return fields


# BigQuery's API always echoes back legacy SQL type names from get_table()
# (FLOAT, INTEGER, BOOLEAN, RECORD) even when a table was created using
# Standard SQL aliases (FLOAT64, INT64, BOOL, STRUCT) as declared in
# SCHEMAS. Comparing field_type strings literally makes ensure_table
# raise a false-positive drift error on every run after the first,
# because the "live" schema and "canonical" schema are semantically
# identical but spelled differently. Normalize both sides to one
# canonical name before comparing.
_TYPE_ALIASES = {
    "INTEGER": "INT64", "INT64": "INT64",
    "NUMERIC": "NUMERIC", "DECIMAL": "NUMERIC",   # DuckDB calls it DECIMAL, BigQuery calls it NUMERIC — same concept
    "BOOLEAN": "BOOL", "BOOL": "BOOL",
    "STRUCT": "RECORD", "RECORD": "RECORD",
}


def schema_signature(fields) -> tuple:
    """Structural signature (name, type, mode, nested subfields) for a list
    of bigquery.SchemaField, order-independent and alias-independent.
    Used to detect real drift between a live BigQuery table's schema and
    the current canonical schema in SCHEMAS -- e.g. a table created
    before a nested struct field like refunds.refund_id existed.

    NOTE: this is the ONLY definition of schema_signature in this file.
    A duplicate definition further down (even one that looks identical
    or "more correct") will silently shadow this one -- Python keeps
    whichever def runs last, with no warning or error. If drift checks
    ever start behaving like this normalization isn't applied, grep this
    file for `def schema_signature` and confirm there's exactly one hit."""
    sig = []
    for f in fields:
        sub = schema_signature(f.fields) if f.fields else ()
        normalized_type = _TYPE_ALIASES.get(f.field_type, f.field_type)
        sig.append((f.name, normalized_type, f.mode, sub))
    return tuple(sorted(sig))


def schema_diff(existing_sig: tuple, canonical_sig: tuple) -> str:
    """Set-difference between two schema_signature() outputs, formatted
    for a human. Shows exactly which field(s) differ instead of a blanket
    'schema doesn't match' -- tells you at a glance whether it's a real
    structural change (needs a migration) or just a spelling/alias gap
    (needs _TYPE_ALIASES extended)."""
    existing_set, canonical_set = set(existing_sig), set(canonical_sig)
    only_existing = existing_set - canonical_set
    only_canonical = canonical_set - existing_set
    lines = []
    if only_existing:
        lines.append("  in LIVE table but not canonical schemas.py:")
        lines += [f"    {f}" for f in sorted(only_existing)]
    if only_canonical:
        lines.append("  in canonical schemas.py but not LIVE table:")
        lines += [f"    {f}" for f in sorted(only_canonical)]
    return "\n".join(lines)


_PA_TYPE_MAP = {
    "STRING": pa.string(),
    "NUMERIC": pa.decimal128(18, 4),   # 18 total digits, 4 after the decimal — plenty for currency
    "INT64": pa.int64(),
    "TIMESTAMP": pa.timestamp("us", tz="UTC"),
    "DATE": pa.date32(),
}

def to_pyarrow_schema(source_name: str) -> pa.Schema:
    fields = []
    for spec in SCHEMAS[source_name]:
        if len(spec) == 3 and spec[1] == "RECORD_REPEATED":
            name, _, subfields = spec
            struct_type = pa.struct([(n, _PA_TYPE_MAP[t]) for n, t in subfields])
            fields.append(pa.field(name, pa.list_(struct_type)))
        else:
            name, bq_type = spec
            fields.append(pa.field(name, _PA_TYPE_MAP[bq_type]))
    return pa.schema(fields)


def validate_dataframe_schema(df: pd.DataFrame, source_name: str) -> None:
    """Validates df against the canonical schema BEFORE any parquet/pyarrow
    conversion is attempted. Raises a specific, readable ValueError naming
    exactly which column and row is wrong, instead of letting a cryptic
    pyarrow.lib.ArrowTypeError or a BigQuery load-job error surface later,
    several steps removed from the actual bad value."""
    schema = to_pyarrow_schema(source_name)
    expected_columns = {f.name for f in schema}
    actual_columns = set(df.columns)

    missing = expected_columns - actual_columns
    if missing:
        raise ValueError(f"[{source_name}] missing expected columns: {sorted(missing)}")

    extra = actual_columns - expected_columns
    if extra:
        raise ValueError(
            f"[{source_name}] unexpected columns not declared in schemas.py: {sorted(extra)}. "
            f"Add them to SCHEMAS or drop them before writing -- nothing rides along silently."
        )

    for field in schema:
        _validate_column(df[field.name], field, source_name)


def _validate_column(col: pd.Series, field: "pa.Field", source_name: str) -> None:
    notnull = col.notna()
    if not notnull.any():
        return  # entire column is null -- trivially valid, nothing to check

    if pa.types.is_list(field.type) or pa.types.is_struct(field.type):
        # Nested types can't be checked with a dtype-level shortcut -- a
        # list/struct column is always object dtype holding real Python
        # objects. Iterate, but only over non-null values, and stop at the
        # first 5 problems instead of walking the whole column regardless.
        bad = []
        for i, value in col[notnull].items():
            if not _matches_type(value, field.type):
                bad.append((i, type(value).__name__, repr(value)[:80]))
            if len(bad) >= 5:
                break
    else:
        # Scalar types: skip per-element isinstance() checks entirely when
        # the column's pandas dtype already guarantees the right type (a
        # float64 column cannot contain a stray string). Only object-dtype
        # columns -- where pandas can't guarantee homogeneity -- fall back
        # to an element-wise pass, via col.map(), which is a fast Cython
        # loop rather than a pure-Python for/enumerate loop.
        mask = _scalar_type_mask(col, field.type)
        bad_idx = col.index[notnull & ~mask]
        bad = [(i, type(col[i]).__name__, repr(col[i])[:80]) for i in bad_idx[:5]]

    if bad:
        detail = "; ".join(f"row {i}: got {t} -> {v}" for i, t, v in bad)
        raise ValueError(
            f"[{source_name}] column '{field.name}' expected {field.type}, "
            f"found mismatched value(s): {detail}"
        )


def _scalar_type_mask(col: pd.Series, arrow_type) -> pd.Series:
    """Vectorized-first type check for scalar (non-nested) columns. When
    the column's pandas dtype already guarantees the target type, returns
    an all-True mask with no per-element work at all. Only falls back to
    col.map() -- one pass, C-level iteration, not a Python for-loop -- for
    object-dtype columns, where individual elements could genuinely be
    anything (this is exactly the case that caught '555-1754' earlier)."""
    if pa.types.is_decimal(arrow_type):
        if pd.api.types.is_float_dtype(col) or pd.api.types.is_integer_dtype(col):
            return pd.Series(True, index=col.index)
        return col.map(lambda v: pd.isna(v) or (isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)))
    if pa.types.is_string(arrow_type):
        if pd.api.types.is_string_dtype(col) and not pd.api.types.is_object_dtype(col):
            return pd.Series(True, index=col.index)
        return col.map(lambda v: pd.isna(v) or isinstance(v, str))
    if pa.types.is_floating(arrow_type):
        if pd.api.types.is_float_dtype(col):
            return pd.Series(True, index=col.index)
        return col.map(lambda v: pd.isna(v) or (isinstance(v, (int, float)) and not isinstance(v, bool)))
    if pa.types.is_integer(arrow_type):
        if pd.api.types.is_integer_dtype(col):
            return pd.Series(True, index=col.index)
        return col.map(lambda v: pd.isna(v) or (isinstance(v, int) and not isinstance(v, bool)))
    if pa.types.is_timestamp(arrow_type) or pa.types.is_date(arrow_type):
        if pd.api.types.is_datetime64_any_dtype(col):
            return pd.Series(True, index=col.index)
        return col.map(lambda v: pd.isna(v) or isinstance(v, (str, datetime, date)))
    return pd.Series(True, index=col.index)  # anything not explicitly modeled above passes through


def _matches_type(value, arrow_type) -> bool:
    if pa.types.is_decimal(arrow_type):
        return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
    if pa.types.is_string(arrow_type):
        return isinstance(value, str)
    if pa.types.is_floating(arrow_type):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if pa.types.is_integer(arrow_type):
        return isinstance(value, int) and not isinstance(value, bool)
    if pa.types.is_timestamp(arrow_type) or pa.types.is_date(arrow_type):
        return isinstance(value, (str, datetime, date))
    if pa.types.is_list(arrow_type):
        return isinstance(value, list) and all(_matches_type(v, arrow_type.value_type) for v in value)
    if pa.types.is_struct(arrow_type):
        if not isinstance(value, dict):
            return False
        return all(
            (value.get(f.name) is None) or _matches_type(value[f.name], f.type)
            for f in arrow_type
        )
    return True  # anything not explicitly modeled above passes through rather than blocking