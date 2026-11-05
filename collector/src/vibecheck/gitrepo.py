"""Blobless clones in cache/repos/ and the git plumbing the metrics need.

Nothing from a clone is ever executed: no checkout of hooks, no submodules, no filters, no
build. Files are read with `git show` / `git cat-file` only.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Git options that keep a clone inert whatever it contains.
SAFE = [
    "-c", "core.hooksPath=/dev/null",
    "-c", "protocol.file.allow=never",
    "-c", "protocol.ext.allow=never",
    "-c", "submodule.recurse=false",
    "-c", "core.fsmonitor=false",
    "-c", "advice.detachedHead=false",
    "-c", "filter.lfs.smudge=",
    "-c", "filter.lfs.process=",
    "-c", "filter.lfs.required=false",
    "-c", "http.userAgent=vibe-check (+https://github.com/n3tman/vibe-check) git",
]
ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "GIT_ASKPASS": "/bin/true", "LC_ALL": "C"}

REV = "origin/HEAD"


class GitError(RuntimeError):
    pass


def git(repo: Path | None, *args: str, timeout: int = 900, input: bytes | None = None, check: bool = True) -> str:
    cmd = ["git", *SAFE]
    if repo is not None:
        cmd += ["-C", str(repo)]
    cmd += list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, env=ENV, input=input)
    except subprocess.TimeoutExpired as e:
        raise GitError(f"git {args[0]} timed out after {timeout}s") from e
    if check and r.returncode != 0:
        msg = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise GitError(f"git {args[0]} failed: {msg[-1] if msg else r.returncode}")
    return r.stdout.decode("utf-8", "replace")


def cache_dir_for(url: str, root: Path) -> Path:
    u = urlparse(url)
    path = re.sub(r"\.git$", "", u.path.strip("/"))
    safe = re.sub(r"[^A-Za-z0-9._/-]", "_", path).replace("..", "_")
    return root / (u.hostname or "unknown") / safe


def clone_or_fetch(url: str, dest: Path, fetch: bool = True) -> None:
    """Blobless clone, or fetch when the clone exists. `origin/HEAD` follows the remote's
    default branch."""
    if (dest / ".git").exists():
        if fetch:
            git(dest, "fetch", "--quiet", "--prune", "--tags", "--force", "--filter=blob:none", "origin")
            git(dest, "remote", "set-head", "origin", "--auto", check=False)
        return
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(None, "clone", "--quiet", "--filter=blob:none", "--no-checkout", "--no-recurse-submodules", url, str(dest), timeout=3600)


def head_info(repo: Path) -> tuple[str, str]:
    sha = git(repo, "rev-parse", REV).strip()
    ref = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False).strip()
    branch = ref.removeprefix("refs/remotes/origin/") if ref else ""
    return sha, branch


@dataclass
class Commit:
    sha: str
    author: str
    email: str
    committer: str
    cemail: str
    date: datetime  # committer date: when the change landed on the branch
    message: str


_SEP = "\x1e"


def log(repo: Path, mailmap: bool) -> list[Commit]:
    """Every non-merge commit on the default branch, newest first."""
    args = []
    if mailmap:
        args = ["-c", f"mailmap.blob={REV}:.mailmap"]
    out = git(
        repo,
        *args,
        "log",
        REV,
        "--no-merges",
        "--use-mailmap",
        f"--format=%H%x00%aN%x00%aE%x00%cN%x00%cE%x00%cI%x00%B{_SEP}",
    )
    commits = []
    for rec in out.split(_SEP):
        rec = rec.lstrip("\n")
        if not rec:
            continue
        parts = rec.split("\x00", 6)
        if len(parts) < 7:
            continue
        sha, an, ae, cn, ce, cd, body = parts
        commits.append(Commit(sha, an, ae, cn, ce, datetime.fromisoformat(cd), body))
    return commits


def ls_tree(repo: Path) -> list[str]:
    out = git(repo, "ls-tree", "-r", "--name-only", "-z", REV)
    return [p for p in out.split("\x00") if p]


def show(repo: Path, path: str, max_bytes: int = 2_000_000) -> str | None:
    """A file at HEAD (fetched on demand); None when missing or too big."""
    size = git(repo, "cat-file", "-s", f"{REV}:{path}", check=False).strip()
    if not size.isdigit() or int(size) > max_bytes:
        return None
    try:
        return git(repo, "show", f"{REV}:{path}", timeout=300)
    except GitError:
        return None


def prefetch(repo: Path, paths: list[str]) -> None:
    """Fetch the blobs of several paths in one round trip instead of one per file."""
    if not paths:
        return
    out = git(repo, "ls-tree", "-z", REV, "--", *paths, check=False)
    oids = []
    for entry in out.split("\x00"):
        meta = entry.split("\t", 1)[0].split()
        if len(meta) == 3 and meta[1] == "blob":
            oids.append(meta[2])
    if oids:
        missing = git(repo, "cat-file", "--batch-check=%(objectname)", input="\n".join(oids).encode(), check=False)
        need = [line.split()[0] for line in missing.splitlines() if line.endswith("missing")]
        if need:
            git(repo, "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "--filter=blob:none", "origin", *need, check=False, timeout=600)


def tags(repo: Path) -> list[tuple[str, datetime]]:
    """Tags newest first, by tagger date (or commit date for lightweight tags)."""
    out = git(repo, "for-each-ref", "refs/tags", "--sort=-creatordate", "--format=%(refname:short)%00%(creatordate:iso-strict)")
    res = []
    for line in out.splitlines():
        name, _, d = line.partition("\x00")
        if d:
            try:
                res.append((name, datetime.fromisoformat(d)))
            except ValueError:
                pass
    return res
