"""One project in, one data/metrics/<slug>.json out."""

from __future__ import annotations

import json
import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from . import VERSION, ai, forges, gitrepo, loc, repofiles, telemetry
from .activity import Activity, human_commits, status, unique_changes
from .authors import ai_bot_tool


# Tags that are not releases: nightlies, betas, release candidates, test builds.
PRERELEASE = re.compile(r"nightly|alpha|beta|[-.]rc\.?\d*|(\d|\b)rc\d|[-.]dev|preview|snapshot|canary|\btest|^untagged", re.I)


@dataclass
class Context:
    root: Path  # repo root (for cache/)
    now: datetime
    fetch: bool = True
    api: bool = True
    loc: bool = True
    per_host: int = 1
    http: forges.Http = field(default_factory=forges.Http)
    _sems: dict[str, threading.Semaphore] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    scc: Path | None = None

    def host(self, url: str) -> threading.Semaphore:
        h = urlparse(url).hostname or "?"
        with self._lock:
            if h not in self._sems:
                self._sems[h] = threading.Semaphore(self.per_host)
            return self._sems[h]

    @property
    def cache(self) -> Path:
        return self.root / "cache"


def _iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def attribution(commits: list[gitrepo.Commit], now: datetime) -> tuple[list[gitrepo.Commit], list[tuple[gitrepo.Commit, set[str]]], Counter, Counter]:
    """Last year's changes (bots dropped, a change landed twice counted once), the ones that
    credit an AI tool with the tools, and the tool and AI-bot tallies."""
    cut = now - timedelta(days=365)
    recent = [c for c in human_commits(unique_changes(commits)) if c.date >= cut]
    tools: Counter[str] = Counter()
    bots: Counter[tuple[str, str]] = Counter()
    credited = []
    for c in recent:
        found = ai.commit_ai_tools(c.message)
        bot = ai_bot_tool(c.author, c.email)
        if bot:
            found.add(bot)
            bots[(c.author, bot)] += 1
        if found:
            tools.update(found)
            credited.append((c, found))
    return recent, credited, tools, bots


def ai_scan(commits: list[gitrepo.Commit], paths: list[str], repo: Path, forge: str, url: str, sha: str, now: datetime) -> dict:
    recent, credited, tools, bots = attribution(commits, now)
    attributed = len(credited)
    examples = [
        {"sha": c.sha, "url": forges.commit_url(forge, url, c.sha), "date": c.date.date().isoformat(), "tools": sorted(found)}
        for c, found in credited[:8]
    ]
    agent_files = [{**f, "url": forges.blob_url(forge, url, sha, f["path"].rstrip("/"))} for f in ai.find_agent_files(paths)]
    wf_paths = [p for p in paths if ai.is_workflow_path(p)][:40]
    gitrepo.prefetch(repo, wf_paths)
    workflows = []
    for p in wf_paths:
        text = gitrepo.show(repo, p, max_bytes=300_000)
        if text:
            hits = ai.scan_workflow(text)
            if hits:
                workflows.append({"path": p, "url": forges.blob_url(forge, url, sha, p), "matches": hits})
    share = round(attributed / len(recent), 4) if recent else None
    bot_list = [{"name": n, "tool": t, "commits_365d": k} for (n, t), k in bots.most_common()]
    return {
        "agent_files": agent_files,
        "commits_365d": len(recent),
        "attributed_commits_365d": attributed,
        "share_365d": share,
        "tools": dict(tools.most_common()),
        "ai_bot_authors": bot_list,
        "examples": examples,
        "workflows": workflows,
        "suggested_dev_usage": ai.suggest_dev_usage(len(agent_files), share, attributed, len(workflows), sum(bots.values())),
    }


def telemetry_scan(paths: list[str], repo: Path, forge: str, url: str, sha: str) -> dict:
    manifests = telemetry.pick_manifests(paths)
    gitrepo.prefetch(repo, manifests)
    found = []
    for p in manifests:
        text = gitrepo.show(repo, p, max_bytes=1_000_000)
        if text:
            for hit in telemetry.scan_manifest(p, text):
                found.append({**hit, "url": forges.blob_url(forge, url, sha, p)})
    return {"found": found, "sdks": sorted({f["sdk"] for f in found}), "manifests_scanned": len(manifests)}


def collect_repo(spec: dict, ctx: Context) -> tuple[dict, list[gitrepo.Commit]]:
    url = spec["url"].rstrip("/")
    forge = spec.get("forge") or forges.guess_forge(url)
    out: dict = {"url": url, "forge": forge, "role": spec.get("role", "main"), "first_parent": bool(spec.get("first_parent")), "ok": False, "error": None}
    dest = gitrepo.cache_dir_for(url, ctx.cache / "repos")
    try:
        with ctx.host(url):
            gitrepo.clone_or_fetch(url, dest, fetch=ctx.fetch)
        sha, branch = gitrepo.head_info(dest)
        paths = gitrepo.ls_tree(dest)
        commits = gitrepo.log(dest, mailmap=".mailmap" in paths, first_parent=bool(spec.get("first_parent")))
    except gitrepo.GitError as e:
        out["error"] = str(e)
        return out, []

    act = Activity(commits, ctx.now)
    m = act.metrics()
    all_tags = gitrepo.tags(dest)
    releases = [t for t in all_tags if not PRERELEASE.search(t[0])] or all_tags
    cut = ctx.now - timedelta(days=365)
    out.update(
        head_sha=sha,
        default_branch=branch or None,
        **m,
        last_tag=releases[0][0] if releases else None,
        last_tag_date=_iso(releases[0][1]) if releases else None,
        tags_365d=sum(1 for _, d in releases if d >= cut),
        prerelease_tags_365d=sum(1 for n, d in all_tags if d >= cut and PRERELEASE.search(n)),
        ci=repofiles.ci_files(paths),
        tests_present=repofiles.tests_present(paths),
        security_policy=repofiles.security_policy(paths),
        licence_file=repofiles.licence_file(paths),
        files=len(paths),
    )
    if out["security_policy"]:
        out["security_policy_url"] = forges.blob_url(forge, url, sha, out["security_policy"])
    out["ai_scan"] = ai_scan(commits, paths, dest, forge, url, sha, ctx.now)
    out["telemetry_scan"] = telemetry_scan(paths, dest, forge, url, sha)

    api = dict(forges.EMPTY, api_error="skipped (--no-api)")
    if ctx.api:
        with ctx.host(url):
            api = forges.fetch(forge, url, ctx.http, ctx.now)
    out.update(api)
    if not out.get("licence_detected") and out.get("licence_file"):
        text = gitrepo.show(dest, out["licence_file"], max_bytes=200_000)
        if text:
            out["licence_detected"] = repofiles.detect_licence(text)
            out["licence_source"] = "file"

    out["loc"] = None
    if ctx.loc and ctx.scc:
        try:
            with ctx.host(url):
                lines, sizes = loc.count(url, ctx.scc, ctx.cache / "tmp")
            out["loc"] = lines
            if out.get("languages") is None and lines:
                # By lines of code, not bytes: one minified bundle would otherwise outweigh the source.
                out["languages"] = forges._shares({k: float(v) for k, v in lines.items()})
                out["languages_source"] = "scc"
            elif out.get("languages") is not None:
                out["languages_source"] = "forge"
        except Exception as e:  # noqa: BLE001
            out["loc_error"] = str(e)[:200]
    out["status"] = status(act.last_commit(), m["authors_90d"], out.get("archived"), ctx.now)
    out["ok"] = True
    return out, commits


# Repos whose activity belongs to someone else: a library the app builds on (Tacit and Tammy
# list Trixnity). They are measured and shown, but left out of the project's own numbers.
NOT_OWN = {"upstream"}
# Two repos that share at least this share of the smaller one's commits are one codebase (a
# mirror, an old home, a copy): their commits are merged and their lines of code, tags, agent
# files and workflows are counted once.
SAME_CODEBASE = 0.5


def _same_codebase(repos: list[dict], shas: list[set[str]]) -> None:
    """Mark each repo that repeats an earlier one with `duplicate_of` (main repo first)."""
    order = sorted(range(len(repos)), key=lambda i: (repos[i].get("role") != "main", i))
    kept: list[int] = []
    for i in order:
        r = repos[i]
        r.pop("duplicate_of", None)
        twin = next(
            (k for k in kept if shas[i] and shas[k] and len(shas[i] & shas[k]) >= SAME_CODEBASE * min(len(shas[i]), len(shas[k]))),
            None,
        )
        if twin is None and r.get("role") == "mirror" and kept:
            twin = kept[0]
        if twin is not None:
            r["duplicate_of"] = repos[twin]["url"]
        else:
            kept.append(i)


def combine(repos: list[dict], commits_by_repo: list[list[gitrepo.Commit]], now: datetime) -> dict | None:
    pairs = [(r, c) for r, c in zip(repos, commits_by_repo) if r.get("ok")]
    if not pairs:
        return None
    own = [(r, c) for r, c in pairs if r.get("role") not in NOT_OWN] or pairs
    ok = [r for r, _ in own]
    _same_codebase(ok, [{c.sha for c in cs} for _, cs in own])
    distinct = [r for r in ok if not r.get("duplicate_of")]
    seen: set[str] = set()
    uniq = []
    for _, cs in own:
        for c in cs:
            if c.sha not in seen:
                seen.add(c.sha)
                uniq.append(c)
    act = Activity(uniq, now)
    m = act.metrics()
    archived = all(r.get("archived") for r in ok)
    recent, credited, tools, bots = attribution(uniq, now)
    attributed, total = len(credited), len(recent)
    share = round(attributed / total, 4) if total else None
    n_agent = sum(len(r["ai_scan"]["agent_files"]) for r in distinct)
    n_wf = sum(len(r["ai_scan"]["workflows"]) for r in distinct)
    n_bot = sum(bots.values())
    tags = [(r["last_tag_date"], r["last_tag"], r["url"]) for r in ok if r.get("last_tag_date")]
    last = max(tags, key=lambda t: datetime.fromisoformat(t[0])) if tags else None
    main = next((r for r in ok if r.get("role") == "main"), ok[0])
    loc_total: Counter[str] = Counter()
    for r in distinct:
        loc_total.update(r.get("loc") or {})

    def total_of(key: str) -> int | None:
        vals = [r.get(key) for r in ok if r.get(key) is not None]
        return sum(vals) if vals else None

    return {
        **m,
        "status": status(act.last_commit(), m["authors_90d"], archived, now),
        "stars": total_of("stars"),
        "forks": total_of("forks"),
        "open_issues": total_of("open_issues"),
        "open_prs": total_of("open_prs"),
        "last_tag": last[1] if last else None,
        "last_tag_date": last[0] if last else None,
        "last_tag_repo": last[2] if last else None,
        "tags_365d": sum(r.get("tags_365d") or 0 for r in distinct),
        "languages": main.get("languages"),
        "main_language": next(iter(main.get("languages") or {}), None),
        "loc_total": sum(loc_total.values()) or None,
        "loc": dict(loc_total.most_common()) or None,
        "licence_detected": main.get("licence_detected"),
        "archived": archived,
        "ci": any(r.get("ci") for r in ok),
        "tests_present": any(r.get("tests_present") for r in ok),
        "security_policy": next((r["security_policy_url"] for r in ok if r.get("security_policy_url")), None),
        "issue_first_response_median_days": main.get("issue_first_response_median_days"),
        "repos_counted": [r["url"] for r in ok],
        "ai": {
            "attributed_commits_365d": attributed,
            "commits_365d": total,
            "share_365d": share,
            "tools": dict(tools.most_common()),
            "agent_files": n_agent,
            "workflows": n_wf,
            "ai_bot_commits_365d": n_bot,
            "suggested_dev_usage": ai.suggest_dev_usage(n_agent, share, attributed, n_wf, n_bot),
        },
        "telemetry_sdks": sorted({s for r in ok for s in r["telemetry_scan"]["sdks"]}),
    }


def collect_project(project: dict, ctx: Context) -> dict:
    repos, commits = [], []
    for spec in project.get("repos") or []:
        if not isinstance(spec, dict) or not spec.get("url"):
            continue
        r, c = collect_repo(spec, ctx)
        repos.append(r)
        commits.append(c)
    return {
        "slug": project["slug"],
        "collector_version": VERSION,
        "fetched_at": ctx.now.isoformat(timespec="seconds"),
        "combined": combine(repos, commits, ctx.now),
        "repos": repos,
    }


def write_if_changed(path: Path, data: dict) -> bool:
    """Write unless only fetched_at would change (keeps refresh commits meaningful)."""
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        try:
            old = json.loads(path.read_text())
            if {**old, "fetched_at": None} == json.loads(json.dumps({**data, "fetched_at": None})):
                return False
        except json.JSONDecodeError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True
