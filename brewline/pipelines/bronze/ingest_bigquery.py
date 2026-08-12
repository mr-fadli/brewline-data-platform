"""
Production bronze ingestion: reads ONE day's raw file per source from the
GCS landing zone (matching Airflow's logical_date/run_date), writes
partitioned parquet to the GCS bronze zone, then loads BigQuery from that
same GCS parquet.

load_strategy (from config.py) determines how each source's single day's
file gets written into BigQuery:
  - "append":   Loaded into a plain staging table, then swapped into the
                real table's day via DELETE+INSERT DML scoped to
                _run_date -- history for other days untouched. NOT loaded
                directly via a $YYYYMMDD partition decorator: BigQuery has
                a known limitation where decorator loads can reject valid
                nested/repeated (array-of-struct) schemas even when the
                same schema and file load cleanly into the whole table.
  - "snapshot": WRITE_TRUNCATE on the whole table -- today's file already
                represents full current state, so it correctly replaces
                the entire table, not just one partition.
"""
import sys
import io
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import json
from datetime import datetime, date, timezone
from decimal import Decimal
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage, bigquery
from google.auth import impersonated_credentials
import google.auth

from brewline.config import SOURCES
from brewline.logging_config import get_logger
from brewline.pipelines.bronze.schemas import to_bigquery_schema, to_pyarrow_schema, validate_dataframe_schema, schema_signature, schema_diff

logger = get_logger("bronze_bigquery")

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
DATASET = "bronze"
IMPERSONATED_SA = os.environ["BRONZE_INGEST_SA"]
PARTITION_COLUMN = "_run_date"


def get_credentials():
    source_credentials, _ = google.auth.default()
    return impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=IMPERSONATED_SA,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def _bigquery_parquet_options() -> bigquery.ParquetOptions:
    """enable_list_inference must be set as an attribute after
    construction -- ParquetOptions.__init__() takes no kwargs in the
    google-cloud-bigquery client library, unlike most other *Options
    classes. Without this, BigQuery reads the file's physical 3-level
    LIST group (list -> element -> field) literally instead of
    collapsing it into the array type our explicit schema declares,
    which is what produces the 'array levels of 1 vs 0 repeated
    fields' mismatch for any REPEATED RECORD column (refunds,
    line_items)."""
    parquet_options = bigquery.ParquetOptions()
    parquet_options.enable_list_inference = True
    return parquet_options


def gcs_partition_path(zone: str, source_name: str, file_date: date, filename: str) -> str:
    return (
        f"{zone}/source_name={source_name}/"
        f"year={file_date.year:04d}/month={file_date.month:02d}/day={file_date.day:02d}/{filename}"
    )


def fetch_raw_file(bucket: storage.Bucket, source: dict, run_date: date) -> pd.DataFrame | None:
    """Returns None (not an exception) when the file is missing AND the
    source is marked non-required in config.py -- e.g. zendesk_tickets,
    which has no file on days with zero tickets. Any other source missing
    its file is still a hard failure: for required sources, a missing
    file means something upstream broke, not that nothing happened."""
    filename = f"{source['name']}_{run_date.isoformat()}.{source['format']}"
    blob = bucket.blob(gcs_partition_path("raw", source["name"], run_date, filename))
    if not blob.exists():
        if not source.get("required", True):
            logger.info(f"no raw file for '{source['name']}' on {run_date} -- treating as zero rows (not required daily)")
            return None
        raise FileNotFoundError(f"No raw file at gs://{BUCKET_NAME}/{blob.name}")

    raw_bytes = blob.download_as_bytes()
    if source["format"] == "csv":
        return pd.read_csv(io.BytesIO(raw_bytes), dtype=str)
    return pd.DataFrame(json.load(io.BytesIO(raw_bytes)))

def _normalize_value(value, arrow_type):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pa.types.is_decimal(arrow_type):
        return Decimal(str(value)) if not isinstance(value, Decimal) else value
    if pa.types.is_list(arrow_type):
        return [_normalize_value(v, arrow_type.value_type) for v in value]
    if pa.types.is_struct(arrow_type):
        return {f.name: _normalize_value(value.get(f.name), f.type) for f in arrow_type}
    return value
    
def build_arrow_table(df: pd.DataFrame, source_name: str) -> pa.Table:
    """Builds the pyarrow table strictly from the canonical schema in
    schemas.py -- no inference anywhere. Every column's type is a fact
    declared once and enforced every time. Assumes validate_dataframe_schema
    has already run upstream (in run(), right after lineage columns are
    stamped) -- the try/except below is a defensive backstop in case this
    is ever called directly without that validation pass."""
    schema = to_pyarrow_schema(source_name)
    arrays = []
    for field in schema:
        values = [_normalize_value(v, field.type) for v in df[field.name].tolist()]
        try:
            arrays.append(pa.array(values, type=field.type))
        except (pa.lib.ArrowInvalid, pa.lib.ArrowTypeError) as exc:
            raise ValueError(f"{source_name}.{field.name}: value doesn't match declared type {field.type} ({exc})") from exc
    return pa.Table.from_arrays(arrays, schema=schema)


def write_parquet_to_gcs(bucket: storage.Bucket, df: pd.DataFrame, source_name: str, run_date: date) -> str:
    table = build_arrow_table(df, source_name)
    buffer = io.BytesIO()
    # use_compliant_nested_type=True forces PyArrow's standard 3-tier list
    # encoding to name the inner field "element" (list.element), matching
    # what BigQuery's strict Parquet reader expects. PyArrow's default
    # names it "item" instead -- structurally still a valid repeated field
    # (build_arrow_table's explicit pa.list_(struct) schema already
    # guarantees that part), but a naming mismatch here is exactly the
    # kind of thing that shows up as a path like "line_items.list.element"
    # not resolving cleanly against the file's actual internal layout.
    pq.write_table(table, buffer, use_compliant_nested_type=True)
    buffer.seek(0)
    blob_path = gcs_partition_path("bronze", source_name, run_date, "part-0000.parquet")
    bucket.blob(blob_path).upload_from_file(buffer, content_type="application/octet-stream")
    return f"gs://{BUCKET_NAME}/{blob_path}"


def ensure_table(client: bigquery.Client, table_id: str, source_name: str) -> bool:
    """Pre-creates the table with the canonical schema (schemas.py) and
    day-partitioning on _run_date if it doesn't exist yet. Required because
    loading into a $YYYYMMDD partition decorator can't auto-create a
    partitioned table -- the partitioning scheme must already exist on the
    table before a decorated load runs. Returns True if this call just
    created the table (fresh), False if it already existed.

    If the table DOES already exist, its live schema is compared against
    the current canonical schema. schemas.py can change over time (a new
    struct subfield, a retyped column) without anyone remembering to
    migrate every table that was created under an older version of it.
    BigQuery load jobs can't silently reconcile a structural mismatch like
    that -- they just reject the load with a cryptic 400. Catching the
    drift here instead means a clear, actionable error at the start of the
    run, naming the table, instead of a BigQuery error surfacing deep
    inside a load job for a reason that isn't obvious from the message.

    Partitioning is on _run_date (the logical/business date the pipeline
    is processing), NOT _ingested_at (true wall-clock execution time).
    Real warehouses partition fact tables by business/event date, not by
    when the pipeline happened to run -- if you backfill three months of
    history in one afternoon, every row's real ingestion timestamp would
    be today, collapsing three months of data into a single partition.
    _run_date/logical_date represents which day's data this is,
    independent of when the pipeline actually executed."""
    canonical_schema = to_bigquery_schema(source_name)
    try:
        existing = client.get_table(table_id)
    except Exception:
        table = bigquery.Table(table_id, schema=canonical_schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field=PARTITION_COLUMN,
        )
        client.create_table(table)
        logger.info(f"created table {table_id} with explicit schema")
        return True

    existing_sig = schema_signature(existing.schema)
    canonical_sig = schema_signature(canonical_schema)
    if existing_sig != canonical_sig:
        diff = schema_diff(existing_sig, canonical_sig)
        raise RuntimeError(
            f"{table_id} already exists but its live schema no longer matches "
            f"the canonical schema in schemas.py. Diff:\n{diff}\n"
            f"If this is a real structural change (e.g. a new/retyped "
            f"field), it's a deliberate migration: drop and recreate, e.g. "
            f"`bq rm -t {table_id}`, then rerun. If the diff only shows a "
            f"type-name spelling difference (e.g. FLOAT vs FLOAT64), extend "
            f"_TYPE_ALIASES in schemas.py instead -- that's not real drift."
        )
    return False


def load_bigquery_from_gcs(client: bigquery.Client, gcs_uri: str, source: dict, run_date: date) -> int:
    table_id = f"{PROJECT_ID}.{DATASET}.{source['name']}"
    schema = to_bigquery_schema(source["name"])

    if source["load_strategy"] == "snapshot":
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition="WRITE_TRUNCATE",
            schema=schema,  # explicit -- never inferred, ever
            parquet_options=_bigquery_parquet_options(),
        )
        load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
        load_job.result()
        return client.get_table(table_id).num_rows

    return _load_append_via_staging(client, gcs_uri, table_id, schema, source["name"], run_date)


def _load_append_via_staging(
    client: bigquery.Client,
    gcs_uri: str,
    table_id: str,
    schema: list,
    source_name: str,
    run_date: date,
) -> int:
    """Loads an "append" source's file into a plain staging table (no
    partition decorator involved at all), then swaps that day's rows into
    the real table via DML.

    This exists because loading Parquet files with nested/repeated
    (array-of-struct) fields directly into a $YYYYMMDD partition decorator
    is a known BigQuery limitation -- the decorator-load code path can
    reject a schema as a mismatch even when that exact schema and file
    load cleanly into the table as a whole. Routing through an undecorated
    staging load sidesteps that code path entirely -- only the final DML
    touches the partitioned table, and it's scoped to exactly one day
    (_run_date), leaving every other partition's history untouched. This
    is what makes backfills and reruns for a single day safe and
    idempotent: rerunning the same day just deletes-then-reinserts that
    day's rows, never anything else."""
    ensure_table(client, table_id, source_name)
    staging_table_id = f"{table_id}_staging"

    # Fresh, unpartitioned staging table every run -- WRITE_TRUNCATE means
    # stale content from a previous failed run can't leak into the swap.
    staging_job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition="WRITE_TRUNCATE",
        schema=schema,
        parquet_options=_bigquery_parquet_options(),
    )
    load_job = client.load_table_from_uri(gcs_uri, staging_table_id, job_config=staging_job_config)
    load_job.result()

    swap_sql = f"""
    DELETE FROM `{table_id}` WHERE {PARTITION_COLUMN} = @run_date;
    INSERT INTO `{table_id}` SELECT * FROM `{staging_table_id}`;
    """
    query_job = client.query(
        swap_sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("run_date", "DATE", run_date)]
        ),
    )
    query_job.result()

    client.delete_table(staging_table_id, not_found_ok=True)
    return client.get_table(table_id).num_rows


def inspect_gcs_parquet_schema(source_name: str, run_date: date) -> None:
    """Diagnostic only -- not part of the pipeline. Downloads whatever
    Parquet file is CURRENTLY sitting at the bronze GCS path for this
    source/date and prints its real physical schema, independent of
    BigQuery entirely. Use this to check whether a file has actually been
    regenerated by the current write_parquet_to_gcs before assuming a
    BigQuery load error is caused by today's code -- a load error against
    an un-regenerated file will look identical to a genuine writer bug,
    but the fix ("rerun write_parquet_to_gcs for that date") is different
    from a fix to build_arrow_table itself.

    Usage: python -c "from ingest_bigquery import inspect_gcs_parquet_schema; \
        from datetime import date; \
        inspect_gcs_parquet_schema('shopify_orders', date(2026, 6, 8))"
    """
    credentials = get_credentials()
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_path = gcs_partition_path("bronze", source_name, run_date, "part-0000.parquet")
    blob = bucket.blob(blob_path)
    if not blob.exists():
        print(f"No file at gs://{BUCKET_NAME}/{blob_path}")
        return

    raw_bytes = blob.download_as_bytes()
    buffer = io.BytesIO(raw_bytes)

    parquet_file = pq.ParquetFile(buffer)
    print(f"gs://{BUCKET_NAME}/{blob_path}")
    print(f"  generated_by: {parquet_file.metadata.created_by}")
    print("\n--- RAW PHYSICAL parquet schema (what BigQuery's error is actually about) ---")
    print(parquet_file.schema)  # low-level: shows REPEATED/OPTIONAL groups explicitly

    print("\n--- Reconstructed ARROW logical schema (what pq.read_schema()/.equals() sees) ---")
    arrow_schema = parquet_file.schema_arrow
    print(arrow_schema)

    expected = to_pyarrow_schema(source_name)
    if arrow_schema.equals(expected, check_metadata=False):
        print("\nLogical schema MATCHES canonical schema.")
    else:
        print("\nLogical schema DOES NOT MATCH canonical schema -- this file predates it and needs to be regenerated.")

    print(
        "\nNote: a logical-schema match does not guarantee the physical layout "
        "above is a strict 3-tier repeated group for every list column -- "
        "compare the RAW PHYSICAL schema's line_items entry directly against "
        "the 'array levels' BigQuery is complaining about."
    )


def run(run_date: date = None):
    run_date = run_date or date.today()
    credentials = get_credentials()
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)

    for source in SOURCES:
        name = source["name"]
        try:
            df = fetch_raw_file(bucket, source, run_date)
            if df is None:
                # Optional source, no file today -- nothing to load, move
                # on to the next source rather than treating this as a
                # pipeline-wide failure.
                logger.info(f"bronze.{name}: skipped, no data for {run_date}")
                continue

            df["_source_system"] = name
            df["_ingested_at"] = datetime.now(timezone.utc)
            df["_run_date"] = run_date

            validate_dataframe_schema(df, name)

            gcs_uri = write_parquet_to_gcs(bucket, df, name, run_date)
            total_rows = load_bigquery_from_gcs(bq_client, gcs_uri, source, run_date)

            strategy_note = "full snapshot replace" if source["load_strategy"] == "snapshot" else f"partition {run_date}"
            logger.info(f"bronze.{name}: {len(df)} rows this run ({strategy_note}) -> {gcs_uri}, {total_rows} total in BigQuery")
        except Exception as exc:
            logger.error(f"bronze ingestion failed for '{name}': {exc}", exc_info=True)
            raise

def _parse_cli_date() -> date:
    if len(sys.argv) > 1:
        try:
            return date.fromisoformat(sys.argv[1])
        except ValueError:
            raise SystemExit(f"Invalid date '{sys.argv[1]}' -- expected format YYYY-MM-DD")
    return date.today()


if __name__ == "__main__":
    run(run_date=_parse_cli_date())