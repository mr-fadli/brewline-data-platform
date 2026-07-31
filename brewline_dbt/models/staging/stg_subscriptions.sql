{{
  config(
    materialized='table',
    cluster_by=['customer_key'] if target.type == 'bigquery' else none
  )
}}

SELECT
    subscription_id,
    customer_email AS customer_key,
    {{ parse_and_convert_to_utc('created_at') }} AS subscription_created_at,
    {{ parse_and_convert_to_utc('cancelled_at') }} AS cancelled_at,
    frequency_days,
    CASE
        WHEN status = 'active' THEN 'is_active'
        WHEN status = 'paused' THEN 'is_paused'
        WHEN status = 'cancelled' AND cancellation_reason = 'customer_cancelled' THEN 'is_voluntarily_cancelled'
        WHEN status = 'cancelled' AND cancellation_reason = 'payment_failed_max_retries' THEN 'is_payment_failure_cancelled'
        ELSE 'unknown_status'
    END AS customer_status
FROM {{ source('bronze', 'recharge_subscriptions') }}