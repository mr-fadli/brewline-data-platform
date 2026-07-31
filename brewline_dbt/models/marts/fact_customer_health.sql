{{
  config(
    materialized='table'
  )
}}

WITH
customers AS (
    SELECT
        customer_key,
        MAX({{ convert_utc_to_local('order_ts_raw', "'" ~ var('reporting_timezone') ~ "'") }}) AS last_order_date
    FROM {{ ref('stg_orders') }}
    GROUP BY customer_key
),
reference_point AS (
    SELECT MAX(last_order_date) AS reference_date FROM customers
),
days_calc AS (
    SELECT
        s.customer_key,
        r.customer_type,
        s.last_order_date,
        {{ dbt.datediff('CAST(s.last_order_date AS DATE)', 'CAST(rp.reference_date AS DATE)', 'day') }} AS days_since_last_order
    FROM customers s
    CROSS JOIN reference_point rp
    LEFT JOIN {{ ref('stg_customers') }} r ON s.customer_key = r.customer_key
    WHERE r.customer_type IN ('loyalty', 'online')
),
customer_health_reshaped AS (
    SELECT
        customer_key,
        customer_type,
        last_order_date,
        days_since_last_order,
        CASE
            WHEN days_since_last_order >= {{ var('customer_churn_days_threshold') }} THEN 'churned'
            WHEN days_since_last_order >= {{ var('customer_at_risk_days_threshold') }} THEN 'at_risk'
            ELSE 'active'
        END AS customer_health
    FROM days_calc
)
SELECT * FROM customer_health_reshaped