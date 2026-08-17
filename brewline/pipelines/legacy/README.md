# Legacy Pipeline (Stage 1)

This was my first iteration — hand-rolled Python + SQL before introducing dbt.
I kept it to show the progression from ad-hoc scripts to a proper transformation framework.
This is intentionally left broken to kept the legacy true to the original v1 design (messy and unstructured).

**Why it was replaced:**
- No version control for SQL logic
- No automated testing
- No documentation generation
- Hard to track data lineage

**references/** holds the v1 local CSV reference data the original transform.py read directly; superseded by brewline_dbt/seeds/ once the project moved to dbt.

**What replaced it:** `brewline_dbt/` with 15+ models, 40+ tests, and auto-generated docs.