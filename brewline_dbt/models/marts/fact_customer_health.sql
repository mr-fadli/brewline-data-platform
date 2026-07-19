-- models/marts/fact_customer_health.sql
WITH
customers AS (
  SELECT DISTINCT customer_key,
      MAX((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York') AS last_order_date
  FROM {{ ref('stg_orders') }}
  GROUP BY customer_key
),
reference_point AS (
  SELECT MAX(last_order_date) AS reference_date FROM customers
),
customer_health_reshaped AS (
  SELECT 
    s.customer_key,
    r.customer_type,
    s.last_order_date,
    CAST(rp.reference_date AS DATE) - CAST(s.last_order_date AS DATE) AS days_since_last_order,
    CASE
      WHEN days_since_last_order >= 60 THEN 'churned'
      WHEN days_since_last_order >= 45 THEN 'at_risk'
      ELSE 'active'
    END AS customer_health
  FROM customers s
  CROSS JOIN reference_point rp
  LEFT JOIN {{ ref('stg_customers') }} r ON s.customer_key = r.customer_key
  WHERE customer_type IN ('loyalty', 'online')
)
SELECT * FROM customer_health_reshaped