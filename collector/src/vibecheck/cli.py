"""vibecheck-collect: compute data/metrics/<slug>.json for every project file.

  uv run --project collector vibecheck-collect                  # every project
  uv run --project collector vibecheck-collect --fixtures       # fixtures/ instead of data/
  uv run --project collector vibecheck-collect --only cinny --only synapse
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from . import VERSION, activity, authors, loc
from .collect import Context, collect_project, write_if_changed
from .forges import now_utc


def find_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "PLAN.md").exists() and (p / "CLAUDE.md").exists():
            return p
    return start


def load_projects(projects_dir: Path) -> tuple[list[dict], list[str]]:
    projects, errors = [], []
    for f in sorted(projects_dir.glob("**/*.yaml")):
        try:
            doc = yaml.safe_load(f.read_text())
        except yaml.YAMLError as e:
            errors.append(f"{f}: YAML error: {e}")
            continue
        if not isinstance(doc, dict) or not doc.get("slug"):
            errors.append(f"{f}: no slug")
            continue
        if not isinstance(doc.get("repos", []), list):
            errors.append(f"{f}: repos is not a list")
            continue
        doc["_file"] = str(f)
        projects.append(doc)
    return projects, errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="vibecheck-collect", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=None, help="repository root (default: found from the current directory)")
    ap.add_argument("--fixtures", action="store_true", help="read fixtures/projects, write fixtures/metrics")
    ap.add_argument("--only", action="append", default=[], metavar="SLUG", help="only these slugs (repeatable)")
    ap.add_argument("--since-cache", action="store_true", help="reuse clones in cache/repos without fetching (clones missing ones)")
    ap.add_argument("--max-age", type=float, default=None, metavar="HOURS", help="skip projects whose metrics are newer than this")
    ap.add_argument("--per-host", type=int, default=1, help="concurrent requests per forge host (default 1)")
    ap.add_argument("--jobs", type=int, default=4, help="projects in flight at once (default 4)")
    ap.add_argument("--no-api", action="store_true", help="skip forge APIs")
    ap.add_argument("--no-loc", action="store_true", help="skip lines of code (no shallow checkout, no scc)")
    args = ap.parse_args(argv)

    root = (args.root or find_root(Path.cwd())).resolve()
    base = root / ("fixtures" if args.fixtures else "data")
    projects, errors = load_projects(base / "projects")
    out_dir = base / "metrics"
    if args.only:
        wanted = set(args.only)
        projects = [p for p in projects if p["slug"] in wanted]
        missing = wanted - {p["slug"] for p in projects}
        for m in sorted(missing):
            errors.append(f"--only {m}: no project file with that slug")

    ctx = Context(root=root, now=now_utc(), fetch=not args.since_cache, api=not args.no_api, loc=not args.no_loc, per_host=max(1, args.per_host))
    if ctx.loc:
        ctx.scc = loc.ensure_scc(root / "cache" / "bin")
        if ctx.scc is None:
            print("scc unavailable: lines of code skipped", file=sys.stderr)

    todo = []
    for p in projects:
        f = out_dir / f"{p['slug']}.json"
        if args.max_age is not None and f.exists():
            try:
                fetched = datetime.fromisoformat(json.loads(f.read_text())["fetched_at"])
                if ctx.now - fetched < timedelta(hours=args.max_age):
                    continue
            except (KeyError, ValueError, json.JSONDecodeError):
                pass
        todo.append(p)

    started = time.time()
    summary = {"projects": len(todo), "written": 0, "unchanged": 0, "repos_ok": 0, "repos_failed": [], "api_errors": [], "project_errors": list(errors)}
    print(f"collector v{VERSION}: {len(todo)} projects from {base / 'projects'}", file=sys.stderr)

    def run(p: dict) -> tuple[dict, dict | None, str | None]:
        try:
            return p, collect_project(p, ctx), None
        except Exception:  # noqa: BLE001 - one bad project never stops the run
            return p, None, traceback.format_exc(limit=3)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for fut in as_completed([pool.submit(run, p) for p in todo]):
            p, data, err = fut.result()
            if err or data is None:
                summary["project_errors"].append(f"{p['slug']}: {err}")
                print(f"  ✗ {p['slug']}: crashed", file=sys.stderr)
                continue
            for r in data["repos"]:
                if r["ok"]:
                    summary["repos_ok"] += 1
                    if r.get("api_error"):
                        summary["api_errors"].append(f"{r['url']}: {r['api_error']}")
                else:
                    summary["repos_failed"].append(f"{r['url']}: {r['error']}")
            changed = write_if_changed(out_dir / f"{p['slug']}.json", data)
            summary["written" if changed else "unchanged"] += 1
            st = (data.get("combined") or {}).get("status") or "no repo"
            print(f"  ✓ {p['slug']}: {len(data['repos'])} repos, {st}{'' if changed else ' (unchanged)'}", file=sys.stderr)

    summary["seconds"] = round(time.time() - started)
    summary["http_calls"] = ctx.http.calls
    meta = {
        "collector_version": VERSION,
        "run_at": ctx.now.isoformat(timespec="seconds"),
        "bot_names": authors.BOT_NAMES,
        "ai_bot_tools": sorted(authors.AI_BOT_PATTERNS),
        "weeks": activity.WEEKS,
        "summary": {k: v for k, v in summary.items() if k != "project_errors"} | {"project_errors": [e.splitlines()[0] for e in summary["project_errors"]]},
    }
    if not args.only and not args.max_age:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "_collector.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")

    print(
        f"\ndone in {summary['seconds']}s: {summary['projects']} projects, {summary['written']} written, "
        f"{summary['unchanged']} unchanged; repos ok {summary['repos_ok']}, failed {len(summary['repos_failed'])}; "
        f"API errors {len(summary['api_errors'])}; {ctx.http.calls} API calls",
        file=sys.stderr,
    )
    for title, items in (("failed repos", summary["repos_failed"]), ("API errors", summary["api_errors"]), ("project errors", summary["project_errors"])):
        if items:
            print(f"{title}:", file=sys.stderr)
            for i in items:
                print(f"  - {i}", file=sys.stderr)
    return 1 if summary["project_errors"] and not summary["repos_ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
