# API & Dashboard

Entropy includes a FastAPI backend and React dashboard for teams that want continuous background monitoring, a visual interface, or programmatic integration with internal tooling.

---

## Starting the Stack

### With Docker (recommended for production)

```bash
# Development stack — hot reload, local volumes
docker compose up

# Production stack — Nginx, SSL-ready
docker compose -f docker-compose.prod.yml up -d
```

Services started:

| Service | Port | Description |
|---------|------|-------------|
| FastAPI | 8000 | REST API + serves dashboard static files |
| PostgreSQL + TimescaleDB | 5433 | Time-series scan history |
| Redis | 6379 | Celery task queue |
| Celery worker | — | Background daily scan scheduler |
| Nginx (prod only) | 80, 443 | Reverse proxy + SSL termination |

### Without Docker

```bash
# Start just the API server
entropy server

# API docs available at:
http://localhost:8000/api/docs

# Dashboard available at:
http://localhost:8000
```

---

## REST API Reference

All endpoints are prefixed with `/api/`. Interactive documentation with try-it-out is available at `/api/docs` when the server is running.

---

### Repositories

#### `POST /api/repos`
Register a new repository for tracking.

**Request body:**
```json
{
  "name": "my-service",
  "path": "/path/to/repo"
}
```

**Response:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "my-service",
  "path": "/path/to/repo",
  "created_at": "2024-06-01T10:00:00Z"
}
```

---

#### `GET /api/repos`
List all tracked repositories with their latest entropy summary.

**Response:**
```json
[
  {
    "id": "3fa85f64...",
    "name": "my-service",
    "last_scan": "2024-06-01T10:00:00Z",
    "modules_scanned": 47,
    "critical_count": 3,
    "high_count": 8,
    "avg_score": 54.2
  }
]
```

---

#### `POST /api/repos/{id}/scan`
Trigger an immediate re-scan outside the daily schedule.

**Response:**
```json
{
  "status": "completed",
  "modules_scanned": 47,
  "critical_count": 3,
  "high_count": 8,
  "alerts_fired": 11
}
```

---

### Modules

#### `GET /api/repos/{id}/modules`
All modules for a repository, sorted by entropy score descending.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `top` | integer | 50 | Limit results to the N highest-scoring modules |
| `severity` | string | — | Filter by severity: `CRITICAL`, `HIGH`, `MEDIUM`, `HEALTHY` |
| `min_blast` | integer | — | Filter to modules with blast radius >= this value |

**Example:**
```bash
curl "http://localhost:8000/api/repos/{id}/modules?top=10&severity=CRITICAL"
```

**Response:**
```json
[
  {
    "module_path": "payments/gateway.py",
    "entropy_score": 94.0,
    "knowledge_score": 85.0,
    "dep_score": 100.0,
    "churn_score": 100.0,
    "age_score": 96.0,
    "blast_radius": 12,
    "bus_factor": 1,
    "severity": "CRITICAL",
    "trend_per_month": 3.2,
    "scanned_at": "2024-06-01T10:00:00Z"
  }
]
```

---

#### `GET /api/repos/{id}/modules/{module_path}`
Full detail for a single module: signal breakdown, 90-day score history, and 30/60/90-day forecast.

**Example:**
```bash
curl "http://localhost:8000/api/repos/{id}/modules/payments/gateway.py"
```

**Response:**
```json
{
  "module_path": "payments/gateway.py",
  "entropy_score": 94.0,
  "knowledge_score": 85.0,
  "dep_score": 100.0,
  "churn_score": 100.0,
  "age_score": 96.0,
  "blast_radius": 12,
  "bus_factor": 1,
  "severity": "CRITICAL",
  "trend_per_month": 3.2,
  "forecast": {
    "days_30": 97.0,
    "days_60": 99.0,
    "days_90": 100.0,
    "estimated_unmaintainable_days": 95
  },
  "history": [
    { "time": "2024-03-01T00:00:00Z", "score": 81.0 },
    { "time": "2024-04-01T00:00:00Z", "score": 84.2 },
    { "time": "2024-05-01T00:00:00Z", "score": 87.1 },
    { "time": "2024-06-01T00:00:00Z", "score": 94.0 }
  ]
}
```

---

### Alerts

#### `GET /api/repos/{id}/alerts`
Active alerts for a repository — modules that have crossed a threshold or are trending rapidly.

**Response:**
```json
[
  {
    "id": "abc-123",
    "module_path": "payments/gateway.py",
    "severity": "CRITICAL",
    "message": "entropy_score > 85",
    "fired_at": "2024-06-01T10:00:00Z",
    "resolved": false
  }
]
```

---

### Trend

#### `GET /api/repos/{id}/trend`
Repository-level average entropy score over time. Requires TimescaleDB and multiple scans.

**Query parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `days` | `90` | Number of days of history to return |

**Response:**
```json
[
  { "time": "2024-03-01T00:00:00Z", "avg_score": 48.2 },
  { "time": "2024-04-01T00:00:00Z", "avg_score": 49.8 },
  { "time": "2024-05-01T00:00:00Z", "avg_score": 51.3 },
  { "time": "2024-06-01T00:00:00Z", "avg_score": 54.2 }
]
```

---

## Dashboard

The React dashboard is served from the API root at `http://localhost:8000` (or your configured domain).

### Heatmap View
A treemap of the codebase where each box represents a module. Box size is proportional to lines of code. Color represents severity — red for Critical, orange for High, blue for Medium, green for Healthy. Click any cell to open the module detail panel.

### Modules View
A sortable, filterable table of all modules with score, severity, blast radius, bus factor, and trend. Use the search bar to find a specific file. Use the severity filter chips to focus on Critical and High modules.

### Trend View
A repository-level area chart showing average entropy over time. Requires multiple scans to populate. Shows whether the codebase as a whole is improving or degrading.

### Alerts View
Active alerts — modules that have crossed a threshold or are trending rapidly upward. Alerts include the specific rule that fired and the timestamp.

---

## Production Deployment

For deploying to a public server (e.g., `entropy.yourdomain.com`):

### 1. Provision a server
An e2-small instance (2 vCPU, 2GB RAM) on Google Cloud, DigitalOcean, or Hetzner is sufficient for a demo-scale deployment with 3–10 tracked repositories.

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com | sh
```

### 3. Clone and configure
```bash
git clone https://github.com/hari715om/entropy-tracker.git
cd entropy-tracker

# Set production credentials
cp .env.example .env
# Edit .env with your DB password and domain
```

### 4. Start the production stack
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 5. Configure SSL
```bash
certbot --nginx -d entropy.yourdomain.com
```

### 6. Pre-load demo data
```bash
# Inside the running container or on the host with DATABASE_URL set:
entropy init ./repos/demo-repo --name demo
entropy init ./repos/django --name django
```

After this, visitors to `entropy.yourdomain.com` see real data immediately without needing to install or configure anything.
