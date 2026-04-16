# Installation

## Requirements

- Python 3.10 or higher
- Git (must be available in your system PATH)
- No API keys required
- No telemetry or external services required for core functionality

---

## Install via pip

```bash
pip install entropy-tracker
```

Verify the installation:

```bash
entropy --version
# entropy 1.0.0
```

---

## First Scan in 60 Seconds

Point Entropy at any local git repository:

```bash
# Step 1 — Register the repo and run the first scan
entropy init ./my-repo

# Step 2 — See the highest-risk modules
entropy report --top 10

# Step 3 — Inspect a specific file
entropy inspect path/to/risky/module.py
```

That is all that is required for the core CLI to work. No database, no Docker, no configuration file needed to start.

---

## Scanning a Remote Repository

To scan a repository you do not have locally:

```bash
# Clone it first, then scan
git clone https://github.com/org/repo.git ./repos/my-repo
entropy init ./repos/my-repo
entropy report --top 10
```

---

## Optional: PostgreSQL + TimescaleDB

By default, Entropy stores scan history in SQLite, which is sufficient for single-user local use. To enable full time-series trend tracking and trajectory forecasting, configure a PostgreSQL database with the TimescaleDB extension.

### With Docker (recommended)

The included Docker Compose file sets up the full stack automatically:

```bash
# Clone the repository
git clone https://github.com/hari715om/entropy-tracker.git
cd entropy-tracker

# Start PostgreSQL + TimescaleDB + Redis + API
docker compose up -d

# Point the CLI at the Docker database
export DATABASE_URL="postgresql://postgres:entropy@localhost:5433/entropy"
```

### With an existing PostgreSQL instance

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE entropy;"

# Set the connection string
export DATABASE_URL="postgresql://user:password@localhost:5432/entropy"

# Run migrations
entropy init ./my-repo   # migrations run automatically on first init
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite (local file) | PostgreSQL connection string for full time-series history |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection for Celery background scheduler |

On Windows, set environment variables with:

```powershell
$env:DATABASE_URL = "postgresql://postgres:entropy@localhost:5433/entropy"
```

On Linux/macOS:

```bash
export DATABASE_URL="postgresql://postgres:entropy@localhost:5433/entropy"
```

To make these permanent, add them to your shell profile (`~/.bashrc`, `~/.zshrc`, or `$PROFILE` on Windows).

---

## Supported Project Layouts

Entropy automatically detects the following Python project structures:

| Layout | Detection | Example |
|--------|-----------|---------|
| Flat | `*.py` at root | `my_module.py` |
| Package | `package/__init__.py` | `myapp/core.py` |
| Src layout | `src/package/` | `src/myapp/core.py` |
| Monorepo | Multiple packages | `services/api/`, `services/worker/` |

Dependency files are parsed in the following order: `uv.lock` → `poetry.lock` → `requirements.txt` → `pyproject.toml`.

---

## Troubleshooting

**`InvalidGitRepositoryError`**
The path you passed to `entropy init` does not contain a `.git` directory. Make sure you are pointing at the root of a git repository, not a subdirectory.

**`PyPI queries are slow on first scan`**
The first scan queries PyPI for each unique package in the codebase. Results are cached locally for 24 hours at `~/.entropy/pypi_cache/`. Subsequent scans are significantly faster.

**`Scan hangs on a large repository`**
Try a smaller repository first to confirm the tool is working. For very large repositories, the first scan can take 1–2 minutes. Django (2,900+ modules, 2,782 commits) completes in approximately 34 seconds.

**`ModuleNotFoundError` after install**
Run `pip install entropy-tracker` in the same Python environment you are calling `entropy` from. If you are using conda or a virtual environment, activate it first.

**`DATABASE_URL` connection refused**
If using Docker, ensure the containers are running with `docker compose ps`. If using a local PostgreSQL instance, check that the service is running and the credentials in your `DATABASE_URL` are correct.
