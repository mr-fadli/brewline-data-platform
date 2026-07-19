-- tests/assert_no_negative_days_since_last_order.sql
SELECT * FROM {{ ref('fact_customer_health') }}
WHERE days_since_last_order < 0