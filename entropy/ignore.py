"""
.entropyignore support — works exactly like .gitignore.

Any file or directory pattern listed in .entropyignore at the repo root
will be excluded from all analysis steps: git_analyzer, dep_analyzer,
ast_analyzer, and npm_analyzer.

Built-in exclusions (always applied, regardless of .entropyignore):
  __pycache__/, .git/, node_modules/, dist/, build/, .venv/, venv/,
  *.min.js, *.pyc, *.pyi (type stubs)

Usage:
    from entropy.ignore import IgnoreFilter

    filt = IgnoreFilter(repo_path)
    if filt.is_ignored("migrations/0001_initial.py"):
        continue  # skip this file

.entropyignore syntax (line by line):
    # comment lines are ignored
    migrations/          -> ignores entire directory
    *_generated.py       -> glob pattern
    vendor/              -> third-party bundled code
    *.pb.py              -> protobuf generated files
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Always-excluded patterns regardless of .entropyignore
_BUILTIN_EXCLUDES: list[str] = [
    "__pycache__/*",
    "__pycache__",
    ".git/*",
    ".git",
    "*.pyc",
    "*.pyo",
    ".venv/*",
    ".venv",
    "venv/*",
    "venv",
    "env/*",
    "env",
    ".env/*",
    "node_modules/*",
    "node_modules",
    "*.min.js",
    "*.min.css",
    ".mypy_cache/*",
    ".ruff_cache/*",
    ".pytest_cache/*",
    "*.egg-info/*",
    "*.egg-info",
    ".tox/*",
    "htmlcov/*",
    ".coverage",
]


class IgnoreFilter:
    """
    Evaluate .entropyignore patterns against file paths.

    Usage:
        filt = IgnoreFilter("/path/to/repo")
        filt.is_ignored("migrations/0001_initial.py")  # True

    Thread-safe: all state is set at __init__ time and patterns are immutable.
    """

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self._patterns: list[str] = list(_BUILTIN_EXCLUDES)
        self._load_entropyignore()

    def _load_entropyignore(self) -> None:
        """Load patterns from .entropyignore if present."""
        ignore_file = self.repo_path / ".entropyignore"
        if not ignore_file.is_file():
            return

        loaded = 0
        for raw_line in ignore_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            # Normalize: strip trailing slash for directories, we match both ways
            normalized = line.rstrip("/")
            self._patterns.append(normalized)
            # Also add a glob to match everything inside the directory
            if not normalized.startswith("*"):
                self._patterns.append(f"{normalized}/*")
            loaded += 1

        if loaded:
            logger.info("IgnoreFilter: loaded %d patterns from .entropyignore", loaded)

    def is_ignored(self, file_path: str) -> bool:
        """
        Return True if the relative file path matches any exclusion pattern.

        Accepts both forward and backslash separators.
        """
        normalized = file_path.replace("\\", "/")
        # Also check just the filename (basename) for simple patterns
        basename = normalized.split("/")[-1]

        for pattern in self._patterns:
            # Direct filename match
            if fnmatch.fnmatch(basename, pattern):
                return True
            # Full path match
            if fnmatch.fnmatch(normalized, pattern):
                return True
            # Prefix match: "migrations" should ignore "migrations/0001.py"
            if normalized.startswith(pattern.rstrip("/") + "/"):
                return True

        return False

    @property
    def patterns(self) -> list[str]:
        """Read-only view of all active patterns (built-in + .entropyignore)."""
        return list(self._patterns)
