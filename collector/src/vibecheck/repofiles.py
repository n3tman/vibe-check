"""Health signals read from the file list: CI, tests, security policy."""

from __future__ import annotations

import posixpath
import re

_CI = re.compile(
    r"^(\.github/workflows/[^/]+\.ya?ml|\.gitlab-ci\.yml|\.forgejo/workflows/[^/]+\.ya?ml|"
    r"\.gitea/workflows/[^/]+\.ya?ml|\.woodpecker\.ya?ml|\.woodpecker/[^/]+\.ya?ml|\.drone\.yml|"
    r"\.builds/[^/]+\.yml|\.build\.yml|\.circleci/config\.yml|\.travis\.yml|Jenkinsfile|"
    r"\.buildkite/[^/]+|azure-pipelines\.yml|bitrise\.yml|codemagic\.yaml|\.cirrus\.yml|appveyor\.yml)$",
    re.I,
)
_TEST_DIR = re.compile(r"(^|/)(tests?|__tests__|spec|specs|test_?suite|androidTest|integration_test|testing|e2e|playwright|cypress|sytest|complement)/", re.I)
_TEST_FILE = re.compile(
    r"(_test\.(go|py|rs|dart|exs|cpp|c|kt)|\.test\.(js|jsx|ts|tsx|mjs)|\.spec\.(js|jsx|ts|tsx)|"
    r"(^|/)test_[^/]+\.py|Tests?\.(kt|java|swift|cs)|_spec\.rb|Test\.php)$",
    re.I,
)
_SECURITY = re.compile(r"^(\.github/|docs/|\.gitlab/|\.forgejo/)?security(\.md|\.txt|\.rst)?$", re.I)


def ci_files(paths: list[str]) -> list[str]:
    return [p for p in paths if _CI.search(p)][:20]


def tests_present(paths: list[str]) -> bool:
    return any(_TEST_DIR.search(p) or _TEST_FILE.search(p) for p in paths)


def security_policy(paths: list[str]) -> str | None:
    for p in paths:
        if _SECURITY.match(p):
            return p
    return None


def licence_file(paths: list[str]) -> str | None:
    for p in paths:
        if "/" not in p and re.match(r"^(licen[sc]e|copying|unlicense)(\.|$|-)", posixpath.basename(p), re.I):
            return p
    return None


# Rough SPDX detection from a licence file's text, used when the forge does not say.
_LICENCES = [
    ("AGPL-3.0", r"GNU AFFERO GENERAL PUBLIC LICENSE\s+Version 3"),
    ("LGPL-3.0", r"GNU LESSER GENERAL PUBLIC LICENSE\s+Version 3"),
    ("LGPL-2.1", r"GNU LESSER GENERAL PUBLIC LICENSE\s+Version 2\.1"),
    ("GPL-3.0", r"GNU GENERAL PUBLIC LICENSE\s+Version 3"),
    ("GPL-2.0", r"GNU GENERAL PUBLIC LICENSE\s+Version 2"),
    ("MPL-2.0", r"Mozilla Public License,? (Version|v\.?) ?2\.0"),
    ("Apache-2.0", r"Apache License,?\s+Version 2\.0"),
    ("EUPL-1.2", r"European Union Public Licen[cs]e\s+v?\.? ?1\.2"),
    ("BSD-3-Clause", r"Redistribution and use in source and binary forms[\s\S]{0,1500}(Neither the name|endorse or promote)"),
    ("BSD-2-Clause", r"Redistribution and use in source and binary forms"),
    ("ISC", r"Permission to use, copy, modify, and(/or)? distribute this software for any"),
    ("MIT", r"Permission is hereby granted, free of charge"),
    ("Unlicense", r"This is free and unencumbered software released into the public domain"),
    ("0BSD", r"Zero-Clause BSD"),
]


def detect_licence(text: str) -> str | None:
    head = text[:6000]
    for spdx, pat in _LICENCES:
        if re.search(pat, head, re.I):
            return spdx
    return None
