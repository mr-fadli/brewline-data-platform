-- gold.fact_refund_alerts
CREATE OR REPLACE TABLE gold.fact_refund_alerts AS
WITH
calender_spine AS (
-- calender spine
  SELECT unnest(generate_series(
      (SELECT MIN(d) FROM (
          SELECT CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM silver.stg_orders
          UNION
          SELECT CAST((refund_ts AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM silver.stg_refunds
      )),
      (SELECT MAX(d) FROM (
          SELECT CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM silver.stg_orders
          UNION
          SELECT CAST((refund_ts AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS d FROM silver.stg_refunds
      )),
      INTERVAL 1 DAY
  )) AS day
),
baseline_rate AS (
-- baseline percentage for the alert system
  SELECT
      COUNT(*) * 100.0 /
      (
          SELECT COUNT(*)
          FROM silver.stg_orders
      ) AS baseline_rate
  
  FROM silver.stg_refunds
),
daily_orders AS (
-- the amount of orders daily
  SELECT DISTINCT
    CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS order_date,
    COUNT(*) AS total_order
  FROM silver.stg_orders
  GROUP BY order_date
),
daily_refunds AS (
-- the amount of refunds daily
  SELECT 
    CAST((refund_ts AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE) AS refund_date,
    COUNT(*) AS total_refund
  FROM silver.stg_refunds
  GROUP BY refund_date
),
daily_metrics AS (
-- base daily metrics
  SELECT 
    c.day,
    COALESCE (o.total_order, 0) AS daily_orders,
    COALESCE (r.total_refund, 0) AS daily_refunds
  FROM calender_spine c
  LEFT JOIN daily_orders o
    ON c.day = o.order_date
  
  LEFT JOIN daily_refunds r
    ON c.day = r.refund_date
)
SELECT
  d.day,
  d.daily_orders,
  d.daily_refunds,
  SUM(d.daily_orders)
    OVER (
        ORDER BY day
        ROWS BETWEEN 6 PRECEDING
        AND CURRENT ROW
    ) AS orders_7d,
    
    SUM(d.daily_refunds)
    OVER (
        ORDER BY day
        ROWS BETWEEN 6 PRECEDING
        AND CURRENT ROW
    ) AS refunds_7d,
    ROUND(
        refunds_7d * 100.0
        / NULLIF(orders_7d,0),
        2
    ) AS refund_rate_pct,
    CASE 
      WHEN refund_rate_pct > r.baseline_rate * 2 THEN 'alert'
      ELSE 'normal' 
    END AS alert_system

FROM daily_metrics d
CROSS JOIN baseline_rate r;
--tested manually inside duckdb