"""Commit authors: the bot filter and identity de-duplication.

Two kinds of non-human authors are told apart:
- infrastructure bots (dependency updates, translation platforms, CI): their commits are
  dropped from every count;
- AI agent bots (copilot-swe-agent, claude[bot], …): their commits are real changes and stay
  in the commit counts and in the AI scan, but they are never counted as authors.
"""

from __future__ import annotations

import re

# Infrastructure bots. Matched against "name <email>", case-insensitive. The site's
# methodology page lists these names (`BOT_NAMES`), so keep the two in step.
BOT_NAMES = [
    "dependabot",
    "renovate",
    "renovate-bot",
    "weblate",
    "hosted weblate",
    "github-actions",
    "gitlab-bot",
    "forgejo-actions",
    "pre-commit-ci",
    "mergify",
    "snyk-bot",
    "greenkeeper",
    "imgbot",
    "allcontributors",
    "semantic-release-bot",
    "release-please",
    "codecov",
    "deepsource-autofix",
    "transifex",
    "crowdin",
    "translate bot",
    "translations bot",
    "localazy",
    "pyup-bot",
    "depfu",
    "stale",
    "copybara",
]

_INFRA_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"dependabot",
        r"renovate(\[bot\]|-bot|@|\b)",
        r"weblate",
        r"github-actions",
        r"action@github\.com",
        r"actions@github\.com",
        r"forgejo-actions",
        r"gitlab-bot",
        r"pre-commit-ci",
        r"mergify",
        r"snyk-bot",
        r"greenkeeper",
        r"imgbot",
        r"allcontributors",
        r"semantic-release-bot",
        r"release-please",
        r"codecov",
        r"deepsource-autofix",
        r"transifex",
        r"crowdin",
        r"translat\w* ?bot",
        r"localazy",
        r"pyup-bot",
        r"depfu",
        r"copybara",
    ]
]

# AI agents that author commits themselves. Matched against "name <email>".
AI_BOT_PATTERNS: dict[str, re.Pattern[str]] = {
    "copilot": re.compile(
        r"copilot-swe-agent|\bCopilot <\d+\+Copilot@users\.noreply\.github\.com>|copilot\[bot\]", re.I
    ),
    "claude": re.compile(r"claude\[bot\]|claude-code\[bot\]|<noreply@anthropic\.com>", re.I),
    "devin": re.compile(r"devin-ai-integration|devin\[bot\]", re.I),
    "jules": re.compile(r"google-labs-jules", re.I),
    "codex": re.compile(r"chatgpt-codex-connector|codex\[bot\]|<codex@openai\.com>", re.I),
    "cursor": re.compile(r"cursor(agent)?\[bot\]|<cursoragent@cursor\.com>", re.I),
    "gemini": re.compile(r"gemini-code-assist|gemini-cli\[bot\]", re.I),
    "aider": re.compile(r"\(aider\)\s*<|<noreply@aider\.chat>", re.I),
    "openhands": re.compile(r"openhands(-agent|\[bot\])", re.I),
    "sweep": re.compile(r"sweep-ai\[bot\]", re.I),
    "coderabbit": re.compile(r"coderabbitai\[bot\]", re.I),
    "amp": re.compile(r"<amp@ampcode\.com>", re.I),
}

_GENERIC_BOT = re.compile(r"\[bot\]|(^|[\s._-])bot(\s|<|$)|<bot@|-bot@|noreply\+bot", re.I)


def ident(name: str, email: str) -> str:
    return f"{name} <{email}>"


def ai_bot_tool(name: str, email: str) -> str | None:
    """The AI tool behind a bot author, or None."""
    s = ident(name, email)
    for tool, pat in AI_BOT_PATTERNS.items():
        if pat.search(s):
            return tool
    return None


def is_infra_bot(name: str, email: str) -> bool:
    """True for dependency, translation, CI and other bots (never for AI agents)."""
    if ai_bot_tool(name, email):
        return False
    s = ident(name, email)
    if any(p.search(s) for p in _INFRA_PATTERNS):
        return True
    return bool(_GENERIC_BOT.search(s))


def is_bot_login(login: str | None) -> bool:
    """For forge comments: a login that looks like a bot."""
    if not login:
        return True
    return bool(re.search(r"\[bot\]$|bot$|-bot\b|^ghost$", login, re.I))


_NOREPLY = re.compile(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", re.I)
_WEAK_NAMES = {"", "root", "user", "admin", "unknown", "ubuntu", "localhost", "none", "github", "you"}
_WEAK_EMAIL = re.compile(r"^(root|user|admin|you)@|@localhost|@\(none\)|@example\.com$", re.I)


def _norm_email(email: str) -> str:
    email = email.strip().lower()
    m = _NOREPLY.match(email)
    if m:
        return f"gh:{m.group(1)}"
    return email


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


class AuthorIndex:
    """Union-find over author identities: two commits share an author when they share an
    email (GitHub noreply addresses reduced to the login) or a full name. Weak names and
    emails (root, localhost, …) never join identities on their own."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def _find(self, k: str) -> str:
        p = self._parent.setdefault(k, k)
        if p != k:
            p = self._find(p)
            self._parent[k] = p
        return p

    def _union(self, a: str, b: str) -> None:
        ra, rb = self._find(a), self._find(b)
        if ra != rb:
            self._parent[max(ra, rb)] = min(ra, rb)

    def _keys(self, name: str, email: str) -> list[str]:
        keys = []
        e = _norm_email(email)
        if e and not _WEAK_EMAIL.search(email):
            keys.append("e:" + e)
        n = _norm_name(name)
        if n not in _WEAK_NAMES and len(n) >= 3:
            keys.append("n:" + n)
        if not keys:
            keys.append("x:" + e + "|" + n)
        return keys

    def add(self, name: str, email: str) -> None:
        keys = self._keys(name, email)
        for k in keys[1:]:
            self._union(keys[0], k)
        self._find(keys[0])

    def key(self, name: str, email: str) -> str:
        """Canonical author id; call after every identity has been added."""
        return self._find(self._keys(name, email)[0])
