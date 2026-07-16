CREATE OR REPLACE TABLE silver.stg_subscriptions AS
SELECT
    subscription_id,
    customer_email AS customer_key,
    timezone('UTC', CAST(created_at AS TIMESTAMPTZ)) AS subscription_created_at,
    timezone('UTC', CAST(cancelled_at AS TIMESTAMPTZ)) AS cancelled_at,
    frequency_days,
    CASE
        WHEN status = 'active' THEN 'is_active'
        WHEN status = 'paused' THEN 'is_paused'
        WHEN status = 'cancelled' AND cancellation_reason = 'customer_cancelled' THEN 'is_voluntarily_cancelled'
        WHEN status = 'cancelled' AND cancellation_reason = 'payment_failed_max_retries' THEN 'is_payment_failure_cancelled'
        ELSE 'unknown_status'
    END AS customer_status
FROM bronze.recharge_subscriptions
--tested manually inside the duckdb notebooks, the result is validated and match the requirements