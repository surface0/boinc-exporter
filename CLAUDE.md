# CLAUDE.md

Project-level guidance for Claude Code working in this repository.
These instructions are specific to **boinc-exporter** and complement any global instructions.

## Project overview

A Prometheus / VictoriaMetrics exporter for BOINC. It connects to a BOINC
client over the GUI RPC interface (TCP/31416), reads task/project state, and
exposes a Prometheus-compatible `/metrics` endpoint. A Grafana dashboard and a
docker-compose stack (exporter + VictoriaMetrics + Grafana) ship with the repo.

## Layout

| Path | Purpose |
|---|---|
| `boinc_exporter/boinc_client.py` | GUI RPC client; parses XML replies into dataclasses (`Project`, `Task`, ...) |
| `boinc_exporter/collector.py` | Prometheus collector; turns client data into metric families |
| `boinc_exporter/main.py`, `__main__.py` | Entry point / HTTP server wiring |
| `tests/` | pytest suite (one file per module) |
| `grafana/dashboards/boinc.json` | Provisioned Grafana dashboard (classic schema, `schemaVersion` 38) |
| `grafana/provisioning/`, `victoriametrics/` | Provisioning + scrape config |
| `docs/` | Supplementary docs (see ERRORS handling below) |

## Development commands

```bash
pip install -r requirements-dev.txt && pip install -e .

python -m pytest -v                                  # run tests
python -m pytest --cov=boinc_exporter --cov-report=term-missing   # with coverage
```

CI (`.github/workflows/test.yml`) runs the suite on Python 3.11 and 3.12. Keep
both versions green. Coverage is reported but not gated — still, add or update
tests for any behavior change.

## Coding conventions

- **Python 3.11+.** Use standard-library-only runtime code where possible; the
  sole runtime dependency is `prometheus-client`. Do not add dependencies
  without a clear reason.
- Follow the existing style: PEP 8, 4-space indent, type hints on public
  functions, `@dataclass` for data carriers (see `boinc_client.py`).
- No linter/formatter is configured. Match the surrounding code rather than
  reformatting unrelated lines. If introducing tooling (ruff/black/mypy),
  record it as an ADR first (see below).
- Every behavior change ships with a test. Mirror the existing per-module test
  layout in `tests/`.
- Metric names follow the `boinc_*` prefix and Prometheus naming conventions;
  keep labels stable — they are part of the dashboard/queries contract.

## Grafana dashboard

- `grafana/dashboards/boinc.json` uses the **classic dashboard schema**
  (`schemaVersion` 38, panels with `gridPos`). When importing layout changes
  exported from the Grafana UI (which now uses the v2 `elements`/`layout`
  schema), translate them back into this classic format — do not switch the
  file's schema.
- Credit metrics (`*_total_credit`, `*_avg_credit`) come from BOINC's
  account-level fields (`user_total_credit` / `user_expavg_credit`) and are
  identical on every host sharing the same account. Aggregate them with
  `max by (project)`, never `sum`, to avoid multi-host double counting.
  Per-host counters (`njobs_*`) are host-local, so `sum` is correct there.
- After validating any edit to the dashboard JSON, run a JSON parse check
  (e.g. `node -e "JSON.parse(require('fs').readFileSync('grafana/dashboards/boinc.json','utf8'))"`).
  Visual/transformation behavior must be verified in the Grafana UI; do not
  assume a transformation renders as intended.

## ERRORS handling

`docs/ERRORS.md` is the running troubleshooting log for this project.

- **When to append:** any time a working approach took **2 or more attempts**,
  record what failed, what worked, and the lesson to remember next time.
- **Location:** always `docs/ERRORS.md` (not the repo root). Keep it in English.
- It is committed to the repo (it is shared knowledge, not scratch). Commit it
  separately from feature changes when practical.

## Architecture Decision Records (ADR)

Record non-obvious or hard-to-reverse decisions (e.g. adopting a linter,
changing the dashboard schema, adding a runtime dependency, changing a metric
name or label) as an ADR.

- **Location:** `docs/adr/NNNN-short-title.md` (zero-padded sequential number,
  e.g. `0001-use-classic-grafana-schema.md`). Create the `docs/adr/` directory
  when the first ADR is written.
- **Template:**

  ```markdown
  # NNNN. <Title>

  - Status: Proposed | Accepted | Superseded by ADR-XXXX
  - Date: YYYY-MM-DD

  ## Context
  What problem/forces led to this decision.

  ## Decision
  The decision, stated plainly.

  ## Consequences
  Trade-offs, follow-ups, and what this rules out.
  ```

- ADRs are immutable once Accepted: supersede with a new ADR rather than
  rewriting history.

## Git / commit conventions

- This repo uses a **PR-based workflow**; the default branch is `main`. Do not
  commit directly to `main` — work on a feature branch and open a PR.
- Commit messages: English, imperative mood. A `type(scope): summary` prefix
  (e.g. `refactor(grafana): ...`) is welcome but not mandatory; keep the
  subject concise and use the body to explain the *why*.
- Keep commits focused: separate documentation/notes commits from
  feature/behavior commits when it keeps the history clearer.
- Only commit or push when explicitly asked.
