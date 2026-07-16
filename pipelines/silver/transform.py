import sys
from pathlib import Path

# Add the project root (two levels up from this file) to Python's import search path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from db import get_connection
from config import REFERENCE_DIR

SILVER_SQL_DIR = Path(__file__).parent / "sql"
EXCHANGE_RATES_CSV = REFERENCE_DIR / "exchange_rates.csv"
STORE_TIMEZONE_CSV = REFERENCE_DIR / "store_timezones.csv"

SQL_FILES_IN_ORDER = [
    "stg_customers.sql",
    "stg_orders.sql",
    "stg_subscriptions.sql",
    "stg_refunds.sql",
]

def load_reference_tables(con):
    con.execute(f"""
        CREATE OR REPLACE TABLE silver.stg_exchange_rates AS
        SELECT * FROM read_csv('{EXCHANGE_RATES_CSV.as_posix()}')
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE silver.stg_store_timezones AS
        SELECT * FROM read_csv('{STORE_TIMEZONE_CSV.as_posix()}')
    """)
    print("[OK] reference tables loaded: stg_exchange_rates, stg_store_timezones")

def run():
    con = get_connection()
    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    con.execute("SET TimeZone='UTC'")

    load_reference_tables(con)

    for filename in SQL_FILES_IN_ORDER:
        sql_text = (SILVER_SQL_DIR / filename).read_text()
        table_name = filename.removesuffix(".sql")
        try:
            con.execute(sql_text)
            row_count = con.execute(f"SELECT COUNT(*) FROM silver.{table_name}").fetchone()[0]
            print(f"[OK]   silver.{table_name:<20} {row_count:>5} rows")
        except Exception as e:
            print(f"[FAIL] {filename}: {e}")
            raise

    con.close()
    print("\nSilver transformation complete.")

if __name__ == "__main__":
    run()