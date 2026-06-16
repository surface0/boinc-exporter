# Contributing to BOINC Exporter

Thanks for your interest in improving BOINC Exporter! This document covers how
to set up a development environment, the conventions this project follows, and
how to submit changes.

## Getting started

```bash
git clone https://github.com/surface0/boinc-exporter.git
cd boinc-exporter

pip install -r requirements-dev.txt
pip install -e .
```

## Running the tests

Every behavior change must ship with a test. Mirror the existing per-module
layout under `tests/`.

```bash
python -m pytest -v

# with coverage
python -m pytest --cov=boinc_exporter --cov-report=term-missing
```

CI runs the suite on Python 3.11 and 3.12 — keep both versions green.

## Coding conventions

- **Python 3.11+.** Prefer the standard library for runtime code; the only
  runtime dependency is `prometheus-client`. Do not add dependencies without a
  clear reason.
- Follow the existing style: PEP 8, 4-space indent, type hints on public
  functions, and `@dataclass` for data carriers (see `boinc_exporter/boinc_client.py`).
- No linter/formatter is configured. Match the surrounding code rather than
  reformatting unrelated lines.
- Metric names use the `boinc_*` prefix and follow Prometheus naming
  conventions. Labels are part of the dashboard/query contract — keep them
  stable.

## Grafana dashboard changes

`grafana/dashboards/boinc.json` uses the **classic dashboard schema**
(`schemaVersion` 38, panels with `gridPos`). If you export layout changes from
the Grafana UI (which uses the newer v2 schema), translate them back into the
classic format — do not switch the file's schema. After editing, run a JSON
parse check:

```bash
node -e "JSON.parse(require('fs').readFileSync('grafana/dashboards/boinc.json','utf8'))"
```

Credit metrics (`*_total_credit`, `*_avg_credit`) are account-level and
identical across hosts sharing an account — aggregate them with `max by
(project)`, never `sum`. Per-host counters (`njobs_*`) are host-local, so `sum`
is correct there.

## Submitting changes

This repository uses a **PR-based workflow**; `main` is the default branch.

1. Create a feature branch — do not commit directly to `main`.
2. Make your change with accompanying tests, and keep commits focused
   (separate documentation commits from behavior changes when practical).
3. Use English, imperative-mood commit messages. A `type(scope): summary`
   prefix (e.g. `feat(collector): ...`) is welcome but not mandatory.
4. Ensure the test suite passes on Python 3.11 and 3.12.
5. Open a pull request describing **what** changed and **why**.

## Releasing

Container images are published to Docker Hub (`seizu/boinc-exporter`) by CI.
To cut a new release, push a version tag:

```bash
git tag v1.0.0
git push --tags
# GitHub Actions will build and push the image to Docker Hub automatically
```

## Reporting bugs and requesting features

Open an issue on GitHub with enough detail to reproduce the problem (BOINC
client version, exporter version, relevant logs, and the metrics or behavior
you observed vs. expected).

For **security** issues, do not open a public issue — see
[SECURITY.md](SECURITY.md).
