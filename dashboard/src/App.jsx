import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useParams, useNavigate, useLocation } from 'react-router-dom';
import Heatmap from './components/Heatmap';
import ModuleDetail from './components/ModuleDetail';
import TrendChart from './components/TrendChart';
import Landing from './components/Landing';
import { getRepos, getModules, getAlerts } from './api';

/* ─── Page fade wrapper: smooth transition between routes ─── */
function PageTransition({ children, dark }) {
  const location = useLocation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(false);
    const t = setTimeout(() => setVisible(true), 20);
    return () => clearTimeout(t);
  }, [location.pathname]);

  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transition: 'opacity 0.28s ease',
        minHeight: '100vh',
        background: dark ? '#0A0A0A' : '#FFFFFF',
        width: '100%',
      }}
    >
      {children}
    </div>
  );
}

/* ─── Dashboard-only Header ─── */
function Header() {
  return (
    <header className="header">
      <div className="header-brand">
        <Link to="/" style={{ textDecoration: 'none' }}>
          <div className="header-logo">ENTROPY</div>
        </Link>
        <div className="header-subtitle">Code Aging Tracker</div>
      </div>
      <nav className="header-nav" aria-label="Dashboard navigation">
        <Link to="/"     className="nav-link">Home</Link>
        <Link to="/demo" className="nav-link">Demo</Link>
        <Link to="/docs" className="nav-link">Docs</Link>
        <a href="/api/docs" className="nav-link" target="_blank" rel="noopener">API</a>
      </nav>
    </header>
  );
}

/* ─── Loading ─── */
function Loading({ text = 'Loading...' }) {
  return (
    <div className="loading-container">
      <div className="spinner" />
      <div className="loading-text">{text}</div>
    </div>
  );
}

/* ─── Severity helpers ─── */
function getSeverityColor(score) {
  if (score >= 85) return 'var(--critical)';
  if (score >= 70) return 'var(--high)';
  if (score >= 50) return 'var(--medium)';
  return 'var(--healthy)';
}

function getSeverityLabel(score) {
  if (score >= 85) return 'CRITICAL';
  if (score >= 70) return 'HIGH';
  if (score >= 50) return 'MEDIUM';
  return 'HEALTHY';
}

/* ─── Dashboard Page ─── */
function Dashboard() {
  const { repoId } = useParams();
  const [repos, setRepos]           = useState([]);
  const [modules, setModules]       = useState([]);
  const [alerts, setAlerts]         = useState([]);
  const [loading, setLoading]       = useState(true);
  const [activeRepo, setActiveRepo] = useState(repoId || null);
  const [view, setView]             = useState('heatmap');
  const [selectedModule, setSelectedModule] = useState(null);

  useEffect(() => {
    getRepos()
      .then(r => {
        setRepos(r);
        if (!activeRepo && r.length > 0) setActiveRepo(r[0].id);
      })
      .catch(() => setRepos([]));
  }, []);

  useEffect(() => {
    if (!activeRepo) { setLoading(false); return; }
    setLoading(true);
    Promise.all([getModules(activeRepo), getAlerts(activeRepo)])
      .then(([m, a]) => { setModules(m); setAlerts(a); })
      .catch(() => { setModules([]); setAlerts([]); })
      .finally(() => setLoading(false));
  }, [activeRepo]);

  const critical = modules.filter(m => m.entropy_score >= 85).length;
  const high     = modules.filter(m => m.entropy_score >= 70 && m.entropy_score < 85).length;
  const healthy  = modules.filter(m => m.entropy_score < 50).length;
  const avgScore = modules.length
    ? (modules.reduce((a, m) => a + m.entropy_score, 0) / modules.length).toFixed(1)
    : '--';

  if (loading) return <Loading text="Analyzing codebase..." />;

  if (!repos.length && !modules.length) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon" style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem', letterSpacing: '0.1em' }}>
          0 repos
        </div>
        <div className="empty-state-text">
          No repositories tracked yet. Use <code>entropy init ./repo</code> to add one.
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Repo Selector */}
      {repos.length > 0 && (
        <div className="repo-selector" role="tablist" aria-label="Repository selector">
          {repos.map(r => (
            <button
              key={r.id}
              role="tab"
              aria-selected={activeRepo === r.id}
              className={`repo-chip ${activeRepo === r.id ? 'active' : ''}`}
              onClick={() => setActiveRepo(r.id)}
            >
              {r.name}
            </button>
          ))}
        </div>
      )}

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="card">
          <div className="card-title">Average Entropy</div>
          <div className="card-value" style={{ color: getSeverityColor(parseFloat(avgScore) || 0) }}>
            {avgScore}
          </div>
          <div className="card-label">{modules.length} modules</div>
        </div>
        <div className="card">
          <div className="card-title">Critical</div>
          <div className="card-value severity-critical">{critical}</div>
          <div className="card-label">score &gt; 85</div>
        </div>
        <div className="card">
          <div className="card-title">High Risk</div>
          <div className="card-value severity-high">{high}</div>
          <div className="card-label">score 70-85</div>
        </div>
        <div className="card">
          <div className="card-title">Healthy</div>
          <div className="card-value severity-healthy">{healthy}</div>
          <div className="card-label">score &lt; 50</div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="header-nav" style={{ marginBottom: 'var(--sp-xl)' }}>
        {[
          { id: 'tab-heatmap', key: 'heatmap', label: 'Heatmap' },
          { id: 'tab-modules', key: 'modules',  label: 'Modules' },
          { id: 'tab-trend',   key: 'trend',    label: 'Trend' },
          { id: 'tab-alerts',  key: 'alerts',   label: `Alerts (${alerts.length})` },
        ].map(t => (
          <button
            key={t.key}
            id={t.id}
            className={`nav-link ${view === t.key ? 'active' : ''}`}
            onClick={() => { setView(t.key); setSelectedModule(null); }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Views */}
      {selectedModule ? (
        <div>
          <button
            className="nav-link"
            onClick={() => setSelectedModule(null)}
            style={{ marginBottom: 'var(--sp-lg)' }}
          >
            &larr; Back to {view}
          </button>
          <ModuleDetail module={selectedModule} repoId={activeRepo} />
        </div>
      ) : (
        <>
          {view === 'heatmap' && (
            <section className="section">
              <h2 className="section-title">Entropy Heatmap</h2>
              <Heatmap modules={modules} onSelect={setSelectedModule} />
            </section>
          )}

          {view === 'modules' && (
            <section className="section">
              <h2 className="section-title">All Modules -- Sorted by Entropy</h2>
              <div className="card" style={{ padding: 0, overflow: 'auto' }}>
                <table className="module-table">
                  <thead>
                    <tr>
                      <th>Module</th>
                      <th>Score</th>
                      <th>Knowledge</th>
                      <th>Deps</th>
                      <th>Churn</th>
                      <th>Age</th>
                      <th>Blast</th>
                      <th>Bus</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modules.map(m => (
                      <tr
                        key={m.module_path}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedModule(m)}
                      >
                        <td className="module-path">{m.module_path}</td>
                        <td className="score-cell" style={{ color: getSeverityColor(m.entropy_score) }}>
                          {m.entropy_score.toFixed(0)}
                        </td>
                        <td className="numeric">{m.knowledge_score?.toFixed(0) ?? '--'}</td>
                        <td className="numeric">{m.dep_score?.toFixed(0)       ?? '--'}</td>
                        <td className="numeric">{m.churn_score?.toFixed(0)     ?? '--'}</td>
                        <td className="numeric">{m.age_score?.toFixed(0)       ?? '--'}</td>
                        <td className="numeric">{m.blast_radius               ?? '--'}</td>
                        <td className="numeric">{m.bus_factor                 ?? '--'}</td>
                        <td>
                          <span className={`severity-badge ${getSeverityLabel(m.entropy_score).toLowerCase()}`}>
                            {getSeverityLabel(m.entropy_score)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {view === 'trend' && (
            <section className="section">
              <h2 className="section-title">Repo Health Over Time</h2>
              <div className="card">
                <TrendChart repoId={activeRepo} />
              </div>
            </section>
          )}

          {view === 'alerts' && (
            <section className="section">
              <h2 className="section-title">Active Alerts</h2>
              {alerts.length === 0 ? (
                <div className="empty-state">
                  <div
                    className="empty-state-icon"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem', letterSpacing: '0.1em', color: 'var(--healthy)' }}
                  >
                    OK
                  </div>
                  <div className="empty-state-text">No active alerts. Codebase is in good shape.</div>
                </div>
              ) : (
                alerts.map(a => (
                  <div key={a.id} className="alert-item">
                    <div className={`alert-dot ${a.severity?.toLowerCase()}`} />
                    <div className="alert-message">{a.message}</div>
                    <span className={`severity-badge ${a.severity?.toLowerCase()}`}>{a.severity}</span>
                    <div className="alert-time">
                      {a.fired_at ? new Date(a.fired_at).toLocaleDateString() : ''}
                    </div>
                  </div>
                ))
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

/* ─── Docs Page ─── */
const DOC_SECTIONS = [
  { id: '01', title: 'Introduction',      anchor: 'introduction' },
  { id: '02', title: 'Installation',      anchor: 'installation' },
  { id: '03', title: 'CLI Reference',     anchor: 'cli-reference' },
  { id: '04', title: 'Configuration',     anchor: 'configuration' },
  { id: '05', title: 'CI Integration',    anchor: 'ci-integration' },
  { id: '06', title: 'API and Dashboard', anchor: 'api-dashboard' },
  { id: '07', title: 'How It Works',      anchor: 'how-it-works' },
];

function DocsPage() {
  const [active, setActive] = useState('introduction');

  const sectionContent = {
    introduction: (
      <>
        <h1>Introduction</h1>
        <p>
          Entropy is a static analysis and git mining pipeline that converts a bare git
          repository into a per-module decay score from 0 to 100. It exposes that score as
          a CLI tool, a REST API, a CI gate, and a GitHub Marketplace Action -- without
          requiring any database, cloud service, or API key.
        </p>
        <p>
          The score combines four signals: knowledge decay (which engineers still understand
          each module), dependency drift (how far behind your packages are), churn patterns
          (chaotic edits vs deliberate refactors), and age since the last intentional
          structural change. Each signal has a weight derived from its reversibility and
          business impact.
        </p>
        <div className="docs-code-block">
{`# The four-signal scoring formula
entropy_score = (
  knowledge_score * 0.35   # lost knowledge is irreversible
  + dep_score     * 0.30   # CVEs and drift: measurable, immediate
  + churn_score   * 0.20   # invisible debt accumulation
  + age_score     * 0.15   # time since last deliberate attention
)`}
        </div>
        <p>
          A score above 85 is CRITICAL. A score above 70 is HIGH. A score above 50
          warrants monitoring. Below 50 is healthy.
        </p>
        <p>
          Entropy works on Python and JavaScript/TypeScript repositories. Python repos
          get all four signals including an AST-based import graph and blast radius
          calculation. JS/TS repos get three signals (knowledge, churn, dependency drift)
          via the NPM registry.
        </p>
      </>
    ),
    installation: (
      <>
        <h1>Installation</h1>
        <p>Requires Python 3.9 or later and git installed on your machine. No external services needed.</p>
        <div className="docs-code-block">
{`$ pip install entropy-tracker
$ entropy --version
entropy-tracker 1.0.5`}
        </div>
        <p>Scan any local git repository immediately after install:</p>
        <div className="docs-code-block">
{`$ entropy scan ./my-repo
$ entropy report --top 10`}
        </div>
        <p>For the REST API and web dashboard, install server dependencies:</p>
        <div className="docs-code-block">
{`$ pip install entropy-tracker[server]
$ entropy server
# Dashboard available at http://localhost:8000`}
        </div>
        <p>Using Docker:</p>
        <div className="docs-code-block">
{`docker pull hari715om/entropy-tracker:latest
docker run -p 8000:8000 hari715om/entropy-tracker`}
        </div>
      </>
    ),
    'cli-reference': (
      <>
        <h1>CLI Reference</h1>
        <p>
          All commands return a Rich terminal table by default.
          Pass <code>--format json</code> for machine-readable output or <code>--format html</code> for a full report.
        </p>
        <div className="docs-code-block">
{`entropy scan ./repo
  Runs the full four-stage pipeline on a local repo.
  Output: per-module scores sorted by entropy, descending.

entropy report --top 10
  Prints the top N highest-entropy modules.
  --top 10        Show top 10 (default: 20)
  --format html   Write HTML report to disk

entropy inspect path/to/module.py
  Deep breakdown of one module: all four signal scores,
  bus factor, blast radius, author list.

entropy diff . --base main --fail-above 75
  Compares current branch to base. Used in CI.
  --base main     The branch to compare against
  --fail-above N  Exit code 1 if any file exceeds N

entropy simulate --author-leaves alice@example.com
  What-if: which files become single points of failure
  if this engineer leaves the team.

entropy alerts --repo ./repo
  Fires and prints all active alerts based on rules.

entropy server
  Starts the FastAPI REST API + React dashboard.
  Default port: 8000`}
        </div>
      </>
    ),
    configuration: (
      <>
        <h1>Configuration</h1>
        <p>
          Place <code>entropy.toml</code> in your repo root to override defaults.
          All fields are optional -- entropy works with zero configuration.
        </p>
        <div className="docs-code-block">
{`[scoring.weights]
knowledge   = 0.35   # must sum to 1.0
dependency  = 0.30
churn       = 0.20
age         = 0.15

[scoring.thresholds]
critical    = 85
high        = 70
watch       = 50

[analysis]
active_window_days = 180   # how long ago counts as "active" author
history_years      = 3     # git log window in years
max_files_blame    = 400   # cap for parallel git blame calls

[alerts]
webhook_url = ""           # Slack/Discord webhook for alert posting`}
        </div>
        <p>
          The <code>active_window_days</code> controls what "active author" means.
          An engineer who committed 7 months ago is not active by default.
          Reduce this to 90 for stricter bus factor calculations.
        </p>
      </>
    ),
    'ci-integration': (
      <>
        <h1>CI Integration</h1>
        <p>
          Add the entropy-action to any GitHub Actions workflow. It installs entropy,
          runs a diff against your base branch, and exits with code 1 if any changed file
          exceeds your threshold. GitHub Actions reads the exit code and marks the PR
          check as failed -- blocking the merge.
        </p>
        <div className="docs-code-block">
{`# .github/workflows/entropy.yml
name: Entropy Gate
on: [pull_request]

jobs:
  entropy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0      # full history required
      - uses: hari715om/entropy-action@v1
        with:
          base-branch: main
          fail-above: 75`}
        </div>
        <p>
          The <code>fetch-depth: 0</code> is required. Without it, GitHub's shallow clone
          gives entropy less than 50 commits to analyze, producing inaccurate scores.
        </p>
        <p>For pre-commit hooks:</p>
        <div className="docs-code-block">
{`# .pre-commit-config.yaml
repos:
  - repo: https://github.com/hari715om/entropy-tracker
    rev: v1.0.5
    hooks:
      - id: entropy-diff
        args: [--fail-above, "80"]`}
        </div>
      </>
    ),
    'api-dashboard': (
      <>
        <h1>API and Dashboard</h1>
        <p>
          Start the REST API with <code>entropy server</code>. FastAPI auto-docs
          are at <code>/api/docs</code> (Swagger UI) and <code>/api/redoc</code> (ReDoc).
        </p>
        <div className="docs-code-block">
{`GET  /api/repos
  Returns list of all tracked repos with last-scan metadata.

POST /api/repos
  Body: { "path": "/absolute/path/to/repo" }
  Registers and runs a full scan. Returns repo_id.

GET  /api/repos/{id}/modules
  All module scores for a repo, sorted by entropy descending.

GET  /api/repos/{id}/alerts
  Active alerts for a repo (CRITICAL / HIGH / WATCH).

GET  /api/repos/{id}/trend?days=365
  Historical average entropy scores, one row per scan.

GET  /api/modules/{id}/detail
  Deep breakdown of one module including forecast data.

GET  /health
  Returns { "status": "ok" } -- for load balancer liveness checks.`}
        </div>
        <p>
          All endpoints return JSON. Authentication is not required for the local
          dashboard. For production deployment, place nginx with basic auth in front.
        </p>
      </>
    ),
    'how-it-works': (
      <>
        <h1>How It Works</h1>
        <p>
          Entropy is a four-stage data pipeline. Each stage produces a typed dict
          keyed on file path. The scorer merges all four dicts and applies the
          weighted formula.
        </p>
        <div className="docs-code-block">
{`Stage 1  GitAnalyzer
  Single "git log --numstat" subprocess call.
  Parses: authors, commit dates, churn vs refactor classification.
  Output: dict[path, FileGitData]

Stage 2  DepAnalyzer (Python) / NpmAnalyzer (JS)
  Async HTTP to PyPI / NPM registry.
  asyncio.Semaphore(10) -- rate limited, 24h local cache.
  Output: dict[path, FileDepData]

Stage 3  ASTAnalyzer
  Python AST import graph via ast.parse().
  BFS on reverse edge map for blast radius.
  Output: ImportGraphData { blast_radius: { path -> int } }

Stage 4  EntropyScorer
  Merges all three dicts per file path.
  Applies weighted formula.
  Bus factor: ThreadPoolExecutor(8) parallel git blame,
  capped at 400 files.
  Output: dict[path, ModuleScore]`}
        </div>
        <p>
          The single <code>git log</code> call is the critical performance decision.
          PyDriller (the common alternative) allocates a Python object per commit.
          On boto3 with 15k commits that costs 4 minutes and gigabytes of memory.
          The raw subprocess approach parses a single string with <code>str.split()</code>,
          reducing scan time to 18 seconds on the same repo.
        </p>
        <p>
          Commit classification distinguishes churn from refactors by examining
          net line change and files touched per commit. A refactor moves code around
          (low net change, touches many files). A churn commit adds hundreds of lines
          to fix bugs with high net change.
        </p>
      </>
    ),
  };

  return (
    <div className="docs-page">
      {/* Sidebar */}
      <aside aria-label="Documentation sections">
        <p className="docs-sidebar-title">Documentation</p>
        <ul className="docs-sidebar-list">
          {DOC_SECTIONS.map(s => (
            <li key={s.id} className="docs-sidebar-item">
              <button
                className={`docs-sidebar-link ${active === s.anchor ? 'active' : ''}`}
                onClick={() => setActive(s.anchor)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  width: '100%',
                  textAlign: 'left',
                  fontFamily: 'var(--font-sans)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                }}
              >
                <span style={{ color: 'var(--dash-text-3)', fontFamily: 'var(--font-mono)', fontSize: '0.68rem', flexShrink: 0 }}>
                  {s.id}
                </span>
                {s.title}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Content */}
      <div className="docs-content">
        <div className="docs-banner">
          Source docs also available at{' '}
          <a href="https://github.com/hari715om/entropy-tracker/tree/main/docs" target="_blank" rel="noopener noreferrer">
            github.com/hari715om/entropy-tracker
          </a>
        </div>
        {sectionContent[active]}
      </div>
    </div>
  );
}

/* ─── App ─── */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing -- white, own nav, own background */}
        <Route
          path="/"
          element={
            <PageTransition dark={false}>
              <Landing />
            </PageTransition>
          }
        />

        {/* Dashboard -- full-bleed dark shell */}
        <Route
          path="/demo"
          element={
            <PageTransition dark={true}>
              <div className="app-container dashboard-mode">
                <Header />
                <Dashboard />
              </div>
            </PageTransition>
          }
        />
        <Route
          path="/demo/:repoId"
          element={
            <PageTransition dark={true}>
              <div className="app-container dashboard-mode">
                <Header />
                <Dashboard />
              </div>
            </PageTransition>
          }
        />

        {/* Docs -- full-bleed dark shell */}
        <Route
          path="/docs"
          element={
            <PageTransition dark={true}>
              <div className="app-container dashboard-mode">
                <Header />
                <DocsPage />
              </div>
            </PageTransition>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
