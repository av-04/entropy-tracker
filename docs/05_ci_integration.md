# CI Integration

`entropy diff --base main` is the command that embeds Entropy permanently in an engineering team's workflow. It runs on every pull request, computes the entropy delta introduced by the branch, and surfaces risk before code is merged.

---

## How entropy diff Works

When you run `entropy diff --base main` from a feature branch:

1. Entropy identifies which files were changed in the current branch vs the base
2. It creates a temporary `git worktree` of the base branch — a clean checkout that does not disturb your working tree
3. Both branches are scored independently
4. The delta is computed per changed file and reported

The temporary worktree is cleaned up automatically. Your working directory is never modified.

---

## GitHub Actions

Add this workflow file to your repository to run entropy diff on every pull request:

```yaml
# .github/workflows/entropy.yml
name: Entropy Check

on:
  pull_request:
    branches: [main, master]

jobs:
  entropy:
    name: Code Decay Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0          # Full history is required for git analysis
                                  # Do not use fetch-depth: 1 — it will fail

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Entropy
        run: pip install entropy-tracker

      - name: Run entropy diff
        run: entropy diff --base ${{ github.base_ref }}
```

**Important:** `fetch-depth: 0` is required. Entropy reads the full git history of changed files. A shallow clone (the GitHub Actions default) will produce incomplete results or errors.

---

## Understanding the Output

```
Entropy Diff — feature/payment-refactor vs main

  Changed File             Delta    Scores         Severity
  payments/gateway.py      +8.2     71 → 79        HIGH → HIGH (worsening)
  auth/tokens.py           +2.1     77 → 79        HIGH
  utils/helpers.py         +0.4     44 → 44        HEALTHY
  payments/new_module.py   NEW      entropy: 12    HEALTHY

  Net branch entropy delta: +3.6 points across 3 changed files
  Highest risk: payments/gateway.py — single-author file gaining churn
```

**Delta** — how much the entropy score changed from base branch to current branch. A positive delta means the PR increased decay. A negative delta means the PR improved the module (rare, but happens after deliberate refactors).

**Scores** — the score on the base branch → the score on the current branch.

**Severity** — the severity at each score. If both are HIGH, the module was already risky and the PR is adding to it. This is the most important signal.

**NEW** — new files have no base score. They are shown with their initial score and never reported as a false positive delta.

---

## Recommended Workflow

Entropy diff is informational by default — it reports risk but does not fail the CI build. This is intentional. Engineers should make informed decisions about risk, not be blocked automatically.

The recommended CI policy is:

```
entropy diff --base main always runs.
Output is visible in the PR checks.
Engineers see the risk before merging.
For high-stakes codebases, fail if critical modules are worsened.
```

**To fail the build on high-risk changes**, check the exit code:

```yaml
- name: Run entropy diff
  run: |
    entropy diff --base ${{ github.base_ref }}
    # entropy diff exits with code 1 if any changed file
    # crosses the CRITICAL threshold (score >= 85)
    # Remove the above comment and the job will fail
```

Entropy exits with code `0` if no changed files cross the CRITICAL threshold, and code `1` if any do. This allows teams to selectively enforce blocking behavior.

---

## Adding a PR Comment

To post the entropy diff output as a comment on the pull request, add this to your workflow:

```yaml
- name: Run entropy diff and capture output
  id: entropy
  run: |
    echo "output<<EOF" >> $GITHUB_OUTPUT
    entropy diff --base ${{ github.base_ref }} >> $GITHUB_OUTPUT
    echo "EOF" >> $GITHUB_OUTPUT

- name: Comment on PR
  uses: actions/github-script@v7
  if: always()
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: '## Entropy Report\n```\n' + '${{ steps.entropy.outputs.output }}' + '\n```'
      })
```

---

## Pre-commit Hook

For teams that want entropy diff to run before every commit rather than in CI:

```bash
# .git/hooks/pre-push
#!/bin/bash
echo "Running entropy diff..."
entropy diff --base main
if [ $? -ne 0 ]; then
  echo "Entropy check failed. Review the output above before pushing."
  exit 1
fi
```

Make the hook executable:

```bash
chmod +x .git/hooks/pre-push
```

Or use [pre-commit](https://pre-commit.com/) for team-wide hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: entropy-diff
        name: Entropy Decay Check
        entry: entropy diff --base main
        language: system
        pass_filenames: false
        stages: [push]
```

---

## Interpreting Results in Code Review

When entropy diff appears in a PR, here is how to interpret the numbers:

**A new file with entropy > 50 on creation**
This is a signal to look at the dependencies being imported and whether the code structure will be easy to maintain. Not urgent, but worth noting.

**An existing HIGH file with a positive delta**
The PR is adding complexity to an already risky module. Ask: is this unavoidable? Can the change be made in a way that also reduces churn (e.g., extracting a helper function rather than adding inline logic)?

**A CRITICAL file with any positive delta**
This module is already at the point of unmaintainability. Any increase is a warning. This is the moment to ask whether the feature being added could be implemented in a different, healthier module instead.

**A positive delta on a module with bus factor 1**
The only person who understands this code is about to have more complexity to carry alone. Consider pairing, documentation, or knowledge transfer as part of the PR process.
