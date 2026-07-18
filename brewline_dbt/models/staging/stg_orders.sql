WITH 
square_aggregated AS (
    -- collapse Square's line-item rows into one row per transaction
    SELECT
        transaction_id,
        location_id,
        COALESCE(customer_phone, location_id || '_' || CAST(DATE(created_at_local) AS VARCHAR)) AS customer_key,
        created_at_local AS order_ts_local,
        SUM(CAST(qty AS INTEGER) * CAST(unit_price AS DOUBLE)
            - CAST(discount AS DOUBLE)) AS amount_original
    FROM {{ source('bronze', 'square_transactions') }}
    GROUP BY transaction_id, location_id, customer_phone, created_at_local
),

square_shaped AS (
    -- reshape into the same columns every source will end up with
    SELECT
        s.transaction_id AS order_id,
        s.customer_key,
        'retail' AS channel,
        'USD' AS currency,
        s.amount_original,
        timezone(tz.timezone_name, CAST(s.order_ts_local AS TIMESTAMP)) AT TIME ZONE 'UTC' AS order_ts_raw
    FROM square_aggregated s
    JOIN {{ ref('store_timezones') }} tz
    ON s.location_id = tz.location_id
),

shopify_shaped AS (
    SELECT
        order_id,
        customer_email AS customer_key,
        CASE WHEN source_name = 'recharge' THEN 'subscription' ELSE 'online_oneoff' END AS channel,
        currency,
        CAST(total_price AS DOUBLE) AS amount_original,
        timezone('UTC', CAST(created_at AS TIMESTAMPTZ)) AS order_ts_raw
    FROM {{ source('bronze', 'shopify_orders') }}
    WHERE cancelled_at IS NULL
),

combined AS (
    -- one unified shape, both sources stacked into the same table
    SELECT * FROM square_shaped
    UNION ALL
    SELECT * FROM shopify_shaped
),

converted AS (
    -- apply currency conversion, joining against the exchange rate table
    SELECT
        c.order_id,
        c.customer_key,
        c.channel,
        c.currency,
        c.amount_original,
        c.amount_original * COALESCE(r.rate_to_usd, 1.0) AS amount_usd,
        c.order_ts_raw
    FROM combined c
    LEFT JOIN {{ ref('exchange_rates') }} r
        ON c.currency = r.currency
        AND CAST(c.order_ts_raw AS DATE) = r.currency_date
)

SELECT * FROM converted