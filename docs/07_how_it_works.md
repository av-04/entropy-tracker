# How It Works

Technical reference for the Entropy scoring engine — architecture, signal computation, performance characteristics, and design decisions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     ENTROPY ENGINE                       │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Git Analyzer │  │ Dep Analyzer │  │ AST Analyzer  │  │
│  │              │  │              │  │               │  │
│  │ git log      │  │ PyPI API     │  │ import graph  │  │
│  │ --numstat    │  │ (aiohttp)    │  │ blast radius  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         └─────────────────┼───────────────────┘          │
│                           ▼                              │
│                    Signal Merger                         │
│                           ▼                              │
│               Entropy Scorer + Forecaster                │
│               (parallel git blame via                    │
│                ThreadPoolExecutor)                       │
│                           ▼                              │
│          PostgreSQL + TimescaleDB (history)              │
│                           ▼                              │
│          CLI  │  HTML Report  │  FastAPI  │  Celery      │
└─────────────────────────────────────────────────────────┘
```

Each scan runs four steps in sequence:

```
Step 1  Git history analysis      → author decay, churn ratios, refactor dates
Step 2  Dependency analysis       → PyPI staleness, CVE counts per module
Step 3  Import graph construction → blast radius per module
Step 4  Scoring                   → composite score, bus factor, forecast
```

---

## Git Analyzer

The git analyzer extracts per-file decay signals from the repository's commit history.

### Implementation

Rather than using a Python library to walk commits one by one, Entropy makes a single native subprocess call:

```bash
git log \
  --since="36 months ago" \
  --format=COMMIT|%H|%ae|%ai \
  --numstat \
  --no-merges \
  --diff-filter=AM
```

This streams the entire relevant history in one operation — author email, timestamp, and per-file line statistics for every commit. The output is parsed in a single pass. No per-commit object deserialization, no Python wrapper overhead.

**Why native `git log` instead of PyDriller or GitPython:**
A Python library walking commits calls Git's object model repeatedly — one deserialization per commit. On Django (2,782 commits), this takes 3–8 minutes. A single `git log --numstat` subprocess call processes the same history in 2–5 seconds, because it runs entirely in native C.

### Time Window

By default, only commits from the last 36 months are analyzed. This ensures that knowledge decay reflects *current* team knowledge, not the original authors from 10 years ago. A module maintained by different engineers today is not a knowledge silo just because the original author left in 2015.

For repositories with no commits in the past 36 months (deprecated or archived codebases), Entropy automatically falls back to the full git history.

### Commit Classification

Every commit is classified as either **churn** or **refactor**:

| Condition | Classification |
|-----------|---------------|
| Total lines touched (added + deleted) > 200 | Churn — large change regardless of net delta |
| Net line change < 10 AND total lines touched < 200 AND files touched > 1 | Refactor — structural reorganization |
| Everything else | Churn |

The total-lines check prevents a common false negative: a complete file rewrite (e.g., 2,488 insertions and 2,486 deletions = net +2 lines) would incorrectly classify as a refactor using net delta alone. Entropy uses total lines touched to catch these cases correctly.

---

## Dependency Analyzer

The dep analyzer determines how far behind each module's direct dependencies are.

### Implementation

1. The project's dependency files are parsed in priority order: `uv.lock` → `poetry.lock` → `requirements.txt` → `pyproject.toml`
2. The AST analyzer extracts import statements from each Python file
3. Import names are mapped to PyPI package names
4. The PyPI JSON API is queried concurrently using `aiohttp` for all unique packages
5. Results are cached locally at `~/.entropy/pypi_cache/` for 24 hours

### Staleness Formula

For each package imported by a module:

```
months_behind  = months between installed version release date
                 and latest version release date

dep_velocity   = total releases / months since package first release
                 (measures how fast the ecosystem moves)

cve_count      = number of known CVEs for the installed version
                 (from pip-audit)

dep_risk       = months_behind × dep_velocity × (1 + cve_count)
```

The final dep score for a module is the normalized mean of `dep_risk` across all its direct dependencies, capped at 100.

**Why weight by velocity:** A dependency that releases monthly and is 12 versions behind is significantly more dangerous than a stable utility library that releases once a year with the same lag. Raw months-behind fails to distinguish these cases.

### Concurrent PyPI Fetching

All package queries are issued concurrently using `aiohttp`. For a codebase with 58 unique packages (Django), sequential fetching would take approximately 8 minutes at network latency. Concurrent fetching completes in 5–10 seconds.

---

## AST Analyzer

The AST analyzer builds a transitive import graph of the codebase to compute blast radius.

### Implementation

Python's built-in `ast` module parses each `.py` file to extract `import` and `from ... import` statements. These are resolved against the discovered source roots (flat layout and `src/` layout both supported).

The result is a directed graph where an edge from A to B means "module A imports module B." Blast radius is the number of nodes that can reach a given module through this graph — the transitive reverse-dependency count.

### Why Blast Radius Matters

A module's entropy score tells you how dangerous it is to touch. Blast radius tells you how dangerous it is to *have wrong*. A module scoring 70 with a blast radius of 450 is a higher operational risk than a module scoring 90 with a blast radius of 0 — because if the former fails or needs urgent rewriting, 450 other modules are affected.

```
boto/cloudsearch/search.py
  Score: 82   HIGH
  Blast radius: 453 modules

If this file needs emergency rewriting, 453 modules are affected.
Every author who wrote it is gone.
```

---

## Scoring Engine

### Composite Score Formula

```python
entropy_score = (
    knowledge_score * 0.35 +
    dep_score       * 0.30 +
    churn_score     * 0.20 +
    age_score       * 0.15
)
```

All inputs are normalized to 0–100. The output is rounded to one decimal place.

### Bus Factor Computation

Bus factor is computed via `git blame` — counting active authors who own more than 10% of current lines:

```python
bus_factor = count(
    authors where:
        lines_owned / total_lines > 0.10
        AND committed_in_last_6_months = True
)
```

`git blame` is an expensive operation (one subprocess call per file). Entropy only runs it for modules scoring above 50 (the threshold where bus factor becomes actionable), with a hard cap of 400 files per scan. Files below the threshold receive an approximation based on the author count from the git log pass.

Bus factor calculations are parallelized using `ThreadPoolExecutor` with 8 workers, since `subprocess.run` releases the Python GIL.

### Trajectory Forecasting

Because Entropy stores a scored snapshot in TimescaleDB on every scan, it accumulates a time series per module. Trajectory is computed using `numpy.polyfit` with degree 1 (linear regression) on the historical scores:

```python
slope, _ = numpy.polyfit(timestamps, scores, 1)
trend_per_month = round(slope * 30, 2)

forecast_30d  = min(current_score + trend_per_month * 1,  100)
forecast_90d  = min(current_score + trend_per_month * 3,  100)

if trend_per_month > 0:
    days_to_100 = (100 - current_score) / (trend_per_month / 30)
```

Forecast accuracy improves with more data points. With fewer than three historical scans, the forecast is marked as directional.

---

## Performance

All benchmarks run on a standard developer laptop (Windows, Intel i7, 16GB RAM).

| Repository | Modules | Commits | Scan Time | Notes |
|-----------|---------|---------|-----------|-------|
| demo-repo | 19 | 56 | ~5s | Artificial test repo |
| click | 62 | 731 | ~11s | |
| Django | 2,903 | 2,782 | ~34s | 36-month window |
| boto | 938 | 7,220 | ~45s | Full history (no recent commits) |

**Second scan times** are significantly faster due to PyPI response caching.

### Performance Optimizations

| Optimization | Impact |
|-------------|--------|
| Native `git log --numstat` instead of Python commit walk | ~20x speedup on large repos |
| Concurrent PyPI fetching with `aiohttp` | ~60x speedup for dep analysis (sequential → parallel) |
| PyPI response caching (24h TTL) | Near-zero dep analysis time on repeat scans |
| `git blame` only on modules scoring > 50 | ~60% reduction in blame subprocess calls |
| Parallel `git blame` via `ThreadPoolExecutor(8)` | ~8x speedup for bus factor computation |
| Batched terminal progress updates (every 100 commits) | Reduced I/O overhead on Windows |

---

## Design Decisions

**Why read git history instead of the code itself?**
Static analysis tools (SonarQube, pylint, mypy) read the code as it exists today. They cannot tell you whether the engineer who wrote it is still here, whether the dependencies it relies on have moved on, or whether the code has been growing through chaotic patches rather than intentional design. Git history contains signals that the code itself cannot.

**Why four signals and these specific weights?**
The weights were chosen to reflect recovery cost. Lost knowledge (0.35) is the hardest to recover — you cannot onboard someone into understanding three years of implicit context in a sprint. Dependency drift (0.30) is measurable and directly tied to CVE exposure. Churn (0.20) is a leading indicator but affected by team cadence. Age (0.15) is the weakest individual signal — old code maintained by active authors is not inherently risky.

**Why a 36-month git history window?**
Using all-time history on a 15-year-old codebase produces uniformly high knowledge decay scores — of course the original authors from 2009 are gone. The 36-month window focuses the knowledge signal on *current* team knowledge: who understands this code as it exists today, not who wrote the original version years ago.

**Why TimescaleDB instead of plain PostgreSQL?**
TimescaleDB's hypertable partitioning makes time-series range queries (e.g., "give me the entropy scores for this module over the last 90 days") orders of magnitude faster than equivalent queries on a standard PostgreSQL table as the history grows. The trajectory forecasting and trend features depend on fast access to historical time-series data.
