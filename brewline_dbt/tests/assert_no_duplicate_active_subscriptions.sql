-- tests/assert_no_duplicate_active_subscriptions.sql
-- Fails if any customer has more than one row marked is_active at once --
-- would break the ROW_NUMBER "pick current status" logic downstream.
SELECT customer_key, COUNT(*) AS active_count
FROM {{ ref('stg_subscriptions') }}
WHERE customer_status = 'is_active'
GROUP BY customer_key
HAVING COUNT(*) > 1