-- tests/assert_reactivated_customers_not_churned.sql
-- Fails if any customer with BOTH a payment-failure-cancelled row AND a
-- later active row still shows up as churned -- this is the exact edge
-- case (reactivation within 48h) the whole churn design was built around.
WITH reactivated AS (
    SELECT customer_key
    FROM {{ ref('stg_subscriptions') }}
    GROUP BY customer_key
    HAVING COUNT(*) > 1
       AND SUM(CASE WHEN customer_status = 'is_payment_failure_cancelled' THEN 1 ELSE 0 END) > 0
       AND SUM(CASE WHEN customer_status = 'is_active' THEN 1 ELSE 0 END) > 0
)
SELECT f.customer_key
FROM {{ ref('fact_subscription_churn') }} f
JOIN reactivated r ON f.customer_key = r.customer_key
WHERE f.churn_status != 'not_churned'