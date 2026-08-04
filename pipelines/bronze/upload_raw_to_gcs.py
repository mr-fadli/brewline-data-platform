"""
Simulates external systems delivering files to the GCS landing zone.
In production, this step is NOT part of the pipeline -- files arrive here
from Shopify's own exports, Square's daily batch, etc. This script exists
only to seed a realistic GCS layout from our synthetic generator's output
for local development and testing against the "production" GCS path.
"""
import sys
from pathlib import Path
from datetime import datetime
from google.cloud import storage
from google.auth import impersonated_credentials
import google.auth
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config import RAW_DIR, SOURCES
from logging_config import get_logger

logger = get_logger("gcs_upload")

BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
PROJECT_ID = os.environ["GCP_PROJECT_ID"]
IMPERSONATED_SA = os.environ["BRONZE_INGEST_SA"]

#getting the client credentials to run in GCS
def get_gcs_client() -> storage.Client:
    source_credentials, _ = google.auth.default()
    target_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=IMPERSONATED_SA,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return storage.Client(project=PROJECT_ID, credentials=target_credentials)

#getting the path blob for partitioning in GCS
def raw_gcs_path(source_name: str, file_date: datetime, filename: str) -> str:
    return (
        f"raw/source_name={source_name}/"
        f"year={file_date.year:04d}/month={file_date.month:02d}/day={file_date.day:02d}/"
        f"{filename}"
    )

def run():
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)

    for source in SOURCES:
        name = source["name"]
        for local_file in sorted(RAW_DIR.glob(f"{name}_*.{source['format']}")):
            date_str = local_file.stem.replace(f"{name}_", "")
            file_date = datetime.fromisoformat(date_str)

            blob_path = raw_gcs_path(name, file_date, local_file.name)
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(local_file))
            logger.info(f"uploaded {local_file.name} -> gs://{BUCKET_NAME}/{blob_path}")

    logger.info("GCS raw zone seeded.")

if __name__ == "__main__":
    run()