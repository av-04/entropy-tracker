# Configuration

Entropy works without any configuration file. All defaults are production-ready. Create `entropy.toml` in your repository root when you need to tune the scoring model or enable integrations.

---

## entropy.toml

Place this file in the root of the repository you are analyzing:

```toml
[repo]
name     = "my-service"
language = "python"        # python | javascript | mixed (default: python)

[scoring.weights]
knowledge  = 0.35          # Knowledge decay signal weight
dependency = 0.30          # Dependency decay signal weight
churn      = 0.20          # Churn-to-touch ratio weight
age        = 0.15          # Age without refactor weight
# Weights must sum to 1.0

[scoring.thresholds]
critical = 85              # Score at or above this = CRITICAL
high     = 70              # Score at or above this = HIGH
medium   = 50              # Score at or above this = MEDIUM
# Below medium threshold = HEALTHY

[analysis]
active_author_window_days   = 180   # Days — defines what "active" means for knowledge decay
churn_total_line_threshold  = 200   # Total lines touched (added + deleted) to classify as churn
refactor_net_line_threshold = 10    # Max net line change to classify as refactor
age_ceiling_months          = 36    # Months at which the age score reaches 100

[alerts]
notify_on   = ["CRITICAL", "HIGH"]
webhook_url = ""                    # Slack or Discord webhook URL (optional)
```

---

## Configuration Reference

### [repo]

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | string | directory name | Human-readable label shown in reports |
| `language` | string | `python` | Primary language for dependency analysis. `python`, `javascript`, or `mixed` |

---

### [scoring.weights]

Controls how much each signal contributes to the composite entropy score. Weights must sum to exactly `1.0`.

| Key | Default | Reasoning |
|-----|---------|-----------|
| `knowledge` | `0.35` | Knowledge decay has the highest weight because lost institutional knowledge is the hardest to recover. You can update a dependency in an afternoon. You cannot recover the mental model of a departed engineer. |
| `dependency` | `0.30` | Dependency drift is directly measurable and directly tied to CVE exposure and breaking changes. |
| `churn` | `0.20` | Churn is a leading indicator of debt accumulation, but lower weight because some churn is expected during active development. |
| `age` | `0.15` | Age is the weakest individual signal — old code is not necessarily risky if it is well-understood and well-maintained. |

**Example — security-focused tuning:**

```toml
[scoring.weights]
knowledge  = 0.25
dependency = 0.50    # Raise dep weight for security-sensitive codebases
churn      = 0.15
age        = 0.10
```

**Example — team knowledge focused:**

```toml
[scoring.weights]
knowledge  = 0.55    # Raise knowledge weight for teams with high turnover
dependency = 0.20
churn      = 0.15
age        = 0.10
```

---

### [scoring.thresholds]

Defines the score boundaries for each severity level. Adjust these if your codebase is new and scores are uniformly low, or mature and scores cluster in the medium range.

| Key | Default | Description |
|-----|---------|-------------|
| `critical` | `85` | Modules at this score or above are flagged CRITICAL |
| `high` | `70` | Modules at this score or above are flagged HIGH |
| `medium` | `50` | Modules at this score or above are flagged MEDIUM |

---

### [analysis]

Controls how the underlying analyzers classify and window data.

| Key | Default | Description |
|-----|---------|-------------|
| `active_author_window_days` | `180` | An author is "active" if they have committed to any file in the repository within this window. Increasing this window is useful for teams with slower commit cadences. |
| `churn_total_line_threshold` | `200` | A commit is classified as churn if the total lines touched (added + deleted) exceeds this value, regardless of net change. This prevents large file rewrites from being misclassified as refactors. |
| `refactor_net_line_threshold` | `10` | A commit is classified as a refactor if the net line change is below this value AND the total lines touched is below `churn_total_line_threshold`. |
| `age_ceiling_months` | `36` | The number of months at which the age signal reaches its maximum score of 100. Files not deliberately refactored for this long score 100 on age. |

---

### [alerts]

| Key | Default | Description |
|-----|---------|-------------|
| `notify_on` | `["CRITICAL", "HIGH"]` | Severity levels that trigger alerts. Options: `CRITICAL`, `HIGH`, `MEDIUM` |
| `webhook_url` | `""` | Slack or Discord incoming webhook URL. When set, alerts are posted to the channel. Leave empty to disable. |

**Slack webhook example:**

```toml
[alerts]
notify_on   = ["CRITICAL"]
webhook_url = "https://hooks.slack.com/services/T00000/B00000/XXXXXXXX"
```

Alert payload format:

```json
{
  "text": "⚠ CRITICAL: payments/gateway.py scored 94\nBlast radius: 12 modules\nBus factor: 1"
}
```

---

## Auto-Discovery

Entropy searches for `entropy.toml` starting from the repository path and walking up the directory tree. This means a single `entropy.toml` at the monorepo root applies to all sub-packages unless overridden by a more specific file closer to the target.

---

## Using Multiple Configurations

For monorepos with different risk profiles per service:

```
my-monorepo/
├── entropy.toml              ← default config for all services
├── services/
│   ├── payments/
│   │   └── entropy.toml     ← stricter thresholds for payments service
│   └── analytics/
│       └── entropy.toml     ← lighter thresholds for analytics service
```

```bash
# Scan with the payments-specific config
entropy report ./services/payments --top 10
```
