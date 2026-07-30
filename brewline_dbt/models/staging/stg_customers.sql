{{
  config(
    materialized='incremental' if target.type == 'bigquery' else 'table',
    unique_key='customer_key',
    incremental_strategy='merge'
  )
}}

WITH shopify_email AS (
    SELECT customer_email AS customer_key, 'online' AS customer_type, MIN(_run_date) AS first_seen_run_date
    FROM {{ source('bronze', 'shopify_orders') }}
    {% if is_incremental() %}
    WHERE _run_date > (SELECT MAX(first_seen_run_date) FROM {{ this }})
    {% endif %}
    GROUP BY customer_email
),
square_loyalty AS (
    SELECT customer_phone AS customer_key, 'loyalty' AS customer_type, MIN(_run_date) AS first_seen_run_date
    FROM {{ source('bronze', 'square_transactions') }}
    WHERE customer_phone IS NOT NULL
    {% if is_incremental() %}
    AND _run_date > (SELECT MAX(first_seen_run_date) FROM {{ this }})
    {% endif %}
    GROUP BY customer_phone
),
square_walk_in AS (
    SELECT
        location_id || '_' || CAST({{ extract_date('created_at_local') }} AS {{ dbt.type_string() }}) AS customer_key,
        'walk_in' AS customer_type,
        MIN(_run_date) AS first_seen_run_date
    FROM {{ source('bronze', 'square_transactions') }}
    WHERE customer_phone IS NULL
    {% if is_incremental() %}
    AND _run_date > (SELECT MAX(first_seen_run_date) FROM {{ this }})
    {% endif %}
    GROUP BY 1
),
combined AS (
    SELECT * FROM shopify_email
    UNION ALL SELECT * FROM square_loyalty
    UNION ALL SELECT * FROM square_walk_in
)
SELECT * FROM combined