{% macro convert_utc_to_local(utc_ts_column, target_tz) %}
  {{ return(adapter.dispatch('convert_utc_to_local')(utc_ts_column, target_tz)) }}
{% endmacro %}

{% macro duckdb__convert_utc_to_local(utc_ts_column, target_tz) %}
  (({{ utc_ts_column }} AT TIME ZONE 'UTC') AT TIME ZONE {{ target_tz }})
{% endmacro %}

{% macro bigquery__convert_utc_to_local(utc_ts_column, target_tz) %}
  DATETIME(TIMESTAMP({{ utc_ts_column }}, 'UTC'), {{ target_tz }})
{% endmacro %}