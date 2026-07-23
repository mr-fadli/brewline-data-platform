-- For an already-offset-aware timestamp string (e.g. Shopify's created_at)
{% macro parse_and_convert_to_utc(ts_column) %}
  {{ return(adapter.dispatch('parse_and_convert_to_utc')(ts_column)) }}
{% endmacro %}

{% macro duckdb__parse_and_convert_to_utc(ts_column) %}
  timezone('UTC', CAST({{ ts_column }} AS TIMESTAMPTZ))
{% endmacro %}

{% macro bigquery__parse_and_convert_to_utc(ts_column) %}
  DATETIME(
    TIMESTAMP({{ ts_column }}),  -- or PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', {{ ts_column }}) if format is nonstandard
    'UTC'
  )
{% endmacro %}