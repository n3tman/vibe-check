"""Forge API data: stars, forks, open issues and PRs, archived flag, licence, languages, and
the median time to a first response on recent issues.

GitHub (REST, `$GH_TOKEN` or `$GITHUB_TOKEN`), GitLab (any instance, /api/v4), Forgejo and
Gitea (/api/v1). SourceHut and unknown forges give nulls. Any failure gives nulls plus an
`api_error`, never an exception to the caller.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .authors import is_bot_login

UA = "vibe-check (+https://github.com/n3tman/vibe-check)"
ISSUE_WINDOW_DAYS = 180

EMPTY = {
    "stars": None,
    "forks": None,
    "open_issues": None,
    "open_prs": None,
    "archived": None,
    "licence_detected": None,
    "languages": None,
    "issue_first_response_median_days": None,
    "issues_sampled": None,
    "issues_responded": None,
    "description": None,
}


class Http:
    """A tiny JSON client: User-Agent, token, retries on 429/5xx, a pause between calls."""

    def __init__(self, pause: float = 0.25):
        self.pause = pause
        self.calls = 0

    def get(self, url: str, headers: dict | None = None, tries: int = 3) -> tuple[object, dict]:
        h = {"User-Agent": UA, "Accept": "application/json", **(headers or {})}
        for attempt in range(tries):
            time.sleep(self.pause)
            self.calls += 1
            req = urllib.request.Request(url, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read()
                    return (json.loads(body) if body else None), {k.lower(): v for k, v in r.headers.items()}
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503, 504) and attempt + 1 < tries:
                    retry = e.headers.get("Retry-After")
                    time.sleep(min(int(retry) if retry and retry.isdigit() else 5 * (attempt + 1), 120))
                    continue
                if e.code == 403 and e.headers.get("x-ratelimit-remaining") == "0" and attempt + 1 < tries:
                    reset = int(e.headers.get("x-ratelimit-reset", "0"))
                    wait = max(0, reset - int(time.time())) + 1
                    if wait <= 900:
                        time.sleep(wait)
                        continue
                raise
            except (urllib.error.URLError, TimeoutError):
                if attempt + 1 < tries:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise
        raise RuntimeError("unreachable")


def split_repo(url: str) -> tuple[str, str]:
    u = urllib.parse.urlparse(url)
    path = re.sub(r"\.git$", "", u.path.strip("/"))
    return f"{u.scheme}://{u.hostname}" + (f":{u.port}" if u.port else ""), path


def guess_forge(url: str) -> str:
    host = urllib.parse.urlparse(url).hostname or ""
    if host == "github.com":
        return "github"
    if host == "gitlab.com" or host.startswith("gitlab.") or ".gitlab." in host:
        return "gitlab"
    if host in ("codeberg.org", "git.gay") or "forgejo" in host:
        return "forgejo"
    if host in ("gitea.com",) or "gitea" in host:
        return "gitea"
    if host.endswith("sr.ht"):
        return "sourcehut"
    return "other"


def _guard(out: dict, fn) -> None:
    """Issue response times are a bonus: a failure there keeps the rest of the API data."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        out["issue_response_error"] = f"{type(e).__name__}: {e}"[:200]


def _median_days(pairs: list[tuple[datetime, datetime | None]]) -> tuple[float | None, int, int]:
    """(median days to first response, issues sampled, issues with a response)."""
    waits = [(r - o).total_seconds() / 86400 for o, r in pairs if r is not None]
    med = round(statistics.median(waits), 2) if waits else None
    return med, len(pairs), len(waits)


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _shares(raw: dict[str, float]) -> dict[str, float] | None:
    total = sum(raw.values())
    if not total:
        return None
    return {k: round(v / total, 4) for k, v in sorted(raw.items(), key=lambda kv: -kv[1]) if v / total >= 0.001}


def _first_responses(issues: list[dict], comments: list[dict]) -> list[tuple[datetime, datetime | None]]:
    """issues: [{number, created, author}]; comments: [{number, created, author}]."""
    first: dict[int, datetime] = {}
    authors = {i["number"]: i["author"] for i in issues}
    for c in comments:
        n = c["number"]
        if n not in authors or c["author"] == authors[n] or is_bot_login(c["author"]):
            continue
        if n not in first or c["created"] < first[n]:
            first[n] = c["created"]
    return [(i["created"], first.get(i["number"])) for i in issues]


# --- GitHub -----------------------------------------------------------------------------

def github(http: Http, url: str, now: datetime) -> dict:
    _, path = split_repo(url)
    api = "https://api.github.com/repos/" + path
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    out = dict(EMPTY)
    repo, _ = http.get(api, h)
    assert isinstance(repo, dict)
    out.update(
        stars=repo.get("stargazers_count"),
        forks=repo.get("forks_count"),
        archived=repo.get("archived"),
        licence_detected=((repo.get("license") or {}).get("spdx_id") or None),
        description=repo.get("description"),
    )
    langs, _ = http.get(api + "/languages", h)
    out["languages"] = _shares(langs) if isinstance(langs, dict) else None

    _, hdr = http.get(api + "/pulls?state=open&per_page=1", h)
    out["open_prs"] = _count_from_link(hdr.get("link"), http, api + "/pulls?state=open&per_page=1", h)
    if repo.get("open_issues_count") is not None and out["open_prs"] is not None:
        out["open_issues"] = max(0, repo["open_issues_count"] - out["open_prs"])

    if repo.get("has_issues"):
        _guard(out, lambda: _github_issues(http, api, h, now, out))
    return out


def _github_issues(http: Http, api: str, h: dict, now: datetime, out: dict) -> None:
    """Newest issues and newest comments, so the two cover the same stretch of time.

    Comments come newest first. When the page cap stops the comment list early, only issues
    opened after the oldest comment read are kept: a first response to any of them comes later
    than the issue, so it is among the comments read. (Oldest-first comments paired with the
    newest issues left the recent issues of a busy repository with no response.)"""
    window = now - timedelta(days=ISSUE_WINDOW_DAYS)
    since = window.strftime("%Y-%m-%dT%H:%M:%SZ")
    comments = []
    capped = False
    for page in range(1, 11):
        data, _ = http.get(f"{api}/issues/comments?since={since}&sort=created&direction=desc&per_page=100&page={page}", h)
        if not isinstance(data, list) or not data:
            break
        for c in data:
            m = re.search(r"/issues/(\d+)$", c.get("issue_url", ""))
            if m:
                comments.append({"number": int(m.group(1)), "created": _dt(c["created_at"]), "author": (c.get("user") or {}).get("login")})
        if len(data) < 100:
            break
        capped = page == 10
    covered_from = window
    if capped and comments:
        covered_from = max(window, min(c["created"] for c in comments if c["created"]))
    issues = []
    for page in range(1, 6):
        data, _ = http.get(f"{api}/issues?state=all&since={since}&sort=created&direction=desc&per_page=100&page={page}", h)
        if not isinstance(data, list) or not data:
            break
        for i in data:
            created = _dt(i.get("created_at"))
            if "pull_request" in i or not created or created < covered_from:
                continue
            login = (i.get("user") or {}).get("login")
            if is_bot_login(login):
                continue
            issues.append({"number": i["number"], "created": created, "author": login})
        oldest = _dt(data[-1].get("created_at"))
        if len(data) < 100 or (oldest and oldest < covered_from):
            break
    med, n, responded = _median_days(_first_responses(issues, comments))
    out.update(issue_first_response_median_days=med, issues_sampled=n, issues_responded=responded)
    if covered_from > window:
        out["issues_window_from"] = covered_from.isoformat(timespec="seconds")


def _count_from_link(link: str | None, http: Http, url: str, h: dict) -> int | None:
    if link:
        m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
        if m:
            return int(m.group(1))
    data, _ = http.get(url, h)
    return len(data) if isinstance(data, list) else None


# --- GitLab -----------------------------------------------------------------------------

def gitlab(http: Http, url: str, now: datetime) -> dict:
    base, path = split_repo(url)
    api = f"{base}/api/v4/projects/{urllib.parse.quote(path, safe='')}"
    out = dict(EMPTY)
    repo, _ = http.get(api + "?license=true")
    assert isinstance(repo, dict)
    out.update(
        stars=repo.get("star_count"),
        forks=repo.get("forks_count"),
        open_issues=repo.get("open_issues_count"),
        archived=repo.get("archived"),
        licence_detected=_gitlab_spdx(repo["license"]) if repo.get("license") else None,
        description=repo.get("description"),
    )
    langs, _ = http.get(api + "/languages")
    out["languages"] = _shares(langs) if isinstance(langs, dict) else None
    _, hdr = http.get(api + "/merge_requests?state=opened&per_page=1")
    total = hdr.get("x-total")
    out["open_prs"] = int(total) if total and total.isdigit() else None
    if out["open_issues"] is None and repo.get("issues_enabled", True):
        _, hdr = http.get(api + "/issues?state=opened&per_page=1")
        total = hdr.get("x-total")
        out["open_issues"] = int(total) if total and total.isdigit() else None

    if repo.get("issues_enabled", True):
        _guard(out, lambda: _gitlab_issues(http, api, now, out))
    return out


def _gitlab_issues(http: Http, api: str, now: datetime, out: dict) -> None:
    after = (now - timedelta(days=ISSUE_WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data, _ = http.get(f"{api}/issues?created_after={after}&per_page=30&order_by=created_at")
    pairs = []
    for i in data if isinstance(data, list) else []:
        author = (i.get("author") or {}).get("username")
        if is_bot_login(author):
            continue
        notes, _ = http.get(f"{api}/issues/{i['iid']}/notes?sort=asc&order_by=created_at&per_page=20")
        first = None
        for n in notes if isinstance(notes, list) else []:
            who = (n.get("author") or {}).get("username")
            if n.get("system") or who == author or is_bot_login(who):
                continue
            first = _dt(n["created_at"])
            break
        pairs.append((_dt(i["created_at"]), first))
    med, n, responded = _median_days(pairs)
    out.update(issue_first_response_median_days=med, issues_sampled=n, issues_responded=responded)


def _gitlab_spdx(lic: dict) -> str | None:
    key = (lic.get("key") or "").lower()
    table = {
        "agpl-3.0": "AGPL-3.0", "gpl-3.0": "GPL-3.0", "gpl-2.0": "GPL-2.0", "lgpl-3.0": "LGPL-3.0",
        "lgpl-2.1": "LGPL-2.1", "mit": "MIT", "apache-2.0": "Apache-2.0", "mpl-2.0": "MPL-2.0",
        "bsd-3-clause": "BSD-3-Clause", "bsd-2-clause": "BSD-2-Clause", "isc": "ISC", "unlicense": "Unlicense",
        "eupl-1.2": "EUPL-1.2",
    }
    return table.get(key) or (lic.get("nickname") or lic.get("name"))


# --- Forgejo / Gitea --------------------------------------------------------------------

def forgejo(http: Http, url: str, now: datetime) -> dict:
    base, path = split_repo(url)
    api = f"{base}/api/v1/repos/{path}"
    out = dict(EMPTY)
    repo, _ = http.get(api)
    assert isinstance(repo, dict)
    lic = repo.get("licenses") or []
    out.update(
        stars=repo.get("stars_count"),
        forks=repo.get("forks_count"),
        open_issues=repo.get("open_issues_count"),
        open_prs=repo.get("open_pr_counter"),
        archived=repo.get("archived"),
        licence_detected=(lic[0] if lic else None),
        description=repo.get("description"),
    )
    langs, _ = http.get(api + "/languages")
    out["languages"] = _shares(langs) if isinstance(langs, dict) else None
    if repo.get("has_issues", True):
        _guard(out, lambda: _forgejo_issues(http, api, now, out))
    return out


def _forgejo_issues(http: Http, api: str, now: datetime, out: dict) -> None:
    since = (now - timedelta(days=ISSUE_WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    issues = []
    for page in range(1, 4):
        data, _ = http.get(f"{api}/issues?state=all&type=issues&since={since}&limit=50&page={page}")
        if not isinstance(data, list) or not data:
            break
        for i in data:
            created = _dt(i.get("created_at"))
            login = (i.get("user") or {}).get("login")
            if not created or created < now - timedelta(days=ISSUE_WINDOW_DAYS) or is_bot_login(login):
                continue
            issues.append({"number": i["number"], "created": created, "author": login})
        if len(data) < 50:
            break
    comments = []
    capped = False
    for page in range(1, 11):
        data, _ = http.get(f"{api}/issues/comments?since={since}&limit=50&page={page}")
        if not isinstance(data, list) or not data:
            break
        for c in data:
            m = re.search(r"/(\d+)$", c.get("issue_url", "") or "")
            if m:
                comments.append({"number": int(m.group(1)), "created": _dt(c["created_at"]), "author": (c.get("user") or {}).get("login")})
        if len(data) < 50:
            break
        capped = page == 10
    if capped and comments:
        # Forgejo lists comments oldest first and the cap stopped the list: a response after
        # the last comment read is missing, so keep only issues opened 14 days before it.
        last = max(c["created"] for c in comments if c["created"])
        issues = [i for i in issues if i["created"] <= last - timedelta(days=14)]
    med, n, responded = _median_days(_first_responses(issues, comments))
    out.update(issue_first_response_median_days=med, issues_sampled=n, issues_responded=responded)


def fetch(forge: str, url: str, http: Http, now: datetime) -> dict:
    fn = {"github": github, "gitlab": gitlab, "forgejo": forgejo, "gitea": forgejo}.get(forge)
    if fn is None:
        return {**EMPTY, "api_error": f"no API reader for forge '{forge}'"}
    try:
        return {**fn(http, url, now), "api_error": None}
    except Exception as e:  # noqa: BLE001 - a forge we can't read gives nulls
        return {**EMPTY, "api_error": f"{type(e).__name__}: {e}"[:300]}


def blob_url(forge: str, url: str, sha: str, path: str) -> str:
    base = re.sub(r"\.git$", "", url.rstrip("/"))
    p = urllib.parse.quote(path)
    if forge == "gitlab":
        return f"{base}/-/blob/{sha}/{p}"
    if forge in ("forgejo", "gitea"):
        return f"{base}/src/commit/{sha}/{p}"
    if forge == "sourcehut":
        return f"{base}/tree/{sha}/item/{p}"
    return f"{base}/blob/{sha}/{p}"


def commit_url(forge: str, url: str, sha: str) -> str:
    base = re.sub(r"\.git$", "", url.rstrip("/"))
    if forge == "gitlab":
        return f"{base}/-/commit/{sha}"
    return f"{base}/commit/{sha}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
