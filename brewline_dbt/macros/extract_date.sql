-- macros/extract_date.sql
{% macro extract_date(ts_string) %}
  {{ return(adapter.dispatch('extract_date')(ts_string)) }}
{% endmacro %}

{% macro duckdb__extract_date(ts_string) %}
  DATE({{ ts_string }})
{% endmacro %}

{% macro bigquery__extract_date(ts_string) %}
  DATE(CAST({{ ts_string }} AS DATETIME))
{% endmacro %}