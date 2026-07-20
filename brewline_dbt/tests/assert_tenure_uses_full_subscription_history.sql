-- tests/assert_tenure_uses_full_subscription_history.sql
-- Fails if any currently-active subscriber's tenure was computed from
-- only their most recent subscription row instead of their true first-ever
-- signup -- this is the reactivation-tenure bug found during development.
WITH true_first_signup AS (
    SELECT customer_key,
        MIN(subscription_created_at) AS true_first_ever
    FROM {{ ref('stg_subscriptions') }}
    GROUP BY customer_key
),
currently_active AS (
    SELECT DISTINCT customer_key FROM {{ ref('stg_subscriptions') }} WHERE customer_status = 'is_active'
)
SELECT rfm.customer_key
FROM {{ ref('fact_customer_rfm') }} rfm
JOIN currently_active ca ON rfm.customer_key = ca.customer_key
JOIN true_first_signup tfs ON rfm.customer_key = tfs.customer_key
WHERE rfm.tenure_bonus = 0
  AND DATE_DIFF('day', CAST(tfs.true_first_ever AS DATE),
      (SELECT MAX(CAST((order_ts_raw AT TIME ZONE 'UTC') AT TIME ZONE 'America/New_York' AS DATE)) FROM {{ ref('stg_orders') }})) >= 90