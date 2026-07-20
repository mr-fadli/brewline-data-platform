-- tests/assert_rfm_total_score_is_sum_of_parts.sql
SELECT *
FROM {{ ref('fact_customer_rfm') }}
WHERE total_score != monetary_score + frequency_score + recency_score + tenure_bonus