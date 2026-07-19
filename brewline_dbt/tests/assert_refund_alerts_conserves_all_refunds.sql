-- tests/assert_refund_alerts_conserves_all_refunds.sql
-- Fails if the spine's daily_refunds don't sum to the true total refund
-- count -- would mean a refund's date fell outside the calendar spine.
SELECT 1 AS mismatch
WHERE (SELECT SUM(daily_refunds) FROM {{ ref('fact_refund_alerts') }})
   != (SELECT COUNT(*) FROM {{ ref('stg_refunds') }})