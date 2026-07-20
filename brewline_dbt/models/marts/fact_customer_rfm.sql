-- models/marts/fact_customer_rfm.sql
WITH
reference_orders AS (
  SELECT 
    s.customer_key, r.customer_type,
    ROUND(SUM(s.amount_usd), 2) AS total_spend,
    MAX((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York') AS recent_order,
    COUNT(s.customer_key) AS total_order
  FROM {{ ref('stg_orders') }} s
  LEFT JOIN {{ ref('stg_customers') }} r ON s.customer_key = r.customer_key
  WHERE r.customer_type IN ('online', 'loyalty')
  GROUP BY s.customer_key, r.customer_type
),
reference_point AS (SELECT MAX(recent_order) AS reference_date FROM reference_orders),
subscribers AS (
  SELECT all_subs.customer_key,
      CAST(rp.reference_date AS DATE) - CAST(all_subs.first_ever_subscribed AS DATE) AS join_days
  FROM (
      SELECT customer_key,
          MIN(subscription_created_at AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS first_ever_subscribed
      FROM {{ ref('stg_subscriptions') }}
      GROUP BY customer_key
  ) all_subs
  CROSS JOIN reference_point rp
  WHERE all_subs.customer_key IN (SELECT customer_key FROM {{ ref('stg_subscriptions') }} WHERE customer_status = 'is_active')
),
rfm_table AS (
  SELECT s.customer_key,
    NTILE(5) OVER (ORDER BY s.total_spend) AS monetary_score,
    NTILE(5) OVER (ORDER BY s.total_order) AS frequency_score,
    NTILE(5) OVER (ORDER BY s.recent_order) AS recency_score,
    CASE WHEN f.join_days > 90 AND f.join_days < 130 THEN 1
         WHEN f.join_days >= 130 THEN 2 ELSE 0 END AS tenure_bonus,
    (monetary_score + frequency_score + recency_score +
     CASE WHEN f.join_days > 90 AND f.join_days < 130 THEN 1
          WHEN f.join_days >= 130 THEN 2 ELSE 0 END) AS total_score
  FROM reference_orders s
  LEFT JOIN subscribers f ON s.customer_key = f.customer_key
)
SELECT * FROM rfm_table ORDER BY total_score DESC