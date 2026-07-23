-- For a naive timestamp + a separate timezone name (e.g. Square's local time + store's zone)
{% macro convert_naive_to_utc(naive_ts_column, zone_column) %}
  {{ return(adapter.dispatch('convert_naive_to_utc')(naive_ts_column, zone_column)) }}
{% endmacro %}

{% macro duckdb__convert_naive_to_utc(naive_ts_column, zone_column) %}
  timezone({{ zone_column }}, CAST({{ naive_ts_column }} AS TIMESTAMP)) AT TIME ZONE 'UTC'
{% endmacro %}

{% macro bigquery__convert_naive_to_utc(naive_ts_column, zone_column) %}
  -- Convert a naive datetime string and text timezone cleanly into a UTC Datetime
  DATETIME(
    TIMESTAMP(CAST({{ naive_ts_column }} AS DATETIME), {{ zone_column }}), 
    'UTC'
  )
{% endmacro %}