-- models/marts/fact_refund_alerts.sql
WITH
calender_spine AS (
  SELECT unnest(generate_series(
      (SELECT MIN(d) FROM (
          SELECT CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM {{ ref('stg_orders') }}
          UNION
          SELECT CAST((refund_ts AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM {{ ref('stg_refunds') }}
      )),
      (SELECT MAX(d) FROM (
          SELECT CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM {{ ref('stg_orders') }}
          UNION
          SELECT CAST((refund_ts AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM {{ ref('stg_refunds') }}
      )),
      INTERVAL 1 DAY
  )) AS day
),
baseline_rate AS (
  SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {{ ref('stg_orders') }}) AS baseline_rate
  FROM {{ ref('stg_refunds') }}
),
daily_orders AS (
  SELECT DISTINCT
    CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS order_date,
    COUNT(*) AS total_order
  FROM {{ ref('stg_orders') }}
  GROUP BY order_date, order_ts_raw
),
daily_refunds AS (
  SELECT 
    CAST((refund_ts AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS refund_date,
    COUNT(*) AS total_refund
  FROM {{ ref('stg_refunds') }}
  GROUP BY refund_date
),
daily_metrics AS (
  SELECT 
    c.day,
    COALESCE(o.total_order, 0) AS daily_orders,
    COALESCE(r.total_refund, 0) AS daily_refunds
  FROM calender_spine c
  LEFT JOIN daily_orders o ON c.day = o.order_date
  LEFT JOIN daily_refunds r ON c.day = r.refund_date
)
SELECT
  d.day, d.daily_orders, d.daily_refunds,
  SUM(d.daily_orders) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS orders_7d,
  SUM(d.daily_refunds) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS refunds_7d,
  ROUND(refunds_7d * 100.0 / NULLIF(orders_7d,0), 2) AS refund_rate_pct,
  CASE WHEN refund_rate_pct > r.baseline_rate * 2 THEN 'alert' ELSE 'normal' END AS alert_system
FROM daily_metrics d
CROSS JOIN baseline_rate r
ORDER BY day