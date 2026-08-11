from datetime import datetime
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

# REAL HOST PATH -- must be your actual Windows path, forward slashes are fine for Docker Desktop
HOST_PROJECT_DIR = "D:/Ijal/data_engineer/brewline_coffee_co"
CONTAINER_PROJECT_DIR = "/opt/project"

project_mount = Mount(source=HOST_PROJECT_DIR, target=CONTAINER_PROJECT_DIR, type="bind")

def docker_task(task_id, image, command, env=None):
    return DockerOperator(
        task_id=task_id,
        image=image,
        command=command,
        working_dir=f"{CONTAINER_PROJECT_DIR}/brewline_dbt" if "dbt" in image else CONTAINER_PROJECT_DIR,
        mounts=[project_mount],
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove="success",
        mount_tmp_dir=False,
        environment=env or {},
    )

with DAG(
    dag_id="brewline_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 7, 8),
    catchup=False,
    tags=["brewline"],
) as dag:

    bronze_ingest = docker_task(
        "bronze_ingest", "brewline-bronze:latest",
        f"python {CONTAINER_PROJECT_DIR}/pipelines/bronze/ingest.py",
    )
    dbt_env = {"DBT_DUCKDB_PATH": f"{CONTAINER_PROJECT_DIR}/brewline.duckdb"}
    dbt_seed = docker_task("dbt_seed", "brewline-dbt:latest", "dbt seed --profiles-dir .", dbt_env)
    dbt_run  = docker_task("dbt_run",  "brewline-dbt:latest", "dbt run --profiles-dir .",  dbt_env)
    dbt_test = docker_task("dbt_test", "brewline-dbt:latest", "dbt test --profiles-dir .", dbt_env)

    bronze_ingest >> dbt_seed >> dbt_run >> dbt_test