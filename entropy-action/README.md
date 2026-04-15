# entropy-action

**GitHub Action for [entropy-tracker](https://pypi.org/project/entropy-tracker/)** — detect high-decay modules touched by a pull request before they are merged.

[![Marketplace](https://img.shields.io/badge/GitHub%20Marketplace-entropy--action-orange)](https://github.com/marketplace/actions/entropy-code-decay-check)
[![PyPI](https://img.shields.io/pypi/v/entropy-tracker?color=2D6A4F)](https://pypi.org/project/entropy-tracker/)

## What it does

On every pull request, this action:
1. Detects which Python files were changed in the PR.
2. Computes the entropy (decay) score for each changed file.
3. Prints a rich diff table showing before/after scores, severity, and trend.
4. Optionally **fails the PR** if any changed file exceeds your configured threshold.

Entropy score combines: knowledge decay (lost authors), dependency drift, churn ratio, and age without refactor — into a single number from 0 to 100.

## Usage

### Report-only mode (never blocks merges)

```yaml
# .github/workflows/entropy.yml
name: Entropy Check

on: [pull_request]

jobs:
  entropy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # required — full history for git analysis
      - uses: hari715om/entropy-action@v1
        with:
          base-branch: main
```

### Gate mode (blocks PRs that touch high-entropy files)

```yaml
- uses: hari715om/entropy-action@v1
  with:
    base-branch: main
    fail-above: 75     # fail if any changed file scores above 75/100
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `base-branch` | No | `main` | Branch to diff entropy scores against |
| `fail-above` | No | `0` | Entropy threshold (0-100). 0 = report only, never fail |
| `python-version` | No | `3.11` | Python version to install entropy-tracker with |

## How the score works

| Score | Severity | Meaning |
|-------|----------|---------|
| 85-100 | CRITICAL | Knowledge nearly gone, deps stale, high churn — dangerous |
| 70-84 | HIGH | Risky. Single point of failure likely. Review carefully |
| 50-69 | MEDIUM | Aging but manageable |
| 0-49 | HEALTHY | Well-maintained module |

## Example PR comment output

```
Entropy Diff [main -> HEAD]

  Changed File                Score       Severity  Delta
  payments/gateway.py         87 -> 89    CRITICAL  +2.1
  auth/tokens.py              45 -> 46    HEALTHY   +0.8

  Net branch entropy delta: +2.9 points across 2 changed files
  Highest risk: payments/gateway.py -- review carefully

  ENTROPY GATE FAILED --fail-above 75 threshold breached by 1 file(s):
    payments/gateway.py  score=89
```

## Full git history required

Always use `fetch-depth: 0` in your checkout step. Entropy's knowledge decay and churn signals require the full commit history. Without it, all scores will be artificially low.

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0   # do not remove this
```

## Install the CLI locally

```bash
pip install entropy-tracker
entropy report --top 10
entropy inspect payments/gateway.py
```

[PyPI](https://pypi.org/project/entropy-tracker/) | [GitHub](https://github.com/hari715om/entropy-tracker) | MIT License
