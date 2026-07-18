WITH 
reference_tbl AS (
  SELECT order_id, customer_email, currency, created_at, UNNEST(refunds) AS refund,
  FROM {{source('bronze', 'shopify_orders')}}
  WHERE len(refunds) > 0),
shipment_tbl AS (
SELECT 
    shopify_order_id AS order_id,
    status,
    timezone('UTC', CAST(last_scan_at AS TIMESTAMPTZ)) AS delivered_at,
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
  s.refund.reason,
  r.delivered_at,
  timezone('UTC', CAST(s.refund.created_at AS TIMESTAMPTZ)) AS refund_ts,
  DATEDIFF('day', r.delivered_at, refund_ts) AS days_since_delivery,
  CASE
    WHEN delivered_at IS NULL THEN NULL  -- can't evaluate policy window without a known delivery date
    WHEN days_since_delivery < 0 THEN TRUE  -- refunded before/at delivery — trivially within any window
    WHEN days_since_delivery <= 30 THEN TRUE
    ELSE FALSE
  END AS within_policy_window,
  CASE
    WHEN delivered_at IS NULL THEN NULL   -- genuinely unknown
    WHEN days_since_delivery < 0 THEN TRUE
    ELSE FALSE                             -- known, and definitively not early
  END AS refunded_before_delivery_confirmed
FROM reference_tbl s
LEFT JOIN shipment_tbl r
  ON s.order_id = r.order_id
),
refunds AS (
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
    s.within_policy_window,
    s.refunded_before_delivery_confirmed
  FROM refunds_shaped s
  LEFT JOIN {{ref('exchange_rates')}} r
    ON s.currency = r.currency
    AND CAST(s.created_at AS DATE) = r.currency_date
)

SELECT * FROM refunds