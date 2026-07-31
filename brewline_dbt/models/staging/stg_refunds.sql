{{
  config(
    materialized='incremental' if target.type == 'bigquery' else 'table',
    unique_key='refund_id',
    partition_by={'field': 'refund_ts', 'data_type': 'datetime', 'granularity': 'day'} if target.type == 'bigquery' else none,
    incremental_strategy='merge'
  )
}}

WITH 
reference_tbl AS (
  {% if target.type == 'bigquery' %}
  SELECT 
    o.order_id, 
    o.customer_email, 
    o.currency, 
    o.created_at, 
    o._run_date AS order_run_date, 
    refund
  FROM {{source('bronze', 'shopify_orders')}} o, UNNEST(o.refunds) AS refund
  {% if is_incremental() %}
  WHERE o._run_date > (SELECT MAX(order_run_date) FROM {{ this }})
  {% endif %}

  {% else %}
  SELECT order_id, customer_email, currency, created_at, _run_date AS order_run_date, UNNEST(refunds) AS refund
  FROM {{source('bronze', 'shopify_orders')}}
  WHERE len(refunds) > 0
  {% endif %}
),
shipment_tbl AS (
SELECT 
    shopify_order_id AS order_id,
    status,
    {{ parse_and_convert_to_utc('last_scan_at') }} AS delivered_at
  FROM {{source('bronze', 'shipstation_shipments')}}
  WHERE status = 'delivered'
),
refunds_shaped AS (
SELECT 
  s.refund.refund_id,
  s.order_id,
  s.customer_email AS customer_key,
  s.refund.amount AS amount_original,
  s.currency,
  s.created_at,
  s.order_run_date,
  s.refund.reason,
  r.delivered_at,
  {{ parse_and_convert_to_utc('s.refund.created_at') }} AS refund_ts,
  {{ dbt.datediff('r.delivered_at', parse_and_convert_to_utc('s.refund.created_at'), 'day')}} AS days_since_delivery
  
  
FROM reference_tbl s
LEFT JOIN shipment_tbl r
  ON s.order_id = r.order_id
)
  SELECT
    s.refund_id,
    s.order_id,
    s.customer_key,
    s.amount_original,
    s.currency,
    s.amount_original * COALESCE(r.rate_to_usd, 1.0) AS amount_usd,
    s.reason,
    s.delivered_at,
    s.refund_ts,
    s.days_since_delivery,
  CASE
    WHEN s.delivered_at IS NULL THEN NULL  -- can't evaluate policy window without a known delivery date
    WHEN s.days_since_delivery < 0 THEN TRUE  -- refunded before/at delivery — trivially within any window
    WHEN s.days_since_delivery <= 30 THEN TRUE
    ELSE FALSE
  END AS within_policy_window,
  CASE
    WHEN s.delivered_at IS NULL THEN NULL   -- genuinely unknown
    WHEN s.days_since_delivery < 0 THEN TRUE
    ELSE FALSE                             -- known, and definitively not early
  END AS refunded_before_delivery_confirmed
  FROM refunds_shaped s
  LEFT JOIN {{ref('exchange_rates')}} r
    ON s.currency = r.currency
    AND {{ extract_date_from_timestamp('s.created_at') }} = r.currency_date
