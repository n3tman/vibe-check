"""The AI scan: agent files, attributed commits, AI bot authors and AI workflows.

What counts is defined in CLAUDE.md "AI rubric". Attribution is a lower bound: most AI use
leaves no trace in a repository.
"""

from __future__ import annotations

import posixpath
import re

# Tool names as they appear in trailers and "Generated with" lines.
_TOOLS: dict[str, str] = {
    "claude": r"claude|anthropic",
    "copilot": r"copilot",
    "codex": r"codex|chatgpt|openai|gpt-?[345o]",
    "gemini": r"gemini|google-labs-jules|jules",
    "cursor": r"cursor(agent)?",
    "devin": r"devin",
    "aider": r"aider",
    "windsurf": r"windsurf|codeium",
    "cline": r"\bcline\b|roo ?code",
    "amp": r"\bamp\b|ampcode",
    "opencode": r"opencode",
    "junie": r"junie",
    "qwen": r"qwen",
    "kiro": r"\bkiro\b",
    "amazon-q": r"amazon q\b|codewhisperer",
    "tabnine": r"tabnine",
    "openhands": r"openhands",
    "coderabbit": r"coderabbit",
}
_TOOL_RES = {k: re.compile(v, re.I) for k, v in _TOOLS.items()}

# Trailers whose value names a tool: Co-authored-by, Assisted-by, Generated-by, …
_TRAILER = re.compile(
    r"^\s*(co-authored-by|assisted-by|generated-by|ai-assisted-by|coded-by|made-with)\s*:\s*(.+)$",
    re.I | re.M,
)
_GENERATED = re.compile(
    r"(generated|created|written|made|authored|co-authored|assisted)\s+(with|by|using|via)\s+"
    r"\[?(claude( code)?|copilot|chatgpt|codex|cursor|gemini( cli)?|aider|devin|windsurf|amp|"
    r"opencode|jules|junie|openhands|kiro|qwen code)\b",
    re.I,
)
_AMP_THREAD = re.compile(r"^\s*amp-thread(-id)?\s*:", re.I | re.M)


def tool_in(text: str) -> str | None:
    for tool, pat in _TOOL_RES.items():
        if pat.search(text):
            return tool
    return None


def commit_ai_tools(message: str) -> set[str]:
    """AI tools a commit message credits, from trailers and "Generated with" lines."""
    found: set[str] = set()
    for _key, value in _TRAILER.findall(message):
        t = tool_in(value)
        if t:
            found.add(t)
    for m in _GENERATED.finditer(message):
        t = tool_in(m.group(3))
        if t:
            found.add(t)
    if _AMP_THREAD.search(message):
        found.add("amp")
    return found


# Agent files, by path. Each entry: (kind, test on the path).
_AGENT_BASENAMES = {
    "claude.md": "claude",
    "claude.local.md": "claude",
    "agents.md": "agents.md",
    "agent.md": "agents.md",
    "gemini.md": "gemini",
    ".cursorrules": "cursor",
    ".windsurfrules": "windsurf",
    ".clinerules": "cline",
    ".roomodes": "cline",
    "llms.txt": "llms.txt",
    "llms-full.txt": "llms.txt",
    ".coderabbit.yaml": "coderabbit",
    ".coderabbit.yml": "coderabbit",
    "copilot-instructions.md": "copilot",
    ".aider.conf.yml": "aider",
    ".aiderignore": "aider",
    ".aider.chat.history.md": "aider",
    ".mcp.json": "mcp",
    ".greptile.json": "greptile",
}
_AGENT_DIRS = {
    ".claude": "claude",
    ".cursor": "cursor",
    ".codex": "codex",
    ".continue": "continue",
    ".windsurf": "windsurf",
    ".clinerules": "cline",
    ".roo": "cline",
    ".junie": "junie",
    ".kiro": "kiro",
    ".gemini": "gemini",
    ".amazonq": "amazon-q",
    ".opencode": "opencode",
    ".augment": "augment",
}
_AGENT_GITHUB_DIRS = {"instructions": "copilot", "prompts": "copilot", "chatmodes": "copilot", "agents": "copilot"}
_SKIP_DIRS = re.compile(r"(^|/)(node_modules|vendor|third[_-]party|external|deps)/", re.I)


def agent_file_kind(path: str) -> str | None:
    if _SKIP_DIRS.search(path):
        return None
    parts = path.split("/")
    base = parts[-1].lower()
    if base in _AGENT_BASENAMES:
        return _AGENT_BASENAMES[base]
    if base.startswith(".aider"):
        return "aider"
    for i, part in enumerate(parts[:-1]):
        p = part.lower()
        if p in _AGENT_DIRS:
            return _AGENT_DIRS[p]
        if p == ".github" and i + 1 < len(parts) - 1 and parts[i + 1].lower() in _AGENT_GITHUB_DIRS:
            return _AGENT_GITHUB_DIRS[parts[i + 1].lower()]
    return None


def find_agent_files(paths: list[str], limit: int = 40) -> list[dict]:
    """Agent files from a tree listing; a directory like .claude/ is reported once."""
    out: list[dict] = []
    seen_dirs: set[str] = set()
    for path in paths:
        kind = agent_file_kind(path)
        if not kind:
            continue
        parts = path.split("/")
        shown = path
        for i, part in enumerate(parts[:-1]):
            if part.lower() in _AGENT_DIRS or (
                part.lower() == ".github" and i + 1 < len(parts) - 1 and parts[i + 1].lower() in _AGENT_GITHUB_DIRS
            ):
                end = i + 1 if part.lower() in _AGENT_DIRS else i + 2
                shown = "/".join(parts[:end]) + "/"
                break
        if shown.endswith("/"):
            if shown in seen_dirs:
                continue
            seen_dirs.add(shown)
        out.append({"path": shown, "kind": kind})
        if len(out) >= limit:
            break
    return out


WORKFLOW_PATTERNS: dict[str, re.Pattern[str]] = {
    "claude-code-action": re.compile(r"anthropics/claude-code(-base)?-action", re.I),
    "codex-action": re.compile(r"openai/codex-action", re.I),
    "gemini-cli-action": re.compile(r"google-github-actions/run-gemini-cli|google-gemini/gemini-cli-action", re.I),
    "copilot": re.compile(r"github/copilot|copilot-review|copilot-swe-agent", re.I),
    "coderabbit": re.compile(r"coderabbitai/", re.I),
    "pr-agent": re.compile(r"(codium-ai|qodo-ai)/pr-agent", re.I),
    "ai-review-action": re.compile(
        r"ai-pr-reviewer|ai-codereviewer|chatgpt-codereview|code-review-gpt|gpt-review|actions/ai-inference|"
        r"sweepai/|cursor-agent|amp-action|opencode",
        re.I,
    ),
    "llm-api-key": re.compile(r"\b(ANTHROPIC|OPENAI|GEMINI|CLAUDE_CODE_OAUTH)_(API_KEY|TOKEN)\b"),
}


def is_workflow_path(path: str) -> bool:
    p = path.lower()
    if p in (".gitlab-ci.yml", ".woodpecker.yml", ".woodpecker.yaml", ".drone.yml", ".build.yml"):
        return True
    d = posixpath.dirname(p)
    if d in (".github/workflows", ".forgejo/workflows", ".gitea/workflows", ".woodpecker", ".builds", ".gitlab/ci"):
        return p.endswith((".yml", ".yaml"))
    return False


def scan_workflow(text: str) -> list[str]:
    return [name for name, pat in WORKFLOW_PATTERNS.items() if pat.search(text)]


def suggest_dev_usage(agent_files: int, share: float | None, attributed: int, workflows: int, ai_bot_commits: int) -> str:
    """The rubric's thresholds, as a suggestion for the research lanes.

    regular: 5 % or more of last-year commits attributed. occasional: 1 to 4 %, or AI
    review/agent workflows. Below 1 % but at least one attributed commit is also reported
    as occasional (the rubric has no lower step): the share is shown next to it.
    """
    if share is not None and share >= 0.05:
        return "regular"
    if attributed > 0 or workflows > 0 or ai_bot_commits > 0:
        return "occasional"
    if agent_files > 0:
        return "config-only"
    return "none-found"
