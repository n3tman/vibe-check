"""vibecheck-discover: list candidate Matrix projects that data/projects/ doesn't have yet.

Sources: repository topics on GitHub, GitLab.com and Codeberg; awesome lists about Matrix; and
every This Week in Matrix post (Markdown files of the matrix.org website repository, cloned into
cache/matrix.org-site). Writes sources/candidates.tsv, one row per repository, minus the
repositories already named by a project file. Step 12's triage decides which become projects.

  uv run --project collector vibecheck-discover                  # every source
  uv run --project collector vibecheck-discover --topic-report   # topics worth adding
  uv run --project collector vibecheck-discover --refresh        # ignore cache/discover

API responses are cached in cache/discover/ so a rerun costs nothing; --refresh refetches.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .cli import find_root, load_projects
from .forges import UA, Http

# --- topics -----------------------------------------------------------------------------

# The repository's own topics, the step's starting list, then the topics the widening loop
# (--topic-report) found on at least 5 kept repositories. Counts are in notes/11.md.
TOPICS = [
    "element", "matrix", "matrix-bot", "matrix-bridge", "matrix-chat", "matrix-client",
    "matrix-homeserver", "matrix-org", "matrix-server",
    "matrix-sdk", "matrix-protocol", "matrix-synapse", "matrix-appservice", "matrix-federation",
    "matrix-widget", "maubot", "mautrix", "element-matrix", "matrixorg",
]
# Topics the widening loop added: on at least 5 kept repositories and about the protocol (topics
# such as matrix-library, matrix-rain or sparse-matrix are maths and screensavers).
TOPICS += [
    "matrix-nio", "matrixrtc", "matrix-widget-api", "matrix-synapse-homeserver", "matrix-js-sdk",
    "matrix-rust-sdk", "matrix-bots", "matrix-admin-api", "matrixbot", "matrix-synapse-server",
    "matrix-registration", "matrix-server-management", "matrix-rooms", "matrix-room", "matrix-dendrite",
    "matrix-authentication-service", "matrix-api",
    "matrix.org",  # GitLab only: GitHub and Forgejo topics can't hold a dot
    "element-web",
]
MATHS_TOPICS = {
    "matrix-library", "matrix-calculations", "matrix-multiplication", "matrix-operations", "matrix-functions",
    "matrix-computations", "matrix-calculator", "linear-algebra", "sparse-matrix", "matrix-rain", "led-matrix",
    "matrix-factorization", "matrix-decompositions", "matrix-inversion", "matrix-digital-rain",
}
# Also maths and UI words: a repository found only through these needs more evidence.
NOISY = {"matrix", "element"}
# Not searched (neural networks, Azure Synapse), but next to a noisy topic it means the homeserver.
CORROBORATING = {"synapse", "matrix-docker-ansible-deploy", "element-web", "element-x", "dendrite", "conduwuit"}
MATHS = re.compile(
    r"matri(?:x|ces) (?:operation|calculat|multiplica|algebra|librar|class|manipulat|comput|addition|inver|determinant)|"
    r"linear algebra|determinant|eigen|sparse|tensor|numpy|digital rain|matrix rain|matrix effect|led matrix|"
    r"anticheat|minecraft|spiral|adjacency|confusion matrix",
    re.I,
)

MATRIX_TEXT = re.compile(
    r"matrix\.org|matrix\.to|homeserver|home server|\bm\.room|\bmxid|matrix-nio|matrix-js-sdk|matrix-rust-sdk|"
    r"mautrix|maubot|synapse|dendrite|conduit|element\.io|\[matrix\]|matrix protocol|matrix-protocol|"
    r"matrix (?:client|bot|bridge|server|chat|room|homeserver|sdk|account|network|federation|messenger|messaging|appservice|widget)|"
    r"(?:for|on|to|via|with|over|in) matrix\b|matrix (?:and|or|/) (?:xmpp|irc|discord|telegram|signal|slack)|"
    r"(?:xmpp|irc|discord|telegram|signal|slack|whatsapp),? (?:and |or |/ ?)?matrix\b",
    re.I,
)


def matrix_topic(t: str) -> bool:
    return (t in TOPICS and t not in NOISY) or t in CORROBORATING


def matrix_verdict(topics: list[str] | None, text: str | None) -> bool | None:
    """True: another Matrix topic, or a Matrix word and no maths word; False: a description
    without that; None: no description, so only the README can tell."""
    topics = [t.lower() for t in topics or []]
    if any(matrix_topic(t) for t in topics):
        return True
    if any(t in MATHS_TOPICS for t in topics):
        return False
    if text and MATRIX_TEXT.search(text) and not MATHS.search(text):
        return True
    if text and text.strip():
        return False
    return None


def readme_verdict(md: str) -> bool:
    head = md[:4000]
    return bool(MATRIX_TEXT.search(head)) and not MATHS.search(head)


# --- URLs -------------------------------------------------------------------------------

FORGE_HOSTS = {
    "github.com": "github", "gitlab.com": "gitlab", "codeberg.org": "forgejo", "git.sr.ht": "sourcehut",
    "framagit.org": "gitlab", "gitlab.gnome.org": "gitlab", "invent.kde.org": "gitlab", "salsa.debian.org": "gitlab",
    "gitlab.freedesktop.org": "gitlab", "0xacab.org": "gitlab", "gitea.com": "gitea", "git.gay": "forgejo",
    "notabug.org": "gitea", "git.envs.net": "forgejo", "gitlab.matrix.org": "gitlab",
}
GITHUB_RESERVED = {
    "about", "apps", "blog", "collections", "contact", "customer-stories", "enterprise", "events", "explore",
    "features", "login", "marketplace", "new", "notifications", "orgs", "organizations", "pricing", "pulls",
    "issues", "readme", "search", "security", "settings", "site", "sponsors", "topics", "trending", "users",
    "join", "signup", "watching", "stars", "codespaces", "account", "dashboard", "gist", "advisories",
}
GITLAB_RESERVED = {"users", "explore", "help", "dashboard", "groups", "search", "api", "projects", "admin", "-"}
GITEA_RESERVED = {"user", "explore", "api", "assets", "org", "repo", "admin", "notifications", "issues", "pulls", "-"}
GITLAB_SUBPAGES = {
    "issues", "merge_requests", "tree", "blob", "commits", "commit", "tags", "releases", "wikis", "raw",
    "pipelines", "compare", "snippets", "milestones", "labels", "branches", "boards", "jobs", "archive",
    "packages", "container_registry", "graphs", "network", "forks", "activity", "edit", "settings",
}


def forge_of(host: str) -> str | None:
    if host in FORGE_HOSTS:
        return FORGE_HOSTS[host]
    if host.startswith("gitlab."):
        return "gitlab"
    if host.startswith(("forgejo.", "gitea.")) or "forgejo" in host:
        return "forgejo"
    return None


def normalise(url: str) -> tuple[str, str] | None:
    """(https://host/owner/repo in lower case, forge) for a link to a repository or to any page
    inside one; None for anything else (profiles, organisations, other sites)."""
    url = url.strip().rstrip(".,;:!?)]}'\"*_>`")
    try:
        u = urllib.parse.urlparse(url)
        host = (u.hostname or "").lower()
    except ValueError:
        return None
    if u.scheme not in ("http", "https", ""):
        return None
    host = host.removeprefix("www.")
    forge = forge_of(host)
    if not forge:
        return None
    parts = [p for p in urllib.parse.unquote(u.path).split("/") if p]
    if forge == "github":
        if len(parts) < 2 or parts[0].lower() in GITHUB_RESERVED:
            return None
        parts = parts[:2]
    elif forge == "sourcehut":
        if len(parts) < 2 or not parts[0].startswith("~"):
            return None
        parts = parts[:2]
    elif forge == "gitlab":
        if "-" in parts:
            parts = parts[: parts.index("-")]
        else:
            cut = next((i for i, p in enumerate(parts) if i >= 2 and p in GITLAB_SUBPAGES), None)
            if cut is not None:
                parts = parts[:cut]
        if len(parts) < 2 or parts[0].lower() in GITLAB_RESERVED:
            return None
    else:
        if len(parts) < 2 or parts[0].lower() in GITEA_RESERVED:
            return None
        parts = parts[:2]
    parts[-1] = re.sub(r"\.git$", "", parts[-1])
    if not parts[-1] or not re.fullmatch(r"[\w.~-]+", "".join(parts).replace("/", "")):
        return None
    return f"https://{host}/" + "/".join(parts).lower(), forge


URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+", re.I)


def links(text: str) -> list[tuple[str, str]]:
    out = []
    for m in URL_RE.finditer(text):
        n = normalise(m.group(0))
        if n:
            out.append(n)
    return out


# --- candidates -------------------------------------------------------------------------

@dataclass
class Cand:
    key: str
    forge: str
    url: str = ""
    name: str | None = None
    description: str | None = None
    stars: int | None = None
    archived: str | None = None  # yes, no, or missing (the forge says it doesn't exist)
    pushed_at: str | None = None
    sources: set[str] = field(default_factory=set)
    twim: dict[str, str] = field(default_factory=dict)  # post date -> section heading
    topics: set[str] = field(default_factory=set)
    meta: bool = False  # metadata came from the forge

    def __post_init__(self):
        self.url = self.url or self.key


class Pool:
    def __init__(self):
        self.c: dict[str, Cand] = {}

    def add(self, key: str, forge: str, source: str, **meta) -> Cand:
        c = self.c.get(key) or self.c.setdefault(key, Cand(key, forge))
        c.sources.add(source)
        if meta:
            set_meta(c, **meta)
        return c

    def twim(self, key: str, forge: str, day: str, heading: str | None) -> None:
        c = self.c.get(key) or self.c.setdefault(key, Cand(key, forge))
        if day not in c.twim or (heading and not c.twim[day]):
            c.twim[day] = heading or ""

    def rename(self, old: str, new: str) -> Cand:
        """The forge says `old` is now `new` (a rename or a transfer): merge the two rows."""
        c = self.c.pop(old)
        if new in self.c:
            n = self.c[new]
            n.sources |= c.sources
            n.topics |= c.topics
            for d, h in c.twim.items():
                n.twim.setdefault(d, h)
            return n
        c.key = new
        self.c[new] = c
        return c


def set_meta(c: Cand, url=None, name=None, description=None, stars=None, archived=None, pushed_at=None, topics=None):
    c.url = url or c.url
    c.name = name or c.name
    c.description = (description or "").strip() or c.description
    c.stars = stars if stars is not None else c.stars
    if archived is not None:
        c.archived = archived if isinstance(archived, str) else ("yes" if archived else "no")
    c.pushed_at = (pushed_at or "")[:10] or c.pushed_at
    c.topics |= set(topics or [])
    c.meta = True


def known_repos(projects: list[dict]) -> set[str]:
    keys = set()
    for p in projects:
        for r in p.get("repos") or []:
            n = normalise(str(r.get("url") or ""))
            if n:
                keys.add(n[0])
        n = normalise(str(p.get("homepage") or ""))
        if n:
            keys.add(n[0])
    return keys


def twim_summary(twim: dict[str, str]) -> str:
    if not twim:
        return ""
    days = sorted(twim)
    if len(days) == 1:
        return f"twim:{days[0]}"
    return f"twim:{len(days)} posts {days[0]}..{days[-1]}"


COLUMNS = ["url", "forge", "name", "description", "stars", "archived", "pushed_at", "sources", "twim_last",
           "twim_posts", "twim_heading", "found", "same_name_as"]


GENERIC_NAMES = {"app", "web", "server", "client", "android", "ios", "desktop", "docs", "website", "matrix", "bot",
                 "sdk", "core", "api", "cli", "frontend", "backend", "mobile", "element"}


def project_names(projects: list[dict]) -> dict[str, str]:
    names: dict[str, str] = {}
    for p in projects:
        for n in [p.get("slug"), p.get("name")] + [str(r.get("url") or "").rstrip("/").rsplit("/", 1)[-1] for r in p.get("repos") or []]:
            if n and str(n).lower() not in GENERIC_NAMES:
                names.setdefault(re.sub(r"\.git$", "", str(n)).lower(), p["slug"])
    return names


def stale(c: Cand, cutoff: str | None) -> bool:
    """Archived, gone, or no push since the cutoff date. Rows without a date (forges whose API
    isn't read) stay in: triage looks at them."""
    if c.archived in ("yes", "missing"):
        return True
    return bool(cutoff and c.pushed_at and c.pushed_at < cutoff)


def rows(pool: Pool, known: set[str], cutoff: str | None = None, slugs: dict[str, str] | None = None) -> list[dict]:
    """slugs: lower-case repository or project name -> slug, to flag forks, mirrors and moves."""
    out, slugs = [], slugs or {}
    for c in pool.c.values():
        if c.key in known or stale(c, cutoff):
            continue
        srcs = sorted(c.sources)
        if c.twim:
            srcs.append(twim_summary(c.twim))
        last = max(c.twim) if c.twim else ""
        name = c.name or c.key.rsplit("/", 1)[-1]
        out.append({
            "same_name_as": slugs.get(name.lower()) or slugs.get(c.key.rsplit("/", 1)[-1], ""),
            "url": c.url, "forge": c.forge, "name": name,
            "description": c.description or "", "stars": "" if c.stars is None else c.stars,
            "archived": c.archived or "", "pushed_at": c.pushed_at or "", "sources": "; ".join(srcs),
            "twim_last": last, "twim_posts": len(c.twim) or "", "twim_heading": c.twim.get(last, "") if last else "",
            "found": len(c.sources) + (1 if c.twim else 0),
        })
    out.sort(key=lambda r: (-r["found"], -(r["stars"] or 0), r["url"]))
    return out


def clean(v) -> str:
    return re.sub(r"[\t\r\n]+", " ", str(v)).strip()


def write_tsv(path: Path, data: list[dict]) -> None:
    lines = ["\t".join(COLUMNS)] + ["\t".join(clean(r[k]) for k in COLUMNS) for r in data]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# --- This Week in Matrix ------------------------------------------------------------------

TWIM_CATEGORY = re.compile(r"^category\s*=\s*\[[^\]]*this week in matrix", re.I | re.M)
TWIM_TITLE = re.compile(r'^title\s*=\s*"this week in matrix', re.I | re.M)
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")


def heading_text(h: str) -> str:
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = re.sub(r"[*_`]", "", h)
    h = re.sub(r"[^\w\s.+&'/()-]", "", h)
    return re.sub(r"\s+", " ", h).strip()


def twim_post(text: str, name: str) -> tuple[str, list[tuple[str, str, str]]] | None:
    """(post date, [(key, forge, heading)]) for a This Week in Matrix post, else None."""
    if not text.startswith(("+++", "\n+++", "﻿+++")) and "+++" not in text[:20]:
        return None
    parts = text.split("+++", 2)
    if len(parts) < 3:
        return None
    front, body = parts[1], parts[2]
    if not (TWIM_CATEGORY.search(front) or TWIM_TITLE.search(front)):
        return None
    m = re.search(r'^date\s*=\s*"?(\d{4}-\d{2}-\d{2})', front, re.M) or re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if not m:
        m = re.search(r"/blog/(\d{4})/(\d{2})/(\d{2})/", front)
        if not m:
            return None
        day = "-".join(m.groups())
    else:
        day = m.group(1)
    found, heading = [], ""
    for line in body.splitlines():
        h = HEADING.match(line)
        if h:
            heading = heading_text(h.group(2))
        for key, forge in links(line):
            found.append((key, forge, heading))
    return day, found


def twim(pool: Pool, site: Path) -> dict:
    posts = []
    for f in sorted((site / "content" / "blog").glob("**/*.md")):
        p = twim_post(f.read_text(encoding="utf-8", errors="replace"), f.name)
        if p:
            posts.append(p)
    for day, found in posts:
        for key, forge, heading in found:
            pool.twim(key, forge, day, heading)
    days = sorted(d for d, _ in posts)
    return {"posts": len(posts), "first": days[0] if days else None, "last": days[-1] if days else None,
            "repos": len({k for _, f in posts for k, _, _ in f})}


# --- HTTP with a cache ------------------------------------------------------------------------

class Fetch:
    """One Http per host (so one request at a time per host), responses cached by URL."""

    def __init__(self, cache: Path, refresh: bool):
        self.cache, self.refresh = cache, refresh
        self.cache.mkdir(parents=True, exist_ok=True)
        self.http: dict[str, Http] = {}
        self.blocked: dict[str, float] = {}  # host -> time it asked us to wait until
        self.calls = 0
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.gh = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            self.gh["Authorization"] = f"Bearer {token}"

    def _file(self, key: str) -> Path:
        return self.cache / (hashlib.sha1(key.encode()).hexdigest() + ".json")

    def get(self, url: str, headers: dict | None = None, pause: float = 0.5, max_wait: int = 3600) -> tuple[object, dict]:
        f = self._file(url)
        if f.exists() and not self.refresh:
            d = json.loads(f.read_text(encoding="utf-8"))
            return d["body"], d["headers"]
        host = urllib.parse.urlparse(url).hostname or ""
        if self.blocked.get(host, 0) > time.time():
            raise RuntimeError(f"{host} asked to wait until {time.strftime('%H:%M', time.localtime(self.blocked[host]))}")
        http = self.http.setdefault(host, Http(pause=pause))
        for attempt in range(6):
            try:
                body, hdr = http.get(url, headers, tries=1 if max_wait < 3600 else 3)
                break
            except urllib.error.HTTPError as e:
                # GitHub's secondary limits answer 403 with Retry-After and no reset header.
                if e.code in (403, 429) and attempt < 5 and (e.code == 429 or e.headers.get("Retry-After") or e.headers.get("x-ratelimit-remaining") == "0"):
                    reset = int(e.headers.get("x-ratelimit-reset") or 0)
                    wait = int(e.headers.get("Retry-After") or 0) or max(5, reset - int(time.time()) + 1)
                    if wait > max_wait:
                        self.blocked[host] = time.time() + wait
                        raise
                    print(f"    rate limited by {host}: waiting {min(wait, 3600)} s", file=sys.stderr)
                    time.sleep(min(wait, 3600))
                    continue
                if e.code == 404:
                    body, hdr = {"_status": 404}, {}
                    break
                raise
        self.calls += 1
        keep = {k: v for k, v in hdr.items() if k in ("link", "x-total", "x-total-pages", "x-total-count")}
        f.write_text(json.dumps({"url": url, "body": body, "headers": keep}, ensure_ascii=False), encoding="utf-8")
        return body, keep

    def graphql(self, query: str) -> dict:
        f = self._file("graphql:" + query)
        if f.exists() and not self.refresh:
            return json.loads(f.read_text(encoding="utf-8"))["body"]
        body = json.dumps({"query": query}).encode()
        for attempt in range(6):
            time.sleep(0.5)
            req = urllib.request.Request("https://api.github.com/graphql", data=body, method="POST",
                                         headers={"User-Agent": UA, "Content-Type": "application/json", **self.gh})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 429, 502, 503, 504) and attempt < 5:
                    wait = int(e.headers.get("Retry-After") or 0) or 30 * (attempt + 1)
                    print(f"    GraphQL {e.code}: waiting {wait} s", file=sys.stderr)
                    time.sleep(wait)
                    continue
                raise
        self.calls += 1
        f.write_text(json.dumps({"query": query, "body": data}, ensure_ascii=False), encoding="utf-8")
        return data


# --- GitHub -----------------------------------------------------------------------------------

def gh_search(fx: Fetch, q: str, page: int) -> dict:
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": q, "per_page": 100, "page": page})
    body, _ = fx.get(url, fx.gh, pause=2.1)  # the search API allows 30 requests a minute
    return body if isinstance(body, dict) else {}


def gh_query_all(fx: Fetch, base: str, log: list) -> list[dict]:
    """Every result of a search, sliced by creation date until each slice is under 1,000."""
    items: list[dict] = []
    today = date.today()

    def run(lo: date | None, hi: date | None) -> None:
        q = base if lo is None else f"{base} created:{lo.isoformat()}..{hi.isoformat()}"
        first = gh_search(fx, q, 1)
        total = first.get("total_count", 0)
        if total > 1000:
            lo, hi = lo or date(2008, 1, 1), hi or today
            if lo < hi:
                mid = lo + (hi - lo) // 2
                run(lo, mid)
                run(mid + timedelta(days=1), hi)
                return
        log.append({"query": q, "total": total, "incomplete": bool(first.get("incomplete_results"))})
        items.extend(first.get("items") or [])
        for page in range(2, math.ceil(min(total, 1000) / 100) + 1):
            items.extend(gh_search(fx, q, page).get("items") or [])

    run(None, None)
    return items


def gh_item(c: Cand, i: dict) -> None:
    set_meta(c, url=i.get("html_url"), name=i.get("name"), description=i.get("description"),
             stars=i.get("stargazers_count"), archived=i.get("archived"), pushed_at=i.get("pushed_at"),
             topics=i.get("topics"))


# --- GitLab and Codeberg ----------------------------------------------------------------------

def gitlab_topic(fx: Fetch, topic: str) -> list[dict]:
    out = []
    for page in range(1, 1000):
        url = "https://gitlab.com/api/v4/projects?" + urllib.parse.urlencode({"topic": topic, "per_page": 100, "page": page, "order_by": "id", "sort": "asc"})
        data, _ = fx.get(url, pause=1.0)
        if not isinstance(data, list) or not data:
            break
        out.extend(data)
        if len(data) < 100:
            break
    return out


def codeberg_topic(fx: Fetch, topic: str) -> list[dict]:
    out = []
    for page in range(1, 1000):
        url = "https://codeberg.org/api/v1/repos/search?" + urllib.parse.urlencode({"q": topic, "topic": "true", "limit": 50, "page": page})
        data, _ = fx.get(url, pause=1.0)
        data = (data or {}).get("data") if isinstance(data, dict) else None
        if not data:
            break
        out.extend(data)
        if len(data) < 50:
            break
    return out


def gl_meta(c: Cand, p: dict) -> None:
    set_meta(c, url=p.get("web_url"), name=p.get("name"), description=p.get("description"),
             stars=p.get("star_count"), archived=p.get("archived"), pushed_at=p.get("last_activity_at"),
             topics=p.get("topics") or p.get("tag_list"))


def cb_meta(c: Cand, r: dict) -> None:
    set_meta(c, url=r.get("html_url"), name=r.get("name"), description=r.get("description"),
             stars=r.get("stars_count"), archived=r.get("archived"), pushed_at=r.get("updated_at"),
             topics=r.get("topics"))


# --- README checks (noisy topics, awesome lists) ---------------------------------------------------

def gh_readme(fx: Fetch, full: str) -> str:
    body, _ = fx.get(f"https://api.github.com/repos/{full}/readme", fx.gh)
    if isinstance(body, dict) and body.get("content"):
        try:
            return base64.b64decode(body["content"]).decode("utf-8", errors="replace")
        except ValueError:
            return ""
    return ""


def gitlab_readme(fx: Fetch, p: dict) -> str:
    url = p.get("readme_url")
    if not url:
        return ""
    m = re.search(r"/-/blob/([^/]+)/(.+)$", url)
    if not m:
        return ""
    api = f"https://gitlab.com/api/v4/projects/{p['id']}/repository/files/{urllib.parse.quote(m.group(2), safe='')}?ref={urllib.parse.quote(m.group(1))}"
    body, _ = fx.get(api, pause=1.0)
    if isinstance(body, dict) and body.get("content"):
        try:
            return base64.b64decode(body["content"]).decode("utf-8", errors="replace")
        except ValueError:
            return ""
    return ""


def first_heading(md: str) -> str:
    for line in md.splitlines():
        h = HEADING.match(line)
        if h:
            return heading_text(h.group(2))
        m = re.search(r"<h1[^>]*>(.*?)</h1>", line, re.I)
        if m:
            return heading_text(m.group(1))
    return ""


def awesome_about_matrix(md: str) -> bool:
    """The README's first heading names Matrix and the text points at the Matrix protocol."""
    return "matrix" in first_heading(md).lower() and bool(re.search(r"matrix\.org|homeserver|matrix\.to|\[matrix\]", md, re.I))


# --- the run ----------------------------------------------------------------------------------

def enrich(fx: Fetch, pool: Pool, log: dict) -> None:
    """Forge metadata for rows that came only from links: GitHub through GraphQL (50 per
    query, following renames), GitLab instances and Forgejo/Gitea through REST."""
    todo = [c for c in pool.c.values() if not c.meta and c.forge == "github"]
    renamed = missing = 0
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        q = "query{" + " ".join(
            f'r{j}:repository(owner:{json.dumps(c.key.split("/")[3])},name:{json.dumps(c.key.split("/")[4])})'
            "{nameWithOwner url name description stargazerCount isArchived pushedAt repositoryTopics(first:20){nodes{topic{name}}}}"
            for j, c in enumerate(batch)) + "}"
        data = (fx.graphql(q) or {}).get("data") or {}
        for j, c in enumerate(batch):
            r = data.get(f"r{j}")
            if not r:
                c.archived, c.meta = "missing", True
                missing += 1
                continue
            topics = [n["topic"]["name"] for n in ((r.get("repositoryTopics") or {}).get("nodes") or [])]
            new = "https://github.com/" + r["nameWithOwner"].lower()
            if new != c.key:
                c = pool.rename(c.key, new)
                renamed += 1
            set_meta(c, url=r["url"], name=r["name"], description=r.get("description"), stars=r.get("stargazerCount"),
                     archived=r.get("isArchived"), pushed_at=r.get("pushedAt"), topics=topics)
    log["github_graphql"] = {"repos": len(todo), "renamed": renamed, "missing": missing}

    other = [c for c in pool.c.values() if not c.meta and c.forge in ("gitlab", "forgejo", "gitea")]
    failed = 0
    for c in other:
        host, path = c.key.split("/", 3)[2], c.key.split("/", 3)[3]
        try:
            if c.forge == "gitlab":
                p, _ = fx.get(f"https://{host}/api/v4/projects/{urllib.parse.quote(path, safe='')}", pause=3.0, max_wait=300)
                if isinstance(p, dict) and p.get("_status") == 404:
                    c.archived, c.meta = "missing", True
                elif isinstance(p, dict) and p.get("path_with_namespace"):
                    gl_meta(c, p)
            else:
                r, _ = fx.get(f"https://{host}/api/v1/repos/{path}", pause=1.0, max_wait=300)
                if isinstance(r, dict) and r.get("_status") == 404:
                    c.archived, c.meta = "missing", True
                elif isinstance(r, dict) and r.get("full_name"):
                    cb_meta(c, r)
        except Exception as e:  # noqa: BLE001 - one unreachable instance never stops the run
            failed += 1
            print(f"    {c.key}: {type(e).__name__}: {e}"[:200], file=sys.stderr)
    log["other_forges"] = {"repos": len(other), "failed": failed}


def topic_report(pool: Pool, topics: list[str]) -> list[tuple[str, int]]:
    """Topics on the kept repositories that look like Matrix topics and aren't searched yet."""
    count: Counter[str] = Counter()
    for c in pool.c.values():
        if any(s.split(":")[0] in ("gh", "gitlab", "codeberg") for s in c.sources):
            count.update({t.lower() for t in c.topics})
    return [(t, n) for t, n in count.most_common() if t not in topics and n >= 5 and ("matrix" in t or t in CORROBORATING)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vibecheck-discover", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--refresh", action="store_true", help="ignore cached API responses")
    ap.add_argument("--topic-report", action="store_true", help="print Matrix-looking topics on 5+ kept repos that aren't in TOPICS")
    ap.add_argument("--topic", action="append", default=[], help="extra topic (repeatable), for trying one before adding it to TOPICS")
    ap.add_argument("--no-twim", action="store_true")
    ap.add_argument("--no-enrich", action="store_true", help="skip forge metadata for rows found only through links")
    ap.add_argument("--site", type=Path, default=None, help="matrix.org website clone (default cache/matrix.org-site)")
    ap.add_argument("--years", type=float, default=2, help="leave out repos with no push for this many years (default 2), and archived or deleted ones")
    args = ap.parse_args(argv)

    root = (args.root or find_root(Path.cwd())).resolve()
    if os.environ.get("SSL_CERT_FILE"):
        # Only this CA bundle: on Windows, Python also loads the system's intermediate store,
        # and an expired intermediate there can break an otherwise valid chain.
        ctx = ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])
        urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)))
    fx = Fetch(root / "cache" / "discover", args.refresh)
    if "Authorization" not in fx.gh:
        print("no GH_TOKEN: the GitHub search API allows 10 requests a minute without one", file=sys.stderr)
    topics = TOPICS + [t for t in args.topic if t not in TOPICS]
    pool = Pool()
    log: dict = {"date": date.today().isoformat(), "topics": {}, "slices": [], "readme_checks": {}, "awesome": {}}
    readme = {"fetched": 0, "kept": 0, "dropped": 0}

    # GitHub topics
    for t in topics:
        if "." in t:
            continue
        slices: list = []
        items = gh_query_all(fx, f"topic:{t}", slices)
        log["slices"].extend(slices)
        kept = 0
        for i in items:
            verdict = matrix_verdict(i.get("topics"), i.get("description")) if t in NOISY else True
            if verdict is None:
                readme["fetched"] += 1
                verdict = readme_verdict(gh_readme(fx, i["full_name"]))
                readme["kept" if verdict else "dropped"] += 1
            if not verdict:
                continue
            n = normalise(i["html_url"])
            if n:
                gh_item(pool.add(n[0], n[1], f"gh:{t}"), i)
                kept += 1
        log["topics"][f"gh:{t}"] = {"results": len(items), "kept": kept, "slices": len(slices)}
        print(f"  gh:{t}: {len(items)} results, {kept} kept, {len(slices)} slices", file=sys.stderr)

    # GitLab.com and Codeberg topics
    for t in topics:
        for label, fetch, meta in (("gitlab", gitlab_topic, gl_meta), ("codeberg", codeberg_topic, cb_meta)):
            if "." in t and label != "gitlab":
                continue
            items = fetch(fx, t)
            kept = 0
            for i in items:
                ts = i.get("topics") or i.get("tag_list") or []
                if label == "codeberg" and t not in [x.lower() for x in ts] and ts:
                    continue  # Forgejo's topic search also matches topics that only contain the word
                verdict = matrix_verdict(ts, i.get("description")) if t in NOISY else True
                if verdict is None and label == "gitlab":
                    readme["fetched"] += 1
                    verdict = readme_verdict(gitlab_readme(fx, i))
                    readme["kept" if verdict else "dropped"] += 1
                if not verdict:
                    continue
                n = normalise(i.get("web_url") or i.get("html_url") or "")
                if n:
                    meta(pool.add(n[0], n[1], f"{label}:{t}"), i)
                    kept += 1
            log["topics"][f"{label}:{t}"] = {"results": len(items), "kept": kept}
            print(f"  {label}:{t}: {len(items)} results, {kept} kept", file=sys.stderr)
    log["readme_checks"] = readme

    if args.topic_report:
        for t, n in topic_report(pool, topics):
            print(f"{n}\t{t}")
        return 0

    # Awesome lists
    lists: dict[str, dict] = {"jryans/awesome-matrix": {}}
    for q in ("awesome matrix in:name", "topic:awesome-list topic:matrix"):
        for i in gh_query_all(fx, q, log["slices"]):
            lists.setdefault(i["full_name"], i)
    for full in sorted(lists, key=str.lower):
        md = gh_readme(fx, full)
        about = full == "jryans/awesome-matrix" or awesome_about_matrix(md)
        entry = {"heading": first_heading(md)[:80], "about_matrix": about}
        if about:
            own = "https://github.com/" + full.lower()
            found = {k: f for k, f in links(md) if k != own}
            for k, f in found.items():
                pool.add(k, f, f"awesome:{full.split('/')[0].lower()}")
            entry["repos"] = len(found)
        log["awesome"][full] = entry
        print(f"  awesome {full}: {'used, ' + str(entry.get('repos')) + ' repos' if about else 'not about Matrix'}", file=sys.stderr)

    # This Week in Matrix
    if not args.no_twim:
        site = args.site or root / "cache" / "matrix.org-site"
        if not (site / "content" / "blog").is_dir():
            print(f"{site} has no content/blog: clone it first (see sources/README.md)", file=sys.stderr)
            return 1
        log["twim"] = twim(pool, site)
        try:
            log["twim"]["site_commit"] = subprocess.run(["git", "-C", str(site), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
        print(f"  twim: {log['twim']}", file=sys.stderr)

    projects, _ = load_projects(root / "data" / "projects")
    known = known_repos(projects)
    if not args.no_enrich:
        enrich(fx, pool, log)
    cutoff = (date.today() - timedelta(days=round(365.25 * args.years))).isoformat()
    data = rows(pool, known, cutoff, project_names(projects))
    log["same_name_as_project"] = sum(bool(r["same_name_as"]) for r in data)
    new = [c for c in pool.c.values() if c.key not in known]
    log["known_repos"] = len(known)
    log["repos_seen"] = len(pool.c)
    log["new_repos"] = len(new)
    log["cutoff"] = cutoff
    log["left_out"] = {
        "archived": sum(c.archived == "yes" for c in new),
        "missing": sum(c.archived == "missing" for c in new),
        "no_push_since_cutoff": sum(c.archived not in ("yes", "missing") and stale(c, cutoff) for c in new),
    }
    log["candidates"] = len(data)
    log["candidates_if_3_years"] = len(rows(pool, known, (date.today() - timedelta(days=round(365.25 * 3))).isoformat()))
    log["api_calls"] = fx.calls
    write_tsv(root / "sources" / "candidates.tsv", data)
    (root / "cache" / "discover-log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{len(pool.c)} repos seen, {len(known)} known, {len(data)} candidates; {fx.calls} API calls (log: cache/discover-log.json)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
