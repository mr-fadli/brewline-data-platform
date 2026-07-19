SELECT 
    date_trunc('week', (order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York')::DATE AS week_start_date,
    channel,
    ROUND(SUM(amount_usd), 2) AS total_revenue
FROM {{ref('stg_orders')}}
GROUP BY week_start_date, channel
ORDER BY week_start_date DESC, channel