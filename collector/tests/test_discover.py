from pathlib import Path

import pytest

from vibecheck import discover as d


# --- URL normalisation ------------------------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/Cinnyapp/Cinny", ("https://github.com/cinnyapp/cinny", "github")),
        ("https://www.github.com/cinnyapp/cinny.git", ("https://github.com/cinnyapp/cinny", "github")),
        ("https://github.com/matrix-org/synapse/pull/123#issuecomment-1", ("https://github.com/matrix-org/synapse", "github")),
        ("https://github.com/mujx/nheko).", ("https://github.com/mujx/nheko", "github")),
        ("http://github.com/a/b/tree/main/docs", ("https://github.com/a/b", "github")),
        ("https://gitlab.com/Group/Sub/Project/-/issues/4", ("https://gitlab.com/group/sub/project", "gitlab")),
        ("https://gitlab.com/group/project/issues/4", ("https://gitlab.com/group/project", "gitlab")),
        ("https://gitlab.gnome.org/World/fractal", ("https://gitlab.gnome.org/world/fractal", "gitlab")),
        ("https://codeberg.org/Owner/Repo/src/branch/main/README.md", ("https://codeberg.org/owner/repo", "forgejo")),
        ("https://git.sr.ht/~user/repo/tree", ("https://git.sr.ht/~user/repo", "sourcehut")),
    ],
)
def test_normalise(url, expected):
    assert d.normalise(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/zecakeh",  # a profile
        "https://github.com/sponsors/someone",
        "https://github.com/orgs/matrix-org/projects/1",
        "https://gitlab.com/users/someone",
        "https://codeberg.org/explore/repos",
        "https://git.sr.ht/user/repo",  # sourcehut owners start with ~
        "https://matrix.org/blog/",
        "https://cgit.drupalcode.org/matrix_api",
        "mailto:someone@github.com",
    ],
)
def test_normalise_rejects(url):
    assert d.normalise(url) is None


def test_links_in_markdown_and_html():
    text = (
        '[nheko](https://github.com/Nheko-Reborn/nheko) and <a href="https://gitlab.com/x/y">y</a>, '
        "see https://github.com/x/z/releases/tag/v1."
    )
    assert [k for k, _ in d.links(text)] == [
        "https://github.com/nheko-reborn/nheko", "https://gitlab.com/x/y", "https://github.com/x/z",
    ]


# --- noise filter -----------------------------------------------------------------------

@pytest.mark.parametrize(
    "topics,text,verdict",
    [
        (["matrix", "matrix-bot"], "A bot", True),  # another Matrix topic
        (["matrix", "chat"], "A client for the Matrix protocol", True),
        (["matrix"], "Bridge between Matrix and IRC", True),
        (["element", "vue"], "Simple chat on matrix.org rooms", True),
        (["matrix"], "Telegram, Discord and Matrix relay", True),
        (["matrix", "linear-algebra"], "Fast matrix multiplication in C++", False),
        (["element", "vue"], "Admin template built on Element UI", False),
        (["matrix", "synapse"], "Worker config", True),  # synapse corroborates, isn't searched
        (["matrix", "matrix-library"], "A tiny matrix library", False),
        (["matrix", "matrix-rain"], "Custom words in matrix rain", False),
        (["matrix"], "Simple library for matrix operations", False),
        (["matrix"], "", None),
        (["matrix"], None, None),
    ],
)
def test_matrix_verdict(topics, text, verdict):
    assert d.matrix_verdict(topics, text) is verdict


def test_awesome_about_matrix():
    assert d.awesome_about_matrix("# Awesome Matrix\n\nClients for https://matrix.org rooms")
    assert not d.awesome_about_matrix("# Awesome Matrix\n\nLinear algebra libraries")
    assert not d.awesome_about_matrix("# Awesome Rust\n\nSee matrix.org")


# --- merging ----------------------------------------------------------------------------

def test_pool_merges_sources_and_drops_known():
    pool = d.Pool()
    pool.add("https://github.com/a/b", "github", "gh:matrix-bot", stars=5, description="Bot")
    pool.add("https://github.com/a/b", "github", "awesome:jryans")
    pool.twim("https://github.com/a/b", "github", "2024-01-05", "B bot")
    pool.twim("https://github.com/a/b", "github", "2025-03-14", "B bot")
    pool.add("https://github.com/c/d", "github", "gh:matrix-client", stars=50)
    pool.add("https://github.com/known/one", "github", "gh:matrix-client", stars=999)
    rows = d.rows(pool, {"https://github.com/known/one"})
    assert [r["url"] for r in rows] == ["https://github.com/a/b", "https://github.com/c/d"]
    ab = rows[0]
    assert ab["found"] == 3
    assert ab["sources"] == "awesome:jryans; gh:matrix-bot; twim:2 posts 2024-01-05..2025-03-14"
    assert (ab["twim_last"], ab["twim_posts"], ab["twim_heading"]) == ("2025-03-14", 2, "B bot")


def test_rows_leave_out_stale_repos():
    pool = d.Pool()
    pool.add("https://github.com/a/new", "github", "gh:matrix-bot", pushed_at="2025-06-01T00:00:00Z", archived=False)
    pool.add("https://github.com/a/old", "github", "gh:matrix-bot", pushed_at="2022-01-01T00:00:00Z", archived=False)
    pool.add("https://github.com/a/archived", "github", "gh:matrix-bot", pushed_at="2026-01-01T00:00:00Z", archived=True)
    pool.add("https://github.com/a/gone", "github", "awesome:jryans").archived = "missing"
    pool.add("https://git.sr.ht/~a/undated", "sourcehut", "awesome:jryans")
    urls = {r["url"] for r in d.rows(pool, set(), "2024-11-05")}
    assert urls == {"https://github.com/a/new", "https://git.sr.ht/~a/undated"}


def test_same_name_as_flags_forks_and_moves():
    projects = [{"slug": "fractal", "name": "Fractal", "repos": [{"url": "https://github.com/GNOME/fractal"}, {"url": "https://github.com/x/app"}]}]
    names = d.project_names(projects)
    assert names == {"fractal": "fractal"}
    pool = d.Pool()
    pool.add("https://gitlab.gnome.org/world/fractal", "gitlab", "twim", name="Fractal")
    pool.add("https://github.com/y/other", "github", "gh:matrix-bot")
    got = {r["url"]: r["same_name_as"] for r in d.rows(pool, set(), None, names)}
    assert got == {"https://gitlab.gnome.org/world/fractal": "fractal", "https://github.com/y/other": ""}


def test_gitlab_token_goes_to_gitlab_com_only(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-x")
    sent = {}
    monkeypatch.setattr(d.Http, "get", lambda self, url, headers=None, tries=3: (sent.__setitem__(url, headers or {}), ({}, {}))[1])
    fx = d.Fetch(tmp_path, refresh=True)
    fx.get("https://gitlab.com/api/v4/projects/1")
    fx.get("https://gitlab.gnome.org/api/v4/projects/1")
    assert sent["https://gitlab.com/api/v4/projects/1"]["PRIVATE-TOKEN"] == "glpat-x"
    assert "PRIVATE-TOKEN" not in sent["https://gitlab.gnome.org/api/v4/projects/1"]


def test_rename_merges_rows():
    pool = d.Pool()
    pool.twim("https://github.com/mujx/nheko", "github", "2018-04-20", "nheko")
    pool.add("https://github.com/nheko-reborn/nheko", "github", "gh:matrix-client")
    c = pool.rename("https://github.com/mujx/nheko", "https://github.com/nheko-reborn/nheko")
    assert list(pool.c) == ["https://github.com/nheko-reborn/nheko"]
    assert c.sources == {"gh:matrix-client"} and c.twim == {"2018-04-20": "nheko"}


def test_known_repos_reads_urls_and_homepages():
    projects = [
        {"slug": "x", "homepage": "https://x.example", "repos": [{"url": "https://GitHub.com/X/Y.git"}]},
        {"slug": "z", "homepage": "https://codeberg.org/z/z", "repos": []},
    ]
    assert d.known_repos(projects) == {"https://github.com/x/y", "https://codeberg.org/z/z"}


def test_write_tsv_flattens_text(tmp_path: Path):
    pool = d.Pool()
    pool.add("https://github.com/a/b", "github", "gh:matrix", description="two\tparts\nand a line")
    f = tmp_path / "c.tsv"
    d.write_tsv(f, d.rows(pool, set()))
    lines = f.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == d.COLUMNS
    assert lines[1].split("\t")[3] == "two parts and a line"


# --- This Week in Matrix ------------------------------------------------------------------

POST = '''+++
title = "This Week in Matrix 2023-06-16"
date = "2023-06-16"

[taxonomies]
category = ["This Week in Matrix"]
+++

## Dept of Clients 📱

### Nheko 🐱

Release out: [v0.11](https://github.com/Nheko-Reborn/nheko/releases/tag/v0.11.3).

### [Fractal](https://gitlab.gnome.org/World/fractal) ✨

More in <a href="https://gitlab.gnome.org/World/fractal/-/merge_requests/1">this MR</a>.
'''


def test_twim_post():
    day, found = d.twim_post(POST, "16-twim.md")
    assert day == "2023-06-16"
    assert found == [
        ("https://github.com/nheko-reborn/nheko", "github", "Nheko"),
        ("https://gitlab.gnome.org/world/fractal", "gitlab", "Fractal"),
        ("https://gitlab.gnome.org/world/fractal", "gitlab", "Fractal"),
    ]


def test_twim_post_date_from_file_name_and_other_posts():
    old = POST.replace('date = "2023-06-16"\n', "")
    assert d.twim_post(old, "2018-04-20-this-week-in-matrix-2018-04-20.md")[0] == "2018-04-20"
    other = POST.replace('category = ["This Week in Matrix"]', 'category = ["Releases"]').replace("This Week in Matrix 2023", "Synapse 1.2")
    assert d.twim_post(other, "x.md") is None
