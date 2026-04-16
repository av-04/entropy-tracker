# CLI Reference

Complete reference for all Entropy commands and flags.

---

## entropy init

Register a repository and run the first scan.

```bash
entropy init <path> [--name <label>]
```

**Arguments**

| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Path to the root of a git repository |
| `--name` | No | Human-readable label for this repository (defaults to directory name) |

**Examples**

```bash
entropy init ./my-repo
entropy init ./repos/django --name django
entropy init /home/user/projects/api --name production-api
```

**What it does**

Runs a full four-step scan: git history analysis → dependency analysis → import graph construction → scoring. Results are stored in the database. If the database does not exist, it is created automatically.

On first run against a large repository, this may take 30–90 seconds. Subsequent scans are incremental and faster.

---

## entropy scan

Re-scan a repository that has already been registered.

```bash
entropy scan <path>
```

**Examples**

```bash
entropy scan ./my-repo
```

Use this to update scores after new commits have been pushed, or to rebuild the scan history for trend tracking.

---

## entropy report

Display all scanned modules sorted by entropy score.

```bash
entropy report [<path>] [--top <n>] [--exclude <prefix>] [--format <fmt>] [--verbose]
```

**Flags**

| Flag | Default | Description |
|------|---------|-------------|
| `--top <n>` | `50` | Show only the N highest-scoring modules. Use `--top 0` for all modules. |
| `--exclude <prefix>` | None | Exclude modules matching a path prefix. Can be used multiple times. |
| `--format html` | terminal | Export the report as a standalone HTML file |
| `--verbose` | False | Show full signal breakdown (Knowledge, Deps, Churn, Age) for each row |

**Examples**

```bash
# Worst 10 modules
entropy report --top 10

# Source modules only, excluding tests and docs
entropy report --top 20 --exclude tests/ --exclude docs/

# Full HTML export
entropy report --top 0 --format html

# With full signal breakdown
entropy report --top 20 --verbose
```

**Terminal output (default)**

```
Entropy Report — my-repo

  Module                         Score   Severity    Trend
  payments/gateway.py              94    CRITICAL    ↑ +3.2/mo
  auth/legacy_tokens.py            91    CRITICAL    ↑↑ +5.1/mo
  core/database/connector.py       83    HIGH         → +0.8/mo
```

**Terminal output (--verbose)**

```
  Module                   Score  Know  Deps  Churn  Age  Blast  Bus  Severity
  payments/gateway.py        94    85   100   100    96    12     1   CRITICAL
```

**HTML export**

The HTML report is a self-contained dark-themed file with a severity distribution bar, stats grid, color-coded score pills, and a column reference legend. Suitable for sharing with stakeholders or archiving.

---

## entropy inspect

Full signal breakdown for a single module, including forecast.

```bash
entropy inspect <module_path> [--repo <path>]
```

**Arguments**

| Argument | Required | Description |
|----------|----------|-------------|
| `module_path` | Yes | Path to the module, relative to the repository root |
| `--repo` | No | Repository path (required if not running from the repo root) |

**Examples**

```bash
entropy inspect payments/gateway.py
entropy inspect django/db/models/query.py --repo ./repos/django
```

**Output**

```
Module: payments/gateway.py
────────────────────────────────────────────────────
  Entropy Score:        94 / 100   ⚠ CRITICAL
  Knowledge Decay:      85 / 100   (1 of 6 authors still active)
  Dependency Decay:    100 / 100   (22 months behind, 2 CVEs)
  Churn-to-Touch:      100 / 100   (60 churn / 2 refactor)
  Age Without Refactor: 96 / 100   (2.8 years)
  Trend:                +3.2 entropy points / month

  Forecast:
    30 days  →  97
    60 days  →  99
    90 days  →  100
    Estimated unmaintainable: ~3 months

  Blast Radius:  12 modules import this file
  Bus Factor:    1  ← single point of knowledge failure
```

---

## entropy diff

Compute the entropy delta between the current branch and a base branch.

```bash
entropy diff --base <branch>
```

**Flags**

| Flag | Required | Description |
|------|----------|-------------|
| `--base <branch>` | Yes | Branch to compare against (typically `main` or `master`) |

**Examples**

```bash
# From your feature branch:
entropy diff --base main
entropy diff --base develop
```

**Output**

```
Entropy Diff — feature-branch vs main

  Changed File           Delta    Scores        Severity
  payments/gateway.py    +8.2     71 → 79       HIGH → HIGH (worsening)
  auth/tokens.py         +2.1     77 → 79       HIGH
  utils/helpers.py       +0.4     44 → 44       HEALTHY

  Net branch entropy delta: +3.6 points across 3 changed files
  Highest risk: payments/gateway.py — single-author file gaining churn
```

**New file behavior**

New files that have no score in the base branch are shown with their initial score and labeled as NEW — they do not report a false positive delta:

```
  payments/new_module.py   NEW   entropy: 12   HEALTHY
```

**How it works**

Entropy uses `git worktree` to create a temporary checkout of the base branch without disturbing the working tree. Both branches are scored, and the delta is computed per changed file. The temporary worktree is cleaned up automatically.

---

## entropy trend

Display the entropy trajectory for a repository over time.

```bash
entropy trend [<path>] [--last <period>]
```

**Flags**

| Flag | Default | Description |
|------|---------|-------------|
| `--last <period>` | `90days` | Time window to display. Examples: `30days`, `90days`, `6months` |

**Examples**

```bash
entropy trend ./my-repo
entropy trend --last 30days
```

**Note:** Trend data requires multiple scans stored in PostgreSQL + TimescaleDB. The trend command shows no data if only one scan has been run, or if using the SQLite fallback.

---

## entropy forecast

Project a single module's entropy score forward in time.

```bash
entropy forecast <module_path> [--repo <path>]
```

**Examples**

```bash
entropy forecast payments/gateway.py
entropy forecast django/db/models/query.py --repo ./repos/django
```

**Output**

```
  Current Score: 87
  Trend: +3.2 entropy points / month

  Projected:
    30 days  →  90
    90 days  →  97
    Estimated unmaintainable: ~4 months
```

**Note:** Forecast accuracy improves with more scan history. With fewer than three historical data points, the projection is based on a linear model and should be treated as directional rather than precise.

---

## entropy server

Start the FastAPI backend and serve the React dashboard.

```bash
entropy server [--host <host>] [--port <port>]
```

**Flags**

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind the server to |
| `--port` | `8000` | Port to listen on |

**Examples**

```bash
entropy server
entropy server --port 9000
```

After starting, the dashboard is available at `http://localhost:8000` and the API documentation at `http://localhost:8000/api/docs`.

For production deployment, use the Docker Compose production configuration instead of running `entropy server` directly. See the API & Dashboard section.

---

## Global Flags

These flags are available on all commands:

| Flag | Description |
|------|-------------|
| `--version` | Print the installed Entropy version and exit |
| `--help` | Show help text for any command |

```bash
entropy --version
entropy report --help
entropy diff --help
```
