"""
NPM Analyzer — measures dependency staleness for JavaScript/TypeScript repositories.

Mirrors the architecture of dep_analyzer.py exactly:
- Reads package.json (dependencies + devDependencies)
- Queries registry.npmjs.org concurrently with bounded concurrency (avoids rate limits)
- 24-hour local cache at ~/.entropy/npm_cache/ to keep repeat scans fast
- Returns {file_path: FileNpmData} mapping .js/.ts files to their dep risk scores

Git signals (knowledge decay, churn) are already language-agnostic and work on
.js/.ts files with zero changes. This module adds the fourth signal: dependency drift.

Usage:
    analyzer = NpmAnalyzer("/path/to/js-repo")
    results = analyzer.analyze()
    # results["src/api/client.ts"].dep_score -> 0-100
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

from entropy.ignore import IgnoreFilter

logger = logging.getLogger(__name__)

# Max concurrent NPM registry requests — keeps large monorepos safe from throttling.
# NPM registry allows ~100 req/s but we stay conservative to be a good citizen.
_NPM_CONCURRENCY = 20

# Cache TTL: 24 hours — NPM packages don't release that often
_CACHE_TTL = 86_400
_CACHE_DIR = Path.home() / ".entropy" / "npm_cache"

# NPM registry base URL
_NPM_REGISTRY = "https://registry.npmjs.org"

# Files we score for dep risk inside a JS/TS repo.
# We have no AST import graph (intentional — see module docstring),
# so every .js/.ts file in the repo inherits the repo-level dep score.
_JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


@dataclass
class NpmPackageInfo:
    """Dependency drift data for a single NPM package."""

    name: str
    installed_version: str = ""
    latest_version: str = ""
    installed_release_date: datetime | None = None
    latest_release_date: datetime | None = None
    months_behind: float = 0.0
    releases_per_month: float = 0.0
    dep_risk: float = 0.0
    is_dev: bool = False


@dataclass
class FileNpmData:
    """Dependency data for a single source file in a JS/TS repo."""

    path: str
    packages: list[NpmPackageInfo] = field(default_factory=list)
    dep_score: float = 0.0


class NpmAnalyzer:
    """
    Analyze dependency staleness for a JavaScript/TypeScript repository.

    Reads package.json, queries the NPM registry concurrently, and computes
    a dep_score (0-100) for every .js/.ts source file in the repo.
    Because we skip JS AST (no import graph), every source file gets the
    same repo-level dep score — which is still extremely valuable signal.
    """

    MAX_DEP_RISK = 50.0  # normalization ceiling — same as Python analyzer

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self._installed_versions: dict[str, str] = {}     # name -> "1.2.3"
        self._dev_packages: set[str] = set()               # dev-only package names
        self._package_cache: dict[str, NpmPackageInfo] = {}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def analyze(self, progress_callback=None) -> dict[str, FileNpmData]:
        """
        Full NPM dependency analysis pipeline.

        Returns ``{relative_file_path: FileNpmData}`` for every .js/.ts file.
        Returns empty dict if no package.json is found (not a JS repo).
        """
        package_json = self._find_package_json()
        if package_json is None:
            logger.info("NpmAnalyzer: no package.json found in %s — skipping", self.repo_path)
            return {}

        logger.info("NpmAnalyzer: found %s", package_json)

        # Step 1: Parse installed versions from package.json
        self._installed_versions, self._dev_packages = self._parse_package_json(package_json)
        if not self._installed_versions:
            logger.info("NpmAnalyzer: package.json has no dependencies")
            return {}

        logger.info("NpmAnalyzer: found %d packages (%d dev)", len(self._installed_versions), len(self._dev_packages))

        # Step 2: Query NPM registry concurrently with batching
        if progress_callback:
            progress_callback(f"Querying NPM registry for {len(self._installed_versions)} packages...")

        fetched = self._query_npm_batch(list(self._installed_versions.keys()))
        self._package_cache.update(fetched)

        # Step 3: Compute repo-level dep score from all production dependencies
        prod_risks: list[float] = []
        for pkg_name, info in self._package_cache.items():
            if pkg_name in self._dev_packages:
                continue  # dev deps don't count toward production decay
            risk = info.months_behind * max(info.releases_per_month, 0.1)
            info.dep_risk = risk
            prod_risks.append(risk)

        repo_dep_score = 0.0
        if prod_risks:
            mean_risk = sum(prod_risks) / len(prod_risks)
            repo_dep_score = min(mean_risk / self.MAX_DEP_RISK * 100, 100)

        # Step 4: Assign score to every JS/TS source file in the repo
        results: dict[str, FileNpmData] = {}
        source_files = self._find_source_files()

        for filepath in source_files:
            try:
                rel_path = filepath.relative_to(self.repo_path).as_posix()
            except ValueError:
                rel_path = filepath.as_posix()

            results[rel_path] = FileNpmData(
                path=rel_path,
                packages=list(self._package_cache.values()),
                dep_score=repo_dep_score,
            )

        logger.info(
            "NpmAnalyzer: scored %d JS/TS files, dep_score=%.1f",
            len(results), repo_dep_score,
        )
        return results

    # -------------------------------------------------------------------------
    # package.json parsing
    # -------------------------------------------------------------------------

    def _find_package_json(self) -> Path | None:
        """Find the root package.json — skips node_modules."""
        candidate = self.repo_path / "package.json"
        if candidate.is_file():
            return candidate
        # Monorepo: try one level down (packages/*/package.json)
        for child in self.repo_path.iterdir():
            if child.is_dir() and child.name not in {"node_modules", ".git", "dist", "build"}:
                candidate = child / "package.json"
                if candidate.is_file():
                    return candidate
        return None

    def _parse_package_json(self, pkg_json_path: Path) -> tuple[dict[str, str], set[str]]:
        """
        Parse dependencies and devDependencies from package.json.

        Returns (all_versions, dev_package_names).
        Strips semver range characters (^, ~, >, =) to get a clean version string.
        """
        try:
            data = json.loads(pkg_json_path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("NpmAnalyzer: failed to parse %s: %s", pkg_json_path, e)
            return {}, set()

        versions: dict[str, str] = {}
        dev_packages: set[str] = set()

        def _add_deps(deps: dict, is_dev: bool = False) -> None:
            for pkg_name, version_spec in deps.items():
                if pkg_name.startswith("//"):        # comment key
                    continue
                # Strip range chars: ^1.2.3 -> 1.2.3, ~2.0.0 -> 2.0.0, >=3 -> 3
                clean_version = re.sub(r"^[\^~>=<v\s]+", "", str(version_spec)).split(" ")[0]
                if not clean_version or clean_version in {"*", "latest", "next"}:
                    clean_version = ""
                versions[pkg_name] = clean_version
                if is_dev:
                    dev_packages.add(pkg_name)

        _add_deps(data.get("dependencies", {}), is_dev=False)
        _add_deps(data.get("devDependencies", {}), is_dev=True)
        _add_deps(data.get("peerDependencies", {}), is_dev=False)

        return versions, dev_packages

    def _find_source_files(self) -> list[Path]:
        """Find all .js/.ts source files, using shared .entropyignore filtering."""
        files: list[Path] = []
        ignore = IgnoreFilter(self.repo_path)
        
        for ext in _JS_EXTENSIONS:
            for filepath in self.repo_path.rglob(f"*{ext}"):
                try:
                    rel_path = filepath.relative_to(self.repo_path).as_posix()
                except ValueError:
                    rel_path = filepath.as_posix()
                    
                if not ignore.is_ignored(rel_path):
                    files.append(filepath)
        return files

    # -------------------------------------------------------------------------
    # NPM registry queries (concurrent with batching)
    # -------------------------------------------------------------------------

    def _query_npm_batch(self, package_names: list[str]) -> dict[str, NpmPackageInfo]:
        """Query NPM registry for all packages. Runs concurrently with bounded semaphore."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._async_query_batch(package_names))
                    return future.result(timeout=120)
            else:
                return loop.run_until_complete(self._async_query_batch(package_names))
        except RuntimeError:
            return asyncio.run(self._async_query_batch(package_names))

    async def _async_query_batch(self, package_names: list[str]) -> dict[str, NpmPackageInfo]:
        """Async: query NPM with bounded concurrency. Batch into groups to avoid overwhelming the registry."""
        semaphore = asyncio.Semaphore(_NPM_CONCURRENCY)
        results: dict[str, NpmPackageInfo] = {}

        async with aiohttp.ClientSession(
            headers={"Accept": "application/json", "User-Agent": "entropy-tracker/1.0"},
            connector=aiohttp.TCPConnector(limit=_NPM_CONCURRENCY),
        ) as session:
            tasks = [
                self._async_query_one(session, semaphore, pkg)
                for pkg in package_names
            ]
            fetched = await asyncio.gather(*tasks, return_exceptions=True)

        for pkg, info in zip(package_names, fetched):
            if isinstance(info, NpmPackageInfo):
                results[pkg] = info
            else:
                # Network failure or rate limit — create empty entry, don't crash
                results[pkg] = NpmPackageInfo(
                    name=pkg,
                    installed_version=self._installed_versions.get(pkg, ""),
                )
                logger.debug("NPM query failed for %s: %s", pkg, info)

        return results

    async def _async_query_one(
        self,
        session: Any,
        sem: asyncio.Semaphore,
        package_name: str,
    ) -> NpmPackageInfo:
        """
        Fetch a single package from the NPM registry.

        Uses abbreviated metadata endpoint ({pkg}/latest) first for speed,
        then falls back to full registry document if version history is needed.
        Caches results to ~/.entropy/npm_cache/{package}.json for 24 hours.
        """
        info = NpmPackageInfo(
            name=package_name,
            installed_version=self._installed_versions.get(package_name, ""),
            is_dev=package_name in self._dev_packages,
        )

        cache_file = _CACHE_DIR / f"{_safe_filename(package_name)}.json"

        async with sem:
            try:
                # --- cache hit? ---------------------------------------------------
                data: dict | None = None
                if cache_file.exists():
                    try:
                        cached = json.loads(cache_file.read_text())
                        if time.time() - cached.get("_cached_at", 0) < _CACHE_TTL:
                            data = cached
                    except Exception:
                        pass

                # --- cache miss: fetch from NPM -----------------------------------
                if data is None:
                    url = f"{_NPM_REGISTRY}/{package_name}"
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=12),
                    ) as resp:
                        if resp.status == 429:
                            logger.debug("NPM rate limit hit for %s — skipping", package_name)
                            return info
                        if resp.status != 200:
                            return info
                        data = await resp.json(content_type=None)
                        try:
                            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
                            data["_cached_at"] = time.time()
                            cache_file.write_text(json.dumps(data, ensure_ascii=False))
                        except Exception:
                            pass

                # --- extract latest version & date --------------------------------
                dist_tags = data.get("dist-tags", {})
                info.latest_version = dist_tags.get("latest", "")

                time_data: dict = data.get("time", {})

                # Latest release date
                if info.latest_version and info.latest_version in time_data:
                    info.latest_release_date = _parse_npm_date(time_data[info.latest_version])

                # Installed release date
                if info.installed_version and info.installed_version in time_data:
                    info.installed_release_date = _parse_npm_date(time_data[info.installed_version])

                # Months behind
                if info.latest_release_date and info.installed_release_date:
                    delta = info.latest_release_date - info.installed_release_date
                    info.months_behind = max(delta.days / 30.44, 0.0)
                elif info.latest_release_date and info.installed_version:
                    info.months_behind = 6.0  # pinned but can't find exact date

                # Velocity: releases per month over project history
                # time_data keys: "created", "modified", plus one key per version
                version_dates: list[datetime] = []
                for key, ts in time_data.items():
                    if key in {"created", "modified", "_cached_at"}:
                        continue
                    dt = _parse_npm_date(ts)
                    if dt:
                        version_dates.append(dt)

                if len(version_dates) >= 2:
                    version_dates.sort()
                    span_months = max((version_dates[-1] - version_dates[0]).days / 30.44, 1.0)
                    info.releases_per_month = len(version_dates) / span_months

            except aiohttp.ClientError as e:
                logger.debug("NPM network error for %s: %s", package_name, e)
            except Exception as e:
                logger.debug("NPM query error for %s: %s", package_name, e)

        return info


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _parse_npm_date(ts: str) -> datetime | None:
    """Parse an ISO 8601 timestamp from the NPM registry time field."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None


def _safe_filename(package_name: str) -> str:
    """
    Convert package name to a filesystem-safe cache filename.
    Scoped packages like @babel/core -> @babel__core
    """
    return re.sub(r"[/\\:*?\"<>|]", "__", package_name)
