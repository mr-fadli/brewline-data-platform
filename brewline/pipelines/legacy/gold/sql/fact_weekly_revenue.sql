CREATE OR REPLACE TABLE gold.fact_weekly_revenue AS
SELECT 
    date_trunc('week', (order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York')::DATE AS week_start_date,
    channel,
    ROUND(SUM(amount_usd), 2) AS total_revenue
FROM silver.stg_orders
GROUP BY week_start_date, channel
ORDER BY week_start_date DESC, channel;
--manually tested inisde the duckdb notebooks and the data is validated and approved