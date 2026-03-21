"""
Git Analyzer — extracts decay signals from git history.

Performance-optimized:
- Commits are bounded to a configurable window (default: MAX_COMMIT_MONTHS)
- Per-commit errors (e.g. shallow clones, binary diffs) are skipped gracefully
- Live progress shows commit counters so users can see progress on large repos
"""

from __future__ import annotations

import logging
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from entropy.config import AnalysisConfig, get_config

logger = logging.getLogger(__name__)

# Cap how far back we walk to keep scans fast on repos with 10k+ commits.
# 3 years of history is enough to capture knowledge and churn signals.
MAX_COMMIT_MONTHS = 36


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileGitData:
    """Aggregated git data for a single file."""

    path: str
    authors_all_time: set[str] = field(default_factory=set)
    authors_active: set[str] = field(default_factory=set)
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    last_refactor_commit: datetime | None = None
    churn_commits: int = 0
    refactor_commits: int = 0
    total_commits: int = 0
    lines_added_total: int = 0
    lines_deleted_total: int = 0
    # For bus factor: author → lines in last blame
    author_line_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def months_since_refactor(self) -> float:
        """Months since the last refactor commit (or first commit if never refactored)."""
        ref_date = self.last_refactor_commit or self.first_commit
        if ref_date is None:
            return 0.0
        now = datetime.now(timezone.utc)
        if ref_date.tzinfo is None:
            ref_date = ref_date.replace(tzinfo=timezone.utc)
        delta = now - ref_date
        return delta.days / 30.44

    def to_dict(self) -> dict[str, Any]:
        fmt = "%Y-%m-%d"
        return {
            "path": self.path,
            "authors_all_time": sorted(self.authors_all_time),
            "authors_active": sorted(self.authors_active),
            "first_commit": self.first_commit.strftime(fmt) if self.first_commit else None,
            "last_commit": self.last_commit.strftime(fmt) if self.last_commit else None,
            "last_refactor_commit": (
                self.last_refactor_commit.strftime(fmt) if self.last_refactor_commit else None
            ),
            "churn_commits": self.churn_commits,
            "refactor_commits": self.refactor_commits,
            "total_commits": self.total_commits,
            "months_since_refactor": round(self.months_since_refactor, 1),
        }


# ---------------------------------------------------------------------------
# Commit classification helpers
# ---------------------------------------------------------------------------

# Thresholds for commit classification
CHURN_TOTAL_THRESHOLD = 200    # total lines touched (added + deleted) — above this is always churn
REFACTOR_NET_THRESHOLD = 10    # net lines changed — below this is a candidate for refactor
REFACTOR_MAX_TOTAL = 200       # refactors can't be massive rewrites


def _classify_commit(added: int, deleted: int, files_touched: int) -> tuple[bool, bool]:
    """
    Classify a commit as churn and/or refactor.

    Returns (is_churn, is_refactor) — both can be True in theory,
    but a massive total change always wins as churn.

    Rules:
    * total > CHURN_TOTAL_THRESHOLD              → churn  (massive rewrite)
    * net < REFACTOR_NET_THRESHOLD  AND          → refactor (structural move)
      total < REFACTOR_MAX_TOTAL AND files > 1
    * everything else                            → churn
    """
    total = added + deleted
    net = abs(added - deleted)

    is_churn = total > CHURN_TOTAL_THRESHOLD
    is_refactor = (
        not is_churn
        and net < REFACTOR_NET_THRESHOLD
        and total < REFACTOR_MAX_TOTAL
        and files_touched > 1
    )
    # Fallthrough: large net with smaller total is still churn
    if not is_churn and not is_refactor:
        is_churn = True
    return is_churn, is_refactor


# Keep legacy wrappers for any external callers
def _is_churn_commit(added: int, deleted: int, churn_threshold: int) -> bool:
    """Legacy wrapper — use _classify_commit in new code."""
    return _classify_commit(added, deleted, 1)[0]


def _is_refactor_commit(added: int, deleted: int, files_touched: int, refactor_threshold: int) -> bool:
    """Legacy wrapper — use _classify_commit in new code."""
    return _classify_commit(added, deleted, files_touched)[1]


def _normalize_path(path: str) -> str:
    """Normalize file path separators to forward slashes for cross-platform consistency."""
    return path.replace("\\", "/")


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

class GitAnalyzer:
    """Analyze a git repository and extract per-file decay signals."""

    def __init__(self, repo_path: str | Path, config: AnalysisConfig | None = None):
        self.repo_path = str(repo_path)
        self.cfg = config or get_config().analysis
        self._cutoff = datetime.now(timezone.utc) - timedelta(days=self.cfg.active_author_window_days)
        # Only walk last MAX_COMMIT_MONTHS of commits
        self._since = datetime.now(timezone.utc) - timedelta(days=MAX_COMMIT_MONTHS * 30)
        self._file_data: dict[str, FileGitData] = {}
        self._global_active_authors: set[str] = set()
        # Pre-count commits in window for progress display (fast git call)
        since_str = self._since.strftime("%Y-%m-%d")
        self._total_commits: int = self._count_commits(since_str)
        self._using_full_history: bool = False  # set True if fallback fires

    def _count_commits(self, since_str: str | None = None) -> int:
        """Quickly count commits in the analysis window using git rev-list."""
        cmd = ["git", "rev-list", "--count", "HEAD"]
        if since_str:
            cmd.insert(3, f"--since={since_str}")
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                return int(result.stdout.strip())
        except Exception:
            pass
        return 0  # unknown — will show counter without total

    # ---- public API --------------------------------------------------------

    def analyze(self, progress_callback=None) -> dict[str, FileGitData]:
        """
        Walk commits in the repo and build per-file git data.
        
        Parameters
        ----------
        progress_callback : optional callable(commit_count, file_count, message)
            Called after every 100 commits so CLI can show live progress.
        
        Returns a dict of ``{file_path: FileGitData}``.
        """
        logger.info("GitAnalyzer: scanning %s (since %s) …", self.repo_path, self._since.strftime("%Y-%m"))
        self._file_data.clear()
        self._global_active_authors.clear()

        try:
            since_str = self._since.strftime("%Y-%m-%d")
            raw_log = self._fetch_raw_log(self.repo_path, since_str)
            self._parse_log(raw_log, progress_callback)

            # Fallback: if the window returned nothing (e.g. deprecated/abandoned repo),
            # re-run without a date filter so we still get meaningful decay signals.
            if not self._file_data:
                logger.warning(
                    "GitAnalyzer: 0 files found in 36-month window — falling back to full history."
                )
                self._using_full_history = True
                self._total_commits = self._count_commits()  # total without date filter
                raw_log = self._fetch_raw_log(self.repo_path, since_date=None)
                self._parse_log(raw_log, progress_callback)
            
            if progress_callback:
                progress_callback(self._total_commits, self._total_commits, len(self._file_data))

            logger.info(
                "GitAnalyzer: processed %d commits, found %d files",
                self._total_commits, len(self._file_data),
            )

        except Exception:
            logger.exception("GitAnalyzer: failed to scan %s", self.repo_path)
            raise

        return self._file_data

    def _fetch_raw_log(self, repo_path: str, since_date: str | None) -> str:
        """Single git log call — replaces entire PyDriller walk."""
        cmd = [
            'git', '-C', repo_path, 'log',
            '--format=COMMIT|%H|%ae|%ai',
            '--numstat',
            '--no-merges',
            '--diff-filter=AM',  # only Added/Modified files
        ]
        if since_date:
            cmd.insert(4, f'--since={since_date}')
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"git log failed: {result.stderr}")
        return result.stdout

    def _parse_log(self, raw: str, progress_callback=None) -> None:
        """
        Parse git log --numstat output into per-file data.
        """
        commits = raw.split('COMMIT|')
        commit_count = 0
        
        for chunk in commits:
            if not chunk.strip():
                continue
                
            commit_count += 1
            lines = chunk.strip().splitlines()
            if not lines:
                continue
                
            header_parts = lines[0].split('|', 2)
            if len(header_parts) < 3:
                continue
                
            current_author = header_parts[1].strip()
            date_str = header_parts[2].strip()
            
            try:
                current_date = datetime.fromisoformat(date_str)
            except ValueError:
                continue
                
            if current_date.tzinfo is None:
                current_date = current_date.replace(tzinfo=timezone.utc)
                
            if current_date > self._cutoff:
                self._global_active_authors.add(current_author)
                
            file_changes = []
            for line in lines[1:]:
                if '\t' not in line or not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 3:
                    file_changes.append(parts)
                    
            files_touched = len(file_changes)
            
            for parts in file_changes:
                added_str, deleted_str, raw_filepath = parts[0], parts[1], parts[2]
                
                if added_str == '-' or deleted_str == '-':
                    continue
                    
                try:
                    added = int(added_str)
                    deleted = int(deleted_str)
                except ValueError:
                    continue
                    
                filepath = _normalize_path(raw_filepath)
                if not filepath.endswith('.py'):
                    continue
                    
                fd = self._get_or_create(filepath)
                fd.authors_all_time.add(current_author)
                fd.total_commits += 1
                fd.lines_added_total += added
                fd.lines_deleted_total += deleted
                fd.author_line_counts[current_author] += added
                
                if current_date > self._cutoff:
                    fd.authors_active.add(current_author)
                    
                if fd.first_commit is None or current_date < fd.first_commit:
                    fd.first_commit = current_date
                if fd.last_commit is None or current_date > fd.last_commit:
                    fd.last_commit = current_date
                    
                is_churn, is_refactor = _classify_commit(added, deleted, files_touched)

                if is_churn:
                    fd.churn_commits += 1
                    
                if is_refactor:
                    fd.refactor_commits += 1
                    if fd.last_refactor_commit is None or current_date > fd.last_refactor_commit:
                        fd.last_refactor_commit = current_date
            
            if progress_callback and commit_count % 100 == 0:
                progress_callback(commit_count, self._total_commits, len(self._file_data))
                
        self._total_commits = max(self._total_commits, commit_count)

    def compute_bus_factor(self, file_path: str) -> int:
        """
        Bus factor for a file: number of *active* authors who contributed ≥10% of lines.
        Falls back to counting any committer if no active authors are found.
        """
        # Try both normalized and original path
        normalized = _normalize_path(file_path)
        fd = self._file_data.get(normalized) or self._file_data.get(file_path)

        result = subprocess.run([
            'git', '-C', self.repo_path, 'blame',
            '--line-porcelain', file_path
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        
        if result.returncode != 0:
            return max(len(fd.authors_active) if fd and fd.authors_active else len(fd.authors_all_time) if fd else 1, 1)

        author_lines = {}
        for line in result.stdout.splitlines():
            if line.startswith('author-mail '):
                parts = line.split(' ', 1)
                if len(parts) > 1:
                    email = parts[1].strip('<>')
                    author_lines[email] = author_lines.get(email, 0) + 1
                    
        total = sum(author_lines.values())
        if total == 0:
            return 1

        significant_active = sum(
            1 for author, lines in author_lines.items()
            if (lines / total) > 0.10 and (fd is None or author in (fd.authors_active or fd.authors_all_time))
        )
        return max(significant_active, 1)  # Always at least 1

    # ---- internal ----------------------------------------------------------

    def _get_or_create(self, path: str) -> FileGitData:
        if path not in self._file_data:
            self._file_data[path] = FileGitData(path=path)
        return self._file_data[path]
