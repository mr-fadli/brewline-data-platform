{% macro extract_date_from_timestamp(ts_column) %}
  {{ return(adapter.dispatch('extract_date_from_timestamp')(ts_column)) }}
{% endmacro %}

{% macro duckdb__extract_date_from_timestamp(ts_column) %}
  CAST((CAST({{ ts_column }} AS TIMESTAMPTZ) AT TIME ZONE 'UTC') AS DATE)
{% endmacro %}

{% macro bigquery__extract_date_from_timestamp(ts_column) %}
  DATE(TIMESTAMP({{ ts_column }}))
{% endmacro %}