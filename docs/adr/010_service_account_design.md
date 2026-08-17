# ADR-010 : Service Account Design

## Status
Accepted

## Context
BigQuery access is required from two independent execution contexts: local developer scripts running directly on a host machine, and containerized Airflow tasks with no interactive session. The GCP project this pipeline targets enforces an org policy disabling service account key creation (`iam.disableServiceAccountKeyCreation`) — an increasingly common default in real organizations, since long-lived static keys have no automatic expiry and are a common source of credential leakage. Any design relying on a downloaded JSON key file is a non-starter under this policy, and would be a weaker security posture even if it were permitted.

Separately, a single shared identity for all pipeline operations violates least-privilege: if one identity can both ingest raw data into bronze and transform/publish gold tables, a credential compromise or a bug in one layer has blast radius across the whole warehouse, not just the layer where it occurred.

## Decision
Two function-scoped service accounts, granted only the permissions their specific job requires:

- **`brewline-bronze-ingest`** — `BigQuery Data Editor` on the `bronze` dataset only. Cannot read or write `silver`/`gold`.
- **`brewline-dbt-transform`** — `BigQuery Data Editor` on `silver`/`gold`, `BigQuery Data Viewer` (read-only) on `bronze`. Cannot write bronze.

Both additionally require `roles/bigquery.jobUser` at the **project** level — BigQuery's job-execution permission cannot be scoped to a single
dataset, since a "job" (any query execution) is a project-scoped resource independent of which data it touches. This is a separate, deliberately broader grant layered on top of the narrow dataset-level grants; job creation and data access remain two independently-scoped permissions, which is BigQuery's own least-privilege model working as intended, not a gap in this design.

Neither service account ever has a key generated. Both are accessed via **impersonation**: the developer authenticates as themselves via `gcloud auth application-default login` (producing short-lived, auto-refreshing Application Default Credentials), and is separately granted `roles/iam.serviceAccountTokenCreator` on each service account, allowing dbt (`impersonate_service_account` in `profiles.yml`) and the Python ingestion scripts (`google.auth.impersonated_credentials`) to request temporary, scoped tokens to act as that service account for the duration of a single operation. No key material exists anywhere, at any point, in any file.

## Alternative Considerations
- **Static service account key file** — Rejected. Blocked outright by org policy; would also be a strictly weaker security posture even without the policy (no expiry, easy to accidentally commit, valid indefinitely until manually revoked).
- **One shared service account for ingestion and transform** — Rejected. Violates least privilege; a compromised or buggy credential would have write access to the entire warehouse rather than being contained to the layer it belongs to.
- **Workload Identity Federation / GCP-attached service account identity**
  — Noted as the correct production-grade pattern (no user credentials or impersonation needed at all), but not reachable from a local Docker Desktop setup — it depends on running inside GCP's own infrastructure (e.g. Cloud Composer, GKE). Documented here as the natural next step for a genuine production deployment, not implemented in this local/portfolio context.

## Consequences
- Airflow's task containers require the developer's ADC credentials mounted read-only at runtime (`~/.config/gcloud` → `/root/.config/gcloud`), rather than any credential baked into an image.
- A reviewer wanting to run this pipeline against their own GCP project must independently create both service accounts, apply the IAM grants above, and complete the impersonation binding themselves — see `docs/gcp_setup_guide.md` for the exact commands.
- This design is inherently tied to the developer's own Google identity being trusted with impersonation rights; a real team would instead provision this per-engineer via a script or Terraform, not by hand — noted as a reasonable follow-up, not implemented here given the scope of a single-developer portfolio project.