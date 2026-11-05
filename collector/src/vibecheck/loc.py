"""Lines of code with scc on a shallow checkout. scc only reads files; the scanned repo is
never built or run. The scc binary is a release download, checked against its SHA-256."""

from __future__ import annotations

import hashlib
import io
import json
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .gitrepo import git

SCC_VERSION = "3.5.0"
# Release assets per platform and their SHA-256, pinned here (copied from the v3.5.0 release's
# checksums.txt and checked against a download on 2026-11-05), so a changed asset is refused.
SCC_ASSETS = {
    ("Linux", "x86_64"): ("scc_Linux_x86_64.tar.gz", "6c31f4d0cf3b7a8c5ca910fa4e451949434798f6541ec5dea4b83f4973e13772"),
    ("Linux", "aarch64"): ("scc_Linux_arm64.tar.gz", "64446b1ca954aa1ac34984bbb4f098f46e6c69c84d64a7d096275ea6e50461eb"),
    ("Darwin", "x86_64"): ("scc_Darwin_x86_64.tar.gz", "33fee1db983a6d22297d5f4e41bca25438c8a09d5c7c558acbfb5f9cd4deb19b"),
    ("Darwin", "arm64"): ("scc_Darwin_arm64.tar.gz", "0e967d77ad564fa77bc5ed157d4e04bc6b56c5619edef317e5c99b15c9fca9d2"),
}


def ensure_scc(bin_dir: Path) -> Path | None:
    found = shutil.which("scc")
    if found:
        return Path(found)
    target = bin_dir / f"scc-{SCC_VERSION}"
    if target.exists():
        return target
    entry = SCC_ASSETS.get((platform.system(), platform.machine()))
    if not entry:
        return None
    asset, want = entry
    base = f"https://github.com/boyter/scc/releases/download/v{SCC_VERSION}/"
    ua = {"User-Agent": "vibe-check (+https://github.com/n3tman/vibe-check)"}
    try:
        with urllib.request.urlopen(urllib.request.Request(base + asset, headers=ua), timeout=120) as r:
            data = r.read()
    except Exception:  # noqa: BLE001
        return None
    if hashlib.sha256(data).hexdigest() != want:
        return None  # fail closed: never run a binary whose checksum is not the pinned one
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        member = next((m for m in tf.getmembers() if m.name.endswith("scc") and m.isfile()), None)
        if member is None:
            return None
        f = tf.extractfile(member)
        assert f
        bin_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f.read())
    target.chmod(0o755)
    return target


# scc "languages" that are prose, data or packaging rather than code; left out of lines of code
# and of the language shares, as forges' language bars leave them out.
NON_CODE = {
    "License", "Markdown", "Plain Text", "ReStructuredText", "AsciiDoc", "Org", "TeX", "Gemini",
    "JSON", "JSONL", "YAML", "TOML", "XML", "CSV", "TSV", "INI", "Properties File", "SVG", "Gettext",
    "XML Schema", "Docker ignore", "gitignore", "gitattributes", "Patch", "Autoconf",
    "Freemarker Template", "Mustache", "Handlebars",
}


def count(url: str, scc: Path, tmp_root: Path) -> tuple[dict[str, int] | None, dict[str, int] | None]:
    """(code lines by language, bytes by language) for the default branch's tip."""
    tmp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
        dest = Path(tmp) / "src"
        git(None, "clone", "--quiet", "--depth", "1", "--single-branch", "--no-recurse-submodules", url, str(dest), timeout=1800)
        shutil.rmtree(dest / ".git", ignore_errors=True)
        r = subprocess.run(
            [str(scc), "--format", "json", "--no-cocomo", "--no-complexity", "--exclude-dir", "node_modules,vendor,.git", str(dest)],
            capture_output=True,
            timeout=900,
        )
        if r.returncode != 0:
            return None, None
        data = json.loads(r.stdout or b"[]")
    code = [d for d in data if d.get("Name") not in NON_CODE] or data  # a repo of only YAML stays YAML
    lines = {d["Name"]: int(d["Code"]) for d in code if d.get("Code")}
    sizes = {d["Name"]: int(d["Bytes"]) for d in code if d.get("Bytes")}
    lines = dict(sorted(lines.items(), key=lambda kv: -kv[1]))
    return lines, sizes
