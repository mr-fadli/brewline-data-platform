SELECT *
FROM {{ref('stg_refunds')}}
WHERE currency = 'CAD' AND amount_usd = amount_original