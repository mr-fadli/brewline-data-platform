{{
  config(
    materialized='table'
  )
}}

SELECT
    {{ date_trunc_week(convert_utc_to_local('order_ts_raw', "'" ~ var('reporting_timezone') ~ "'")) }} AS week_start_date,
    channel,
    ROUND(SUM(amount_usd), 2) AS total_revenue
FROM {{ ref('stg_orders') }}
GROUP BY week_start_date, channel
ORDER BY week_start_date DESC, channel