"""DuckDB connection management."""
import duckdb
from config import DB_PATH


def get_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("SET TimeZone='UTC'")
    return con
