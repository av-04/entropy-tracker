# Entropy Documentation

## Documentation Structure

This documentation is organized as seven pages, matching the sidebar navigation of the Entropy website. Each page covers one distinct area. Users follow them in order during initial setup, then reference individual pages later.

---

### Pages

| # | Page | What it covers |
|---|------|---------------|
| 1 | **Introduction** | What Entropy is, the problem it solves, how the scoring model works |
| 2 | **Installation** | pip install, system requirements, first scan in 60 seconds |
| 3 | **CLI Reference** | Every command, every flag, every output format — the complete reference |
| 4 | **Configuration** | entropy.toml — all options with explanations and defaults |
| 5 | **CI Integration** | GitHub Actions, entropy diff, PR gating workflow |
| 6 | **API & Dashboard** | REST API endpoints, Docker stack, self-hosted dashboard |
| 7 | **How It Works** | Architecture, scoring formula, signal computation, performance |

---

### Suggested Website Sidebar Structure

```
ENTROPY DOCS
├── Introduction
├── Installation
├── CLI Reference
│   ├── init
│   ├── scan
│   ├── report
│   ├── inspect
│   ├── diff
│   ├── trend
│   ├── forecast
│   └── server
├── Configuration
├── CI Integration
├── API & Dashboard
│   ├── REST API
│   └── Docker Setup
└── How It Works
    ├── Architecture
    ├── Scoring Model
    └── Performance
```
