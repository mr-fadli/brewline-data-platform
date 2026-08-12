# airflow/dags/brewline_pipeline_bigquery_dag.py
from datetime import datetime
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

HOST_PROJECT_DIR = "D:/Ijal/data_engineer/brewline_coffee_co"
CONTAINER_PROJECT_DIR = "/opt/project"
HOST_GCLOUD_DIR = "C:/Users/cepot/AppData/Roaming/gcloud"          # adjust to your actual Windows path, e.g. C:/Users/you/AppData/Roaming/gcloud

project_mount = Mount(source=HOST_PROJECT_DIR, target=CONTAINER_PROJECT_DIR, type="bind")
gcloud_mount = Mount(source=HOST_GCLOUD_DIR, target="/root/.config/gcloud", type="bind", read_only=True)

GCP_ENV = {
    "GCP_PROJECT_ID": "brewline-coffee-co",
    "GCS_BUCKET_NAME": "brewline-data-lake",
    "BRONZE_INGEST_SA": "brewline-bronze-ingest@brewline-coffee-co.iam.gserviceaccount.com",
    "GOOGLE_APPLICATION_CREDENTIALS": "/root/.config/gcloud/application_default_credentials.json",
}

def docker_task(task_id, image, command, working_dir=CONTAINER_PROJECT_DIR):
    return DockerOperator(
        task_id=task_id,
        image=image,
        command=command,
        working_dir=working_dir,
        mounts=[project_mount, gcloud_mount],
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="success",
        mount_tmp_dir=False,
        environment=GCP_ENV,
    )

with DAG(
    dag_id="brewline_pipeline_bigquery",
    schedule="@daily",
    start_date=datetime(2026, 6, 8),
    catchup=False,
    max_active_runs=1,      # only one day's DAG run in flight at a time
    max_active_tasks=2,     # at most 2 tasks (across all runs) executing at once
    tags=["brewline", "bigquery"],
) as dag:

    bronze_ingest = docker_task(
        "bronze_ingest_bigquery", "brewline-bronze:latest",
        "python brewline/pipelines/bronze/ingest_bigquery.py {{ ds }}",
    )
    dbt_run = docker_task(
        "dbt_run_bigquery", "brewline-dbt:latest",
        [
            "sh",
            "-c",
            "dbt deps && dbt run --target bigquery --profiles-dir ."
        ],
        working_dir=f"{CONTAINER_PROJECT_DIR}/brewline_dbt",
    )
    dbt_test = docker_task(
        "dbt_test_bigquery", "brewline-dbt:latest",
        [
            "sh",
            "-c",
            "dbt deps && dbt test --target bigquery --profiles-dir ."
        ],
        working_dir=f"{CONTAINER_PROJECT_DIR}/brewline_dbt",
    )

    bronze_ingest >> dbt_run >> dbt_test