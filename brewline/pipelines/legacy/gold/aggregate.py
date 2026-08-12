"""
Gold aggregation orchestrator.

Each gold table answers one specific question from the original business
requirement, built on top of verified silver tables. Unlike silver, gold
tables have no dependencies on each other -- each reads directly from
silver, so order between them doesn't matter (only that silver runs first,
which is a separate pipeline stage, not this script's concern).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[4]))

from brewline.db import get_connection
from brewline.logging_config import get_logger
logger = get_logger("gold")

GOLD_SQL_DIR = Path(__file__).parent / "sql"

# Order doesn't matter for correctness (no gold table depends on another),
# but listing explicitly -- rather than globbing -- keeps this consistent
# with bronze/silver and makes it obvious at a glance what gold contains.
SQL_FILES = [
    "fact_weekly_revenue.sql",
    "fact_subscription_churn.sql",
    "fact_customer_health.sql",
    "fact_refund_alerts.sql",
    "fact_customer_rfm.sql",
]

def run():
    con = get_connection()
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    con.execute("SET TimeZone='UTC'")

    for filename in SQL_FILES:
        sql_text = (GOLD_SQL_DIR / filename).read_text()
        table_name = filename.removesuffix(".sql")
        try:
            con.execute(sql_text)
            row_count = con.execute(f"SELECT COUNT(*) FROM gold.{table_name}").fetchone()[0]
            logger.info(f"[OK]   gold.{table_name:<28} {row_count:>5} rows")
        except Exception as e:
            logger.error(f"[FAIL] {filename}: {e}")
            raise

    con.close()
    logger.info("Gold aggregation complete.")

if __name__ == "__main__":
    run()