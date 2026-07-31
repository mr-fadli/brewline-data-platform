{% macro generate_date_spine(start_date, end_date) %}
  {{ return(adapter.dispatch('generate_date_spine')(start_date, end_date)) }}
{% endmacro %}

{% macro duckdb__generate_date_spine(start_date, end_date) %}
  SELECT unnest(generate_series(
    CAST({{ start_date }} AS DATE),
    CAST({{ end_date }} AS DATE),
    INTERVAL 1 DAY
  )) AS day
{% endmacro %}

{% macro bigquery__generate_date_spine(start_date, end_date) %}
  SELECT day
  FROM UNNEST(GENERATE_DATE_ARRAY(
    CAST({{ start_date }} AS DATE),
    CAST({{ end_date }} AS DATE),
    INTERVAL 1 DAY
  )) AS day
{% endmacro %}