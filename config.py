"""Central configuration for the Brewline bronze pipeline."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
BRONZE_DIR = PROJECT_ROOT / "pipelines" / "bronze"
RAW_DIR = BRONZE_DIR / "raw"
BRONZE_PARQUET_DIR = BRONZE_DIR / "parquet"
DB_PATH = PROJECT_ROOT / "brewline.duckdb"

BRONZE_PARQUET_DIR.mkdir(parents=True, exist_ok=True)

# Each source only declares what's actually independent (name + format).
# file_pattern and table_name are conventions derived from name, not duplicated by hand.
SOURCES = [
    {"name": "shopify_orders", "format": "json"},
    {"name": "square_transactions", "format": "csv"},
    {"name": "recharge_subscriptions", "format": "json"},
    {"name": "zendesk_tickets", "format": "csv"},
    {"name": "shipstation_shipments", "format": "csv"},
]
