# v1.0.0 
- run locally by hand
- Programming Language using Python/SQL
- database will be using DuckDB
- pipeline will process into Bronze - Silver - Gold
- bronze data will be stored using parquet and added a minimum data lineage for traceability
- Data Provided will be in CSV and JSON
- silver and gold will be processed inside the database via SQL

# v2.0.0
- silver and gold will be run through dbt
- add orchestrator airflow as the scheduler
- enrich the observability layer.
- database will be swapped to free tier cloud