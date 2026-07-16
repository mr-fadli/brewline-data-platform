CREATE OR REPLACE TABLE silver.stg_store_timezones AS
SELECT * FROM read_csv('reference/store_timezones.csv')
--manually run inside the duckdb notebooks