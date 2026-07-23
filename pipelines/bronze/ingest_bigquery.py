# pipelines/bronze/ingest_bigquery.py
import sys
from pathlib import Path
from google.cloud import bigquery
from google.auth import impersonated_credentials
import google.auth

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import RAW_DIR, SOURCES
from extractors import EXTRACTORS
from ingest import resolve_file, stamp_lineage   # reuse, don't duplicate
from logging_config import get_logger

logger = get_logger("bronze_bigquery")

PROJECT_ID = "brewline-coffee-co"
DATASET = "bronze"
IMPERSONATED_SA = f"brewline-bronze-ingest@{PROJECT_ID}.iam.gserviceaccount.com"

def get_bigquery_client() -> bigquery.Client:
    source_credentials, _ = google.auth.default()
    target_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=IMPERSONATED_SA,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=PROJECT_ID, credentials=target_credentials)

def run():
    client = get_bigquery_client()

    for source in SOURCES:
        name = source["name"]
        extractor = EXTRACTORS[source["format"]]

        file_path = resolve_file(source)
        df = extractor(file_path)
        df = stamp_lineage(df, source_name=name, file_path=file_path)

        table_id = f"{PROJECT_ID}.{DATASET}.{name}"
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")

        load_job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        load_job.result()  # blocks until the load finishes, raises on failure

        table = client.get_table(table_id)
        logger.info(f"bronze.{name} loaded to BigQuery: {table.num_rows} rows")

    logger.info("BigQuery bronze ingestion complete.")

if __name__ == "__main__":
    run()