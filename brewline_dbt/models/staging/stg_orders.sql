{{
  config(
    materialized='incremental' if target.type == 'bigquery' else 'table',
    unique_key='order_id',
    partition_by={'field': 'order_ts_raw', 'data_type': 'datetime', 'granularity': 'day'} if target.type == 'bigquery' else none,
    cluster_by=['channel'] if target.type == 'bigquery' else none,
    incremental_strategy='merge' if target.type == 'bigquery' else none
  )
}}
-- order_ts_raw is UTC-normalized upstream; 
-- partitioning here reflects UTC calendar days, matching how weekly bucketing is later done in fact_weekly_revenue

WITH 
square_aggregated AS (
    SELECT
        transaction_id,
        location_id,
        COALESCE(customer_phone, location_id || '_' || CAST(DATE(created_at_local) AS {{ dbt.type_string() }})) AS customer_key,
        MIN(created_at_local) AS order_ts_local,
        SUM(CAST(qty AS {{ dbt.type_float() }}) * CAST(unit_price AS {{ dbt.type_float() }}) - CAST(discount AS {{ dbt.type_float() }})) AS amount_original
    FROM {{ source('bronze', 'square_transactions') }}
    GROUP BY transaction_id, location_id, customer_phone, created_at_local
),
square_shaped AS (
    SELECT
        s.transaction_id AS order_id,
        s.customer_key,
        'retail' AS channel,
        'USD' AS currency,
        s.amount_original,
        {{ convert_naive_to_utc('s.order_ts_local', 'tz.timezone_name') }} AS order_ts_raw
    FROM square_aggregated s
    JOIN {{ ref('store_timezones') }} tz ON s.location_id = tz.location_id
),
shopify_shaped AS (
    SELECT
        order_id,
        customer_email AS customer_key,
        CASE WHEN source_name = 'recharge' THEN 'subscription' ELSE 'online_oneoff' END AS channel,
        currency,
        CAST(total_price AS {{ dbt.type_float() }}) AS amount_original,
        {{ parse_and_convert_to_utc('created_at') }} AS order_ts_raw
    FROM {{ source('bronze', 'shopify_orders') }}
    WHERE cancelled_at IS NULL
),
combined AS (
    SELECT * FROM square_shaped
    UNION ALL SELECT * FROM shopify_shaped
),
converted AS (
    SELECT
        c.*,
        c.amount_original * COALESCE(r.rate_to_usd, 1.0) AS amount_usd,
    FROM combined c
    LEFT JOIN {{ ref('exchange_rates') }} r
        ON c.currency = r.currency AND CAST(c.order_ts_raw AS DATE) = r.currency_date
)
SELECT * FROM converted

{% if is_incremental() %}
WHERE order_ts_raw > (SELECT MAX(order_ts_raw) FROM {{ this }})
{% endif %}