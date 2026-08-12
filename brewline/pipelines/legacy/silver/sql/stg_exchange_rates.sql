CREATE OR REPLACE TABLE silver.stg_exchange_rates AS
SELECT * FROM read_csv('reference/exchange_rates.csv')
--run manually in the SQL database for now
