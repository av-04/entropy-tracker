# Introduction

## What is Entropy?

Entropy is a command-line tool that measures how dangerous each module in a codebase has become over time — not by reading the code itself, but by reading its history.

Every codebase has files that engineers are afraid to touch. Not because the code is wrong, but because nobody fully understands it anymore. The original author left. The dependencies are ancient. Every PR that touches it breaks something unexpected. That fear exists in every engineering team. Until now, no tool has measured it.

Entropy gives that fear a number.

```bash
entropy report --top 5

  Module                      Score   Severity    Trend
  payments/gateway.py           94    CRITICAL    ↑ +3.2/mo
  auth/legacy_tokens.py         91    CRITICAL    ↑↑ +5.1/mo
  core/database/connector.py    83    HIGH         → +0.8/mo
  utils/email_sender.py         71    HIGH         ↑ +1.1/mo
  api/v1/handlers.py            68    MEDIUM       → +0.2/mo
```

---

## The Problem Entropy Solves

Software does not just accumulate bugs. It **ages**.

Code written three years ago, never touched, slowly becomes dangerous — not because it broke, but because the world around it changed:

- The library it depends on has released 14 major versions since it was pinned
- The external API it calls has changed its contract
- The four engineers who understood it have all moved on
- The test coverage around it has quietly shrunk

None of these signals trigger an alert. No linter catches them. They accumulate silently until something breaks in production and the team spends three days figuring out code nobody wrote and nobody understands.

Entropy catches these patterns before they become incidents.

---

## What Entropy Measures

Entropy combines four independent signals into one composite score per module, from 0 (no decay) to 100 (critically dangerous):

### Knowledge Decay
Who wrote this file, and are they still here?

Entropy reads the full git history of each file, identifies every author who contributed meaningful code, and checks which of them are still active in the repository (defined as having committed in the last 6 months by default). A file where 5 of 6 original authors have gone inactive is a knowledge silo — dangerous to touch, difficult to debug, impossible to reason about without significant investment.

**Weight in composite score: 35%**

### Dependency Decay
How far behind are this file's dependencies?

Entropy maps each file's imports to their upstream PyPI packages, queries the PyPI API for current release history, and computes how far behind the installed version is — weighted by how fast that ecosystem moves. A dependency that releases monthly and is 18 months behind is significantly riskier than one that releases yearly with the same lag. CVE counts are factored in via pip-audit.

**Weight in composite score: 30%**

### Churn-to-Touch Ratio
Is this file being maintained or just patched?

Not all commits are equal. Entropy classifies each commit as either a *churn commit* (large, unfocused changes — the kind that add complexity without intention) or a *refactor commit* (structural improvements with minimal net line change). A file with 60 churn commits and 2 refactor commits over its lifetime is accumulating invisible debt with every change. The ratio of these two commit types is the churn signal.

**Weight in composite score: 20%**

### Age Without Refactor
When was the last time anyone deliberately restructured this?

Code that is never intentionally revisited drifts from team understanding. Entropy tracks the date of the last refactor commit — the last time an engineer restructured rather than just added or patched. Files that have not been deliberately revisited in years are drifting toward unmaintainability, regardless of how many bug fixes have been applied.

**Weight in composite score: 15%**

---

## Severity Thresholds

| Score | Severity | What it means |
|-------|----------|--------------|
| 85–100 | **Critical** | A fire hazard. Do not ship features through this module without remediation. Immediate attention required. |
| 70–85 | **High** | Risky to touch. Knowledge silos and stale dependencies are compounding. Schedule attention. |
| 50–70 | **Medium** | Aging. Multiple signals drifting in the wrong direction. Worth monitoring. |
| 0–50 | **Healthy** | Active authors, current dependencies, regular refactoring. No action needed. |

---

## Additional Risk Signals

Beyond the composite score, Entropy surfaces two supplementary signals that are reported alongside every module:

### Blast Radius
How many other modules would be affected if this one needed emergency rewriting?

Entropy builds a transitive import graph of the entire codebase using AST analysis. The blast radius of a module is the number of other modules that directly or indirectly import it. A high-entropy file with a blast radius of 450 is not just dangerous to touch — it is dangerous to ignore.

```
boto/cloudsearch/search.py
  Score: 82   HIGH
  Blast Radius: 453 modules depend on this file
```

### Bus Factor
How many engineers understand this module well enough to safely modify it?

Bus factor is calculated via `git blame` — it counts the number of active engineers who own more than 10% of the current lines in the file. A bus factor of 1 means a single engineer is the only person who could safely work on this code. If they leave, that knowledge is gone.

```
payments/gateway.py
  Bus Factor: 1  ← single point of knowledge failure
```

---

## Trajectory Prediction

Because Entropy stores scores in a time-series database on every scan, it can compute the **decay velocity** of each module and project it forward. This turns Entropy from a diagnostic tool into a predictive one.

```
entropy forecast payments/gateway.py

  Current Score: 87
  Trend: +3.2 entropy points / month

  Forecast:
    30 days  →  90
    90 days  →  97
    Estimated unmaintainable in: ~4 months
```

A module scoring 60 today with a trend of +5/month is more urgent than a module scoring 80 with no trend. Entropy surfaces both dimensions.

---

## Who Entropy Is For

**Individual engineers** — run it against your own codebase before a major refactor. Know which files will surprise you before you touch them.

**Engineering leads** — use it for sprint planning and technical debt prioritization. "payments/gateway.py has a blast radius of 37 and a bus factor of 1" is a business risk argument, not just a technical one.

**Platform and DevOps teams** — embed `entropy diff --base main` in CI. Flag PRs that add churn to already high-risk files before they are merged.

**New engineers joining a team** — run `entropy report --top 10` on your first day. Immediately know which parts of the codebase are dangerous and should be approached carefully.

---

## How It Differs From Existing Tools

| Tool | What it measures | What it misses |
|------|-----------------|---------------|
| SonarQube | Code smells, duplication, complexity | Who understands this code. Whether knowledge is leaving the team. |
| Dependabot | Vulnerable and outdated dependencies | Everything about human knowledge and code history. |
| CodeScene | Code churn × complexity hotspots | Dependency staleness, trajectory forecasting, free self-hosted use, PR-level diff. |
| git-fame | Author attribution per file | Risk scoring, blast radius, composite signals, any synthesis. |
| **Entropy** | All four signals combined + blast radius + bus factor + forecast | — |

Entropy is the only tool that combines git history, dependency drift, and knowledge decay into a single actionable risk score, runs locally for free, and integrates into CI with one command.
