"""Central configuration for the Brewline bronze pipeline."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

REFERENCE_DIR = PROJECT_ROOT / "references"

BRONZE_DIR = PROJECT_ROOT / "pipelines" / "bronze"
RAW_DIR = BRONZE_DIR / "raw"
BRONZE_PARQUET_DIR = BRONZE_DIR / "parquet"

DB_PATH = PROJECT_ROOT / "brewline.duckdb"

BRONZE_PARQUET_DIR.mkdir(parents=True, exist_ok=True)

# load_strategy:
#   "append"   -- each day's file is new, distinct facts; local dev loads ALL days,
#                 concatenated, to reproduce full history for testing.
#   "snapshot" -- each day's file is a full current-state snapshot; local dev loads
#                 only the LATEST day's file, since older snapshots are redundant
#                 with the newest one (loading all would triple/30x-count rows).
SOURCES = [
    {"name": "shopify_orders", "format": "json", "load_strategy": "append"},
    {"name": "square_transactions", "format": "csv", "load_strategy": "append"},
    {"name": "recharge_subscriptions", "format": "json", "load_strategy": "snapshot"},
    {"name": "zendesk_tickets", "format": "csv", "load_strategy": "append", "required": False},
    {"name": "shipstation_shipments", "format": "csv", "load_strategy": "append"},
]
