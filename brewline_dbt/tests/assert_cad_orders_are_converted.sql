-- Fails if any CAD order's amount_usd equals its amount_original --
-- that would mean the exchange rate join silently didn't apply.
SELECT *
FROM {{ ref('stg_orders') }}
WHERE currency = 'CAD'
  AND amount_usd = amount_original