# ADR-017 : Environment Secrets split across .env files

## Status
Accepted

## Context
GCP project config needed by both host-run scripts and Airflow's containers; Docker-specific paths (host mount sources) only meaningful to the containerized path.

## Decision
shared values in root `.env` (read via `load_dotenv()` for host scripts, or via `docker compose --env-file` merge for containers); Docker-only values in `airflow/.env`.

## Consequences
Compose must always be invoked via the two-env-file form — wrapped in `compose.ps1`/`compose.sh` specifically so this isn't left to memory.