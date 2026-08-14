# ADR-016 : Installable Package Structure

## Status
Accepted

## Context
cross-folder imports relied on manually-computed `sys.path.append()` calls in every entrypoint script, fragile across refactors.

## Decision
`pyproject.toml` + `pip install -e .`, dependencies split into `base`/`gcp`/`dev` optional extras.

## Alternative Rejected
keeping `sys.path` hacks (kept breaking on folder moves).

## Consequences
task Docker images must `COPY` and `pip install -e .` the package at build time, meaning code changes require an image rebuild, not just a bind-mount refresh — a real, ongoing dev-loop cost, worth stating plainly.