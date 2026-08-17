# GCP Setup Guide

Step-by-step commands to replicate this project's GCP infrastructure from scratch. See `docs/adr/010_service_account_design.md` for the reasoning behind this design.

## 1. Create the two service accounts
```bash
gcloud iam service-accounts create brewline-bronze-ingest \
    --display-name="Brewline Bronze Ingestion"
gcloud iam service-accounts create brewline-dbt-transform \
    --display-name="Brewline dbt Transform"
```

## 2. Create the BigQuery datasets
```bash
bq mk --dataset YOUR_PROJECT_ID:bronze
bq mk --dataset YOUR_PROJECT_ID:silver
bq mk --dataset YOUR_PROJECT_ID:gold
```

## 3. Grant dataset-level access
Via Console: BigQuery → dataset → Sharing → Permissions → Add principal.
- `bronze` dataset: `BigQuery Data Editor` → `brewline-bronze-ingest`
- `bronze` dataset: `BigQuery Data Viewer` → `brewline-dbt-transform`
- `silver`/`gold` datasets: `BigQuery Data Editor` → `brewline-dbt-transform`

## 4. Grant project-level job execution permission
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:brewline-bronze-ingest@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:brewline-dbt-transform@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"
```

## 5. Grant yourself impersonation rights
```bash
gcloud iam service-accounts add-iam-policy-binding \
    brewline-bronze-ingest@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --member="user:you@example.com" --role="roles/iam.serviceAccountTokenCreator"
gcloud iam service-accounts add-iam-policy-binding \
    brewline-dbt-transform@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --member="user:you@example.com" --role="roles/iam.serviceAccountTokenCreator"
```

## 6. Create the GCS bucket
```bash
gcloud storage buckets create gs://YOUR_BUCKET_NAME --location=us-central1
```
Grant `brewline-bronze-ingest` the `Storage Object Admin` role on this bucket.

## 7. Authenticate locally
```bash
gcloud auth application-default login
```

## 8. Configure `.env`
Copy `.env.example` → `.env`, fill in your project ID, bucket name, and
service account emails.