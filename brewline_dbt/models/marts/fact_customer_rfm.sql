{{
  config(
    materialized='table'
  )
}}

WITH
reference_orders AS (
    SELECT
        s.customer_key,
        r.customer_type,
        ROUND(SUM(s.amount_usd), 2) AS total_spend,
        MAX({{ convert_utc_to_local('s.order_ts_raw', "'" ~ var('reporting_timezone') ~ "'") }}) AS recent_order,
        COUNT(s.customer_key) AS total_order
    FROM {{ ref('stg_orders') }} s
    LEFT JOIN {{ ref('stg_customers') }} r ON s.customer_key = r.customer_key
    WHERE r.customer_type IN ('online', 'loyalty')
    GROUP BY s.customer_key, r.customer_type
),
reference_point AS (
    SELECT MAX(recent_order) AS reference_date FROM reference_orders
),
subscriber_first_sub AS (
    SELECT
        customer_key,
        MIN({{ convert_utc_to_local('subscription_created_at', "'" ~ var('reporting_timezone') ~ "'") }}) AS first_ever_subscribed
    FROM {{ ref('stg_subscriptions') }}
    GROUP BY customer_key
),
subscribers AS (
    SELECT
        all_subs.customer_key,
        {{ dbt.datediff('CAST(all_subs.first_ever_subscribed AS DATE)', 'CAST(rp.reference_date AS DATE)', 'day') }} AS join_days
    FROM subscriber_first_sub all_subs
    CROSS JOIN reference_point rp
    WHERE all_subs.customer_key IN (
        SELECT customer_key FROM {{ ref('stg_subscriptions') }} WHERE customer_status = 'is_active'
    )
),
rfm_scores AS (
    SELECT
        s.customer_key,
        NTILE(5) OVER (ORDER BY s.total_spend) AS monetary_score,
        NTILE(5) OVER (ORDER BY s.total_order) AS frequency_score,
        NTILE(5) OVER (ORDER BY s.recent_order) AS recency_score,
        CASE
            WHEN f.join_days > {{ var('subscriber_tenure_bonus_days_lower') }}
                 AND f.join_days < {{ var('subscriber_tenure_bonus_days_upper') }} THEN 1
            WHEN f.join_days >= {{ var('subscriber_tenure_bonus_days_upper') }} THEN 2
            ELSE 0
        END AS tenure_bonus
    FROM reference_orders s
    LEFT JOIN subscribers f ON s.customer_key = f.customer_key
),
rfm_table AS (
    SELECT
        customer_key,
        monetary_score,
        frequency_score,
        recency_score,
        tenure_bonus,
        (monetary_score + frequency_score + recency_score + tenure_bonus) AS total_score
    FROM rfm_scores
)
SELECT * FROM rfm_table ORDER BY total_score DESC