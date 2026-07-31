{% macro date_trunc_week(date_or_ts_column) %}
  {{ return(adapter.dispatch('date_trunc_week')(date_or_ts_column)) }}
{% endmacro %}

{% macro duckdb__date_trunc_week(date_or_ts_column) %}
  CAST(date_trunc('week', {{ date_or_ts_column }}) AS DATE)
{% endmacro %}

{% macro bigquery__date_trunc_week(date_or_ts_column) %}
  DATE_TRUNC(DATE({{ date_or_ts_column }}), WEEK(MONDAY))
{% endmacro %}