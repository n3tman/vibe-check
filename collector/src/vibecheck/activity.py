"""Activity metrics from a commit list: counts, authors, bus factor, weekly and daily series,
authors per quarter, and the activity status of CLAUDE.md "Activity status"."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from .authors import AuthorIndex, ai_bot_tool, is_infra_bot
from .gitrepo import Commit

WEEKS = 52
QUARTERS = 16


def human_commits(commits: list[Commit]) -> list[Commit]:
    """Drop infrastructure bots (by author or, for translation platforms, committer)."""
    out = []
    for c in commits:
        if is_infra_bot(c.author, c.email):
            continue
        if "weblate" in (c.committer + c.cemail).lower() and "weblate" in c.message.lower():
            continue
        out.append(c)
    return out


def unique_changes(commits: list[Commit]) -> list[Commit]:
    """One commit per change: a change rebased or cherry-picked onto the branch a second time
    keeps its author, author date and subject, so later copies are dropped (the newest-first
    order of git log keeps the copy that landed last). Commits without an author date stay."""
    seen: set[tuple[str, str, str]] = set()
    out = []
    for c in commits:
        if c.adate is not None:
            key = (c.email.strip().lower(), c.adate.isoformat(), c.message.strip().split("\n", 1)[0])
            if key in seen:
                continue
            seen.add(key)
        out.append(c)
    return out


def bus_factor(counts: list[int]) -> int | None:
    """Fewest authors whose commits make up at least half of the total."""
    total = sum(counts)
    if total == 0:
        return None
    acc = 0
    for i, n in enumerate(sorted(counts, reverse=True), 1):
        acc += n
        if acc * 2 >= total:
            return i
    return len(counts)


def status(last_commit: datetime | None, authors_90d: int, archived: bool | None, now: datetime) -> str | None:
    if archived:
        return "archived"
    if last_commit is None:
        return None
    days = (now - last_commit).total_seconds() / 86400
    if days <= 30:
        return "active" if authors_90d >= 3 else "small-team"
    if days <= 180:
        return "slowing"
    if days <= 730:
        return "dormant"
    return "abandoned"


def quarter(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def last_quarters(now: datetime, n: int = QUARTERS) -> list[str]:
    y, q = now.year, (now.month - 1) // 3 + 1
    out = []
    for _ in range(n):
        out.append(f"{y}-Q{q}")
        q -= 1
        if q == 0:
            y, q = y - 1, 4
    return list(reversed(out))


class Activity:
    """Activity over one or several repos' commits (authors de-duplicated across them)."""

    def __init__(self, commits: list[Commit], now: datetime):
        self.now = now
        self.all = human_commits(unique_changes(commits))
        self.index = AuthorIndex()
        for c in self.all:
            if not ai_bot_tool(c.author, c.email):
                self.index.add(c.author, c.email)

    def _author(self, c: Commit) -> str | None:
        if ai_bot_tool(c.author, c.email):
            return None
        return self.index.key(c.author, c.email)

    def since(self, days: int) -> list[Commit]:
        cut = self.now - timedelta(days=days)
        return [c for c in self.all if c.date >= cut]

    def authors(self, commits: list[Commit]) -> set[str]:
        return {a for c in commits if (a := self._author(c))}

    def metrics(self) -> dict:
        now = self.now
        c30, c90, c365 = self.since(30), self.since(90), self.since(365)
        dates = [c.date for c in self.all]
        per_author = Counter(a for c in c365 if (a := self._author(c)))

        weekly = [0] * WEEKS
        start = now - timedelta(days=7 * WEEKS)
        for c in self.all:
            if c.date >= start:
                i = int((c.date - start).total_seconds() // (7 * 86400))
                weekly[min(i, WEEKS - 1)] += 1

        daily: Counter[str] = Counter(c.date.astimezone(timezone.utc).date().isoformat() for c in c365)

        qs = last_quarters(now)
        by_q: dict[str, set[str]] = defaultdict(set)
        for c in self.all:
            q = quarter(c.date.astimezone(timezone.utc).date())
            a = self._author(c)
            if a and q in qs:
                by_q[q].add(a)

        return {
            "first_commit": min(dates).astimezone(timezone.utc).isoformat() if dates else None,
            "last_commit": max(dates).astimezone(timezone.utc).isoformat() if dates else None,
            "commits_all": len(self.all),
            "commits_30d": len(c30),
            "commits_90d": len(c90),
            "commits_365d": len(c365),
            "authors_90d": len(self.authors(c90)),
            "authors_365d": len(self.authors(c365)),
            "authors_all": len(self.authors(self.all)),
            "bus_factor_365d": bus_factor(list(per_author.values())),
            "weekly_commits": weekly,
            "daily_commits": dict(sorted(daily.items())),
            "authors_by_quarter": {q: len(by_q.get(q, ())) for q in qs},
        }

    def last_commit(self) -> datetime | None:
        return max((c.date for c in self.all), default=None)
