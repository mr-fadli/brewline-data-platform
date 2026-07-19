WITH
table_partition AS (
  SELECT *
  FROM (
      SELECT *,
          ROW_NUMBER() OVER (PARTITION BY customer_key ORDER BY subscription_created_at DESC) AS rn
      FROM {{ ref('stg_subscriptions')}}
  )
  WHERE rn = 1 
)
SELECT 
  subscription_id, customer_key,
  CASE
    WHEN customer_status = 'is_voluntarily_cancelled' THEN 'is_voluntarily_churned'
    WHEN customer_status = 'is_payment_failure_cancelled' THEN 'is_involuntarily_churned'
    WHEN customer_status IN ('is_active', 'is_paused') THEN 'not_churned'
    ELSE NULL
  END AS churn_status
FROM table_partition