import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

/* ─────────────────────────────────────────────────────────────
   Terminal animation data
   ───────────────────────────────────────────────────────────── */
const TERMINAL_LINES = [
  { type: 'cmd',      text: '$ pip install entropy-tracker',                          delay: 300 },
  { type: 'success',  text: 'Successfully installed entropy-tracker-1.0.5',           delay: 500 },
  { type: 'out',      text: '',                                                        delay: 100 },
  { type: 'cmd',      text: '$ entropy scan ./boto',                                  delay: 600 },
  { type: 'out',      text: 'Scanning boto... analyzing 938 modules',                 delay: 300 },
  { type: 'bar',      text: '[####################] 100%  done in 18s',               delay: 1200 },
  { type: 'out',      text: '',                                                        delay: 100 },
  { type: 'out',      text: 'MODULE                           SCORE  BUS  SEVERITY',   delay: 200 },
  { type: 'out',      text: '-------------------------------- -----  ---  ---------', delay: 100 },
  { type: 'critical', text: 'boto/s3/inject.py               91     1    CRITICAL',   delay: 200 },
  { type: 'high',     text: 'boto/session.py                 74     2    HIGH',       delay: 200 },
  { type: 'watch',    text: 'boto/resources/factory.py       58     3    WATCH',      delay: 200 },
  { type: 'watch',    text: 'boto/core/xform_name.py         52     2    WATCH',      delay: 200 },
  { type: 'out',      text: '',                                                        delay: 100 },
  { type: 'success',  text: '4 alerts fired  |  scan complete',                       delay: 200 },
];

const COLOR_MAP = {
  cmd:      'terminal-cmd',
  success:  'terminal-success',
  out:      'terminal-out',
  critical: 'terminal-critical',
  high:     'terminal-high',
  watch:    'terminal-watch',
  bar:      'terminal-bar-fill',
};

function TerminalWindow() {
  const [visibleLines, setVisibleLines] = useState([]);
  const [showCursor, setShowCursor] = useState(true);
  const hasAnimated = useRef(false);
  const containerRef = useRef(null);

  useEffect(() => {
    if (hasAnimated.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          runAnimation();
        }
      },
      { threshold: 0.3 }
    );
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  function runAnimation() {
    let accDelay = 0;
    TERMINAL_LINES.forEach((line, i) => {
      accDelay += line.delay;
      setTimeout(() => {
        setVisibleLines(prev => [...prev, line]);
      }, accDelay);
    });
    // Hide cursor after all lines
    const total = TERMINAL_LINES.reduce((s, l) => s + l.delay, 0) + 600;
    setTimeout(() => setShowCursor(false), total);
  }

  return (
    <div className="terminal-window" ref={containerRef}>
      <div className="terminal-bar">
        <div className="terminal-dot close" />
        <div className="terminal-dot min" />
        <div className="terminal-dot max" />
        <span className="terminal-bar-label">zsh -- macOS Sequoia</span>
      </div>
      <div className="terminal-body">
        {visibleLines.map((line, i) => (
          <span key={i} className={`terminal-line ${COLOR_MAP[line.type] || 'terminal-out'}`}>
            {line.text}
          </span>
        ))}
        {showCursor && <span className="terminal-cursor" />}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   Signals data
   ───────────────────────────────────────────────────────────── */
const SIGNALS = [
  {
    num: '01',
    name: 'Knowledge Decay',
    desc: 'Tracks which modules have lost the engineers who originally wrote them. Measures active author concentration over the last 180 days.',
    weight: '35%',
  },
  {
    num: '02',
    name: 'Dependency Drift',
    desc: 'Measures how far your pinned versions are behind the latest release, weighted by how fast each ecosystem moves and active CVE counts.',
    weight: '30%',
  },
  {
    num: '03',
    name: 'Churn Patterns',
    desc: 'Distinguishes chaotic bug-fix churn from deliberate architectural refactors by examining commit size, net line change, and files touched.',
    weight: '20%',
  },
  {
    num: '04',
    name: 'Age Since Refactor',
    desc: 'Time elapsed since the last deliberate structural change. Code that is only patched and never refactored accumulates silent risk.',
    weight: '15%',
  },
];

/* ─────────────────────────────────────────────────────────────
   Docs list
   ───────────────────────────────────────────────────────────── */
const DOCS = [
  { num: '01', name: 'Introduction',      desc: 'What entropy is, the four signals, and why each weight.' },
  { num: '02', name: 'Installation',      desc: 'pip install, Docker, and First scan in under 3 minutes.' },
  { num: '03', name: 'CLI Reference',     desc: 'Every command and flag with exact output examples.' },
  { num: '04', name: 'Configuration',     desc: 'entropy.toml options, custom weights, and thresholds.' },
  { num: '05', name: 'CI Integration',    desc: 'GitHub Actions, PR gate workflow, and pre-commit hooks.' },
  { num: '06', name: 'API and Dashboard', desc: 'All 7 REST endpoints, response shapes, and production deploy.' },
  { num: '07', name: 'How It Works',      desc: 'Architecture, the git log decision, scoring formula, and performance.' },
];

/* ─────────────────────────────────────────────────────────────
   Landing Component
   ───────────────────────────────────────────────────────────── */
export default function Landing() {
  return (
    <div className="landing-root">

      {/* ── Nav ── */}
      <nav className="land-nav" aria-label="Main navigation">
        <div className="land-nav-brand">
          <span className="land-nav-wordmark">Entropy</span>
          <span className="land-nav-tag">Code Aging Tracker</span>
        </div>
        <div className="land-nav-links">
          <a
            href="https://github.com/hari715om/entropy-tracker"
            target="_blank"
            rel="noopener noreferrer"
            className="land-nav-link"
          >
            GitHub
          </a>
          <Link to="/docs" className="land-nav-link">Docs</Link>
          <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="land-nav-link">API</a>
          <Link to="/demo" className="land-nav-cta">Live Demo</Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="land-hero" aria-labelledby="hero-heading">
        <div className="land-pill">For Engineering Teams</div>
        <h1 className="land-h1" id="hero-heading">
          Code ages.<br />
          <span className="land-h1-accent">Entropy measures it.</span>
        </h1>
        <p className="land-subtitle">
          A static analysis pipeline that converts git history, dependency drift,
          and knowledge loss into a single 0-100 decay score per module.
          No config. No cloud. Just answers.
        </p>
        <div className="land-cta-group">
          <Link to="/demo" className="land-btn-primary" id="hero-cta-demo">
            Explore Live Demo &rarr;
          </Link>
          <Link to="/docs" className="land-btn-secondary" id="hero-cta-docs">
            Read the Docs
          </Link>
        </div>
      </section>

      {/* ── Terminal Demo ── */}
      <div className="land-terminal-section" aria-label="Terminal demo">
        <TerminalWindow />
        <p className="land-terminal-caption">
          Runs on any Python or JS/TS repository. No API key. No account.
        </p>
      </div>

      <hr className="land-divider" />

      {/* ── Four Signals ── */}
      <section className="land-signals" aria-labelledby="signals-heading">
        <p className="land-section-label" id="signals-heading">Four Signals. One Score.</p>
        <div className="land-signals-grid" role="list">
          {SIGNALS.map(sig => (
            <div className="land-signal-item" key={sig.num} role="listitem">
              <span className="land-signal-num">{sig.num}</span>
              <div>
                <div className="land-signal-name">{sig.name}</div>
                <div className="land-signal-desc">{sig.desc}</div>
              </div>
              <span className="land-signal-weight">{sig.weight}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── CI Strip ── */}
      <section className="land-ci" aria-labelledby="ci-heading">
        <div className="land-ci-inner">
          <div className="land-ci-copy">
            <h2 id="ci-heading">
              Block merges that<br />
              <span style={{ fontStyle: 'italic' }}>spike decay.</span>
            </h2>
            <p>
              One YAML block in your GitHub Actions workflow. Every PR that pushes
              a module past your threshold gets blocked before it merges.
              Same mechanism as ESLint and pytest.
            </p>
            <Link to="/docs" className="land-btn-secondary" style={{ display: 'inline-flex' }}>
              View CI Docs &rarr;
            </Link>
          </div>
          <div className="land-ci-code" role="code" aria-label="GitHub Actions YAML snippet">
            <span className="yaml-comment"># .github/workflows/entropy.yml</span>{'\n'}
            <span className="yaml-key">- uses</span>: <span className="yaml-val">hari715om/entropy-action@v1</span>{'\n'}
            {'  '}<span className="yaml-key">with</span>:{'\n'}
            {'    '}<span className="yaml-key">base-branch</span>: <span className="yaml-val">main</span>{'\n'}
            {'    '}<span className="yaml-key">fail-above</span>: <span className="yaml-val">75</span>
          </div>
        </div>
      </section>

      {/* ── Docs Strip ── */}
      <section className="land-docs" aria-labelledby="docs-heading">
        <div className="land-docs-inner">
          <h2 className="land-docs-title" id="docs-heading">Documentation</h2>
          <ul className="land-docs-list" aria-label="Documentation sections">
            {DOCS.map(doc => (
              <li className="land-doc-item" key={doc.num}>
                <Link to="/docs" className="land-doc-link" id={`doc-link-${doc.num}`}>
                  <div className="land-doc-meta">
                    <span className="land-doc-num">{doc.num}</span>
                    <div>
                      <div className="land-doc-name">{doc.name}</div>
                      <div className="land-doc-desc">{doc.desc}</div>
                    </div>
                  </div>
                  <span className="land-doc-arrow" aria-hidden="true">&rarr;</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="land-footer" role="contentinfo">
        <div className="land-footer-inner">
          <span className="land-footer-wordmark">Entropy</span>
          <nav className="land-footer-links" aria-label="Footer links">
            <a
              href="https://github.com/hari715om/entropy-tracker"
              target="_blank"
              rel="noopener noreferrer"
              className="land-footer-link"
            >
              GitHub
            </a>
            <a
              href="https://pypi.org/project/entropy-tracker/"
              target="_blank"
              rel="noopener noreferrer"
              className="land-footer-link"
            >
              PyPI
            </a>
            <Link to="/docs" className="land-footer-link">Docs</Link>
            <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="land-footer-link">
              API
            </a>
          </nav>
          <span className="land-footer-copy">entropy-tracker v1.0.5</span>
        </div>
      </footer>

    </div>
  );
}
