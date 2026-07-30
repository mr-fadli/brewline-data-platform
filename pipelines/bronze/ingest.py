"""
Bronze ingestion orchestrator (local dev).

For each registered source, resolves ALL available daily files, extracts and
stamps each one, then combines them according to the source's load_strategy:
  - "append": concatenate every day's file -- full history, matching how
    silver/gold models were built and verified.
  - "snapshot": load only the most recent day's file -- older snapshots are
    redundant with the newest, since each one already represents full state.

This intentionally diverges from the date-scoped, incremental loading used
in production (see ingest_bigquery.py) -- local dev's job is fast iteration
against complete history, not simulating a single day's arrival.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import duckdb
import pandas as pd

from config import RAW_DIR, BRONZE_PARQUET_DIR, SOURCES
from db import get_connection
from extractors import EXTRACTORS
from logging_config import get_logger

logger = get_logger("bronze")


def resolve_all_files(source: dict) -> list[Path]:
    """Returns every dated file for this source, sorted chronologically.
    Used for local dev's 'load everything' mode."""
    matches = sorted(RAW_DIR.glob(f"{source['name']}_*.{source['format']}"))
    if not matches:
        raise FileNotFoundError(f"No files found for source '{source['name']}' in {RAW_DIR}")
    return matches


def stamp_lineage(df: pd.DataFrame, source_name: str, file_path: Path) -> pd.DataFrame:
    df = df.copy()
    df["_source_system"] = source_name
    df["_source_file"] = file_path.name
    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    return df


def load_source(source: dict) -> pd.DataFrame:
    """Extracts and stamps this source's data, combined per its load_strategy."""
    extractor = EXTRACTORS[source["format"]]
    files = resolve_all_files(source)

    if source["load_strategy"] == "snapshot":
        files = [files[-1]]  # only the most recent day's full-state file

    frames = []
    for file_path in files:
        df = extractor(file_path)
        if df.empty:
            continue
        df = stamp_lineage(df, source_name=source["name"], file_path=file_path)
        frames.append(df)

    if not frames:
        raise ValueError(f"Source '{source['name']}' produced 0 rows across {len(files)} file(s) -- refusing to load empty.")

    return pd.concat(frames, ignore_index=True)


def load_to_bronze(df: pd.DataFrame, table_name: str, con: duckdb.DuckDBPyConnection) -> int:
    parquet_path = BRONZE_PARQUET_DIR / f"{table_name}.parquet"
    df.to_parquet(parquet_path, index=False, engine="pyarrow")

    con.execute(f"""
        CREATE OR REPLACE TABLE bronze.{table_name} AS
        SELECT * FROM read_parquet('{parquet_path.as_posix()}')
    """)
    return con.execute(f"SELECT COUNT(*) FROM bronze.{table_name}").fetchone()[0]


def run() -> None:
    con = get_connection()

    for source in SOURCES:
        name = source["name"]
        try:
            df = load_source(source)
            row_count = load_to_bronze(df, table_name=name, con=con)
            strategy_note = "latest snapshot" if source["load_strategy"] == "snapshot" else "all days combined"
            logger.info(f"bronze.{name:<26} {row_count:>5} rows  ({strategy_note})")
        except Exception as e:
            logger.error(f"{name} failed: {e}", exc_info=True)
            raise

    con.close()
    logger.info("Bronze ingestion complete.")


if __name__ == "__main__":
    run()