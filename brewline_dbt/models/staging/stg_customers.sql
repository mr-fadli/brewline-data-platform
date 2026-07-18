WITH shopify_email AS (
    SELECT DISTINCT customer_email AS customer_key, 'online' AS customer_type
    FROM {{ source('bronze', 'shopify_orders') }}
),
square_loyalty AS (
    SELECT DISTINCT customer_phone AS customer_key, 'loyalty' AS customer_type
    FROM {{ source('bronze', 'square_transactions') }}
    WHERE customer_phone IS NOT NULL
),
square_walk_in AS (
    SELECT DISTINCT
        location_id || '_' || CAST(DATE(created_at_local) AS VARCHAR) AS customer_key,
        'walk_in' AS customer_type
    FROM {{ source('bronze', 'square_transactions') }}
    WHERE customer_phone IS NULL
),
combined AS (
    SELECT * FROM shopify_email
    UNION ALL SELECT * FROM square_loyalty
    UNION ALL SELECT * FROM square_walk_in
)
SELECT * FROM combined