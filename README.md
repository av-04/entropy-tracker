# Entropy

The engineer who wrote `payments/gateway.py` left 18 months ago. Nobody else understands it. Entropy tells you that before production goes down.

![Entropy Report Output](./assets/demo.png)

Software does not just accumulate bugs. It **ages**. Code written three years ago, never touched, slowly becomes dangerous — not because it broke, but because the world around it changed. The library it depends on evolved. The external API it calls shifted its contract. The engineers who wrote it have left. 

This is **software entropy**. Entropy is a continuously-running analysis engine that combines git history, dependency drift, and code churn into a single decay score per module, and projects it forward in time.

---

## Quick Start

Get your first risk score in 3 commands:

```bash
# Install the CLI
pip install entropy-tracker

# Register a repository and run the first scan
entropy init ./my-repo

# See your most decayed, highest-risk modules
entropy report --top 10
```

---

## What Entropy Measures

Entropy combines four distinct signals into one module-level composite score (0–100):

| Signal | What it measures | Why it matters |
|--------|-----------------|----------------|
| **Knowledge Decay** | % of authors who touched this module that are still active | A module where 5 of 6 authors have gone inactive is a knowledge silo. |
| **Dependency Decay** | How far behind this module's direct dependencies are | A 12-month-old dep in a fast-moving ecosystem is riskier than a stable one. |
| **Churn-to-Touch** | Ratio of chaotic edits to intentional refactors | High churn with no refactoring = technical debt accumulating invisibly. |
| **Age Without Refactor** | Months since the last structural refactor | Old code that is never deliberately revisited drifts from team understanding. |

### The Entropy Output

Modules are scored from 0 to 100:
- **0–50 (Healthy):** Active authors, up-to-date dependencies, regular refactoring.
- **50–70 (Medium):** Aging code. Starting to drift.
- **70–85 (High):** Risky to touch. Single points of failure emerging.
- **85–100 (Critical):** A fire hazard. Do not ship features through this without remediation. 

You can inspect exactly why a file is failing:
```bash
entropy inspect payments/gateway.py
```

### Advanced Forecasting & Alerts

Because Entropy stores scores over time, it computes the **decay velocity** of each module and projects forward.

```bash
entropy forecast payments/gateway.py
# Output:
# 30 days → 90 (CRITICAL)
# 90 days → 97 (CRITICAL)
# Estimated unmaintainable: ~4 months
```

---

## Architecture 

Entropy runs entirely locally with zero external telemetry. The architecture includes:
- **Git Analyzer:** PyDriller + GitPython extract author decay and churn ratios.
- **Dep Analyzer:** PyPI API concurrent requests + pip-audit identify drift.
- **TimescaleDB:** Time-series storage for continuous scoring and forecasting.
- **FastAPI / Celery:** Optional background scheduler to continuously monitor repositories overnight.

## Roadmap & v2 Features

We are actively building features to embed Entropy permanently in engineering workflows:
- **PR-level Diffing:** `entropy diff --base main` to block PRs that increase complexity on undocumented modules.
- **Simulations:** "What happens to the codebase if Engineer X leaves?"
- **Ecosystem Expansion:** Full JavaScript / TypeScript support.
