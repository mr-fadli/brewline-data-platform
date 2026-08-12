# Legacy Pipeline (Stage 1)

This was my first iteration — hand-rolled Python + SQL before introducing dbt.
I kept it to show the progression from ad-hoc scripts to a proper transformation framework.

**Why it was replaced:**
- No version control for SQL logic
- No automated testing
- No documentation generation
- Hard to track data lineage

**What replaced it:** `brewline_dbt/` with 15+ models, 40+ tests, and auto-generated docs.