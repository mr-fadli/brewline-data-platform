"""
Bronze ingestion orchestrator.

For each registered source: resolve its file on disk, extract it with the
right format parser, stamp it with lineage metadata, write it to parquet
(the durable archive), and load it into DuckDB (the queryable working copy).

Bronze does not clean, join, or interpret anything — it is a faithful,
lineage-stamped copy of exactly what each source handed over.
"""
import sys
from datetime import datetime, date, timezone
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from config import RAW_DIR, BRONZE_PARQUET_DIR, SOURCES
from db import get_connection
from extractors import EXTRACTORS
from logging_config import get_logger
logger = get_logger("bronze")


def resolve_file(source: dict, run_date: date | None = None) -> Path:
    """Finds the file for this source. If run_date is given, requires an
    exact dated filename (fails loudly if missing) — this is the interface
    a scheduled run (and later, Airflow) will use. If run_date is None,
    falls back to matching the source name with no date suffix, for the
    current single-batch generator output."""
    if run_date is not None:
        expected = RAW_DIR / f"{source['name']}_{run_date.isoformat()}.{source['format']}"
        if not expected.exists():
            raise FileNotFoundError(f"Expected file for {run_date} not found: {expected}")
        return expected

    matches = sorted(RAW_DIR.glob(f"{source['name']}*.{source['format']}"))
    if not matches:
        raise FileNotFoundError(f"No file found for source '{source['name']}' in {RAW_DIR}")
    if len(matches) > 1:
        raise ValueError(
            f"Ambiguous match for source '{source['name']}': {matches}. "
            f"Pass an explicit run_date to disambiguate."
        )
    return matches[0]


def stamp_lineage(df: pd.DataFrame, source_name: str, file_path: Path) -> pd.DataFrame:
    df = df.copy()
    df["_source_system"] = source_name
    df["_source_file"] = file_path.name
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    return df


def load_to_bronze(df: pd.DataFrame, table_name: str, con: duckdb.DuckDBPyConnection) -> int:
    parquet_path = BRONZE_PARQUET_DIR / f"{table_name}.parquet"

    # Nested columns (Shopify line_items/refunds) need pyarrow to serialize
    # correctly as parquet's native list<struct> type.
    df.to_parquet(parquet_path, index=False, engine="pyarrow")

    con.execute(f"""
        CREATE OR REPLACE TABLE bronze.{table_name} AS
        SELECT * FROM read_parquet('{parquet_path.as_posix()}')
    """)

    row_count = con.execute(f"SELECT COUNT(*) FROM bronze.{table_name}").fetchone()[0]
    return row_count


def run(run_date: date | None = None) -> None:
    con = get_connection()

    for source in SOURCES:
        name = source["name"]
        fmt = source["format"]
        extractor = EXTRACTORS[fmt]

        try:
            file_path = resolve_file(source, run_date=run_date)
            df = extractor(file_path)

            if df.empty:
                raise ValueError(f"Source '{name}' extracted 0 rows from {file_path} — refusing to load an empty table silently.")

            df = stamp_lineage(df, source_name=name, file_path=file_path)
            row_count = load_to_bronze(df, table_name=name, con=con)
            logger.info(f"bronze.{name} loaded: {row_count} rows <- {file_path.name}")

        except Exception as e:
            logger.error(f"{name} failed: {e}")
            raise  # fail loudly — a silently-skipped source is worse than a crashed run

    con.close()
    logger.info("Bronze Ingestion Completed")


if __name__ == "__main__":
    run()
