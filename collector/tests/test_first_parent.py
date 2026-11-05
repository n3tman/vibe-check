"""git log --first-parent keeps upstream's commits out of a fork's count."""
import subprocess
from pathlib import Path

from vibecheck import gitrepo


def _git(repo: Path, *args: str) -> None:
    env = {"GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@x", "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@x",
           "HOME": str(repo), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def test_first_parent_skips_merged_upstream(tmp_path: Path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "fork base")
    _git(repo, "checkout", "-q", "-b", "upstream")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "upstream work")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "fork work")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge upstream", "upstream")
    monkeypatch.setattr(gitrepo, "REV", "HEAD")
    every = {c.message.strip() for c in gitrepo.log(repo, mailmap=False)}
    own = {c.message.strip() for c in gitrepo.log(repo, mailmap=False, first_parent=True)}
    assert every == {"fork base", "upstream work", "fork work"}
    assert own == {"fork base", "fork work"}
