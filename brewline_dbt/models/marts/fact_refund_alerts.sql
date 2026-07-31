{{
  config(
    materialized='table',
    partition_by={'field': 'day', 'data_type': 'date', 'granularity': 'day'} if target.type == 'bigquery' else none
  )
}}

WITH
order_dates AS (
    SELECT CAST({{ convert_utc_to_local('order_ts_raw', "'" ~ var('reporting_timezone') ~ "'") }} AS DATE) AS d
    FROM {{ ref('stg_orders') }}
),
refund_dates AS (
    SELECT CAST({{ convert_utc_to_local('refund_ts', "'" ~ var('reporting_timezone') ~ "'") }} AS DATE) AS d
    FROM {{ ref('stg_refunds') }}
),
combined_dates AS (
    SELECT d FROM order_dates
    UNION DISTINCT
    SELECT d FROM refund_dates
),
calendar_spine AS (
    {{ generate_date_spine('(SELECT MIN(d) FROM combined_dates)', '(SELECT MAX(d) FROM combined_dates)') }}
),
baseline_rate AS (
    SELECT
        (SELECT COUNT(*) FROM {{ ref('stg_refunds') }}) * 100.0
        / (SELECT COUNT(*) FROM {{ ref('stg_orders') }}) AS baseline_rate
),
daily_orders AS (
    SELECT d AS order_date, COUNT(*) AS total_order
    FROM order_dates
    GROUP BY d
),
daily_refunds AS (
    SELECT d AS refund_date, COUNT(*) AS total_refund
    FROM refund_dates
    GROUP BY d
),
daily_metrics AS (
    SELECT
        c.day,
        COALESCE(o.total_order, 0) AS daily_orders,
        COALESCE(r.total_refund, 0) AS daily_refunds
    FROM calendar_spine c
    LEFT JOIN daily_orders o ON c.day = o.order_date
    LEFT JOIN daily_refunds r ON c.day = r.refund_date
),
rolling_metrics AS (
    SELECT
        d.day,
        d.daily_orders,
        d.daily_refunds,
        SUM(d.daily_orders) OVER (
            ORDER BY d.day
            ROWS BETWEEN {{ var('refund_rolling_window_days') - 1 }} PRECEDING AND CURRENT ROW
        ) AS orders_rolling,
        SUM(d.daily_refunds) OVER (
            ORDER BY d.day
            ROWS BETWEEN {{ var('refund_rolling_window_days') - 1 }} PRECEDING AND CURRENT ROW
        ) AS refunds_rolling
    FROM daily_metrics d
),
refund_rates AS (
    SELECT
        r.day,
        r.daily_orders,
        r.daily_refunds,
        r.orders_rolling,
        r.refunds_rolling,
        ROUND(r.refunds_rolling * 100.0 / NULLIF(r.orders_rolling, 0), 2) AS refund_rate_pct
    FROM rolling_metrics r
),
final AS (
    SELECT
        r.day,
        r.daily_orders,
        r.daily_refunds,
        r.orders_rolling,
        r.refunds_rolling,
        r.refund_rate_pct,
        b.baseline_rate,
        CASE
            WHEN r.refund_rate_pct > b.baseline_rate * {{ var('refund_alert_multiplier') }} THEN 'alert'
            ELSE 'normal'
        END AS alert_system
    FROM refund_rates r
    CROSS JOIN baseline_rate b
)
SELECT * FROM final