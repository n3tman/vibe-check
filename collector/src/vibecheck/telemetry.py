"""Analytics and crash-report SDKs found in dependency manifests.

A match says a manifest names the SDK; it says nothing about whether it is on by default,
opt-in or compiled out. The research lanes read the code for that.
"""

from __future__ import annotations

import posixpath
import re

MANIFEST_NAMES = {
    "package.json",
    "cargo.toml",
    "pubspec.yaml",
    "build.gradle",
    "build.gradle.kts",
    "libs.versions.toml",
    "go.mod",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "podfile",
    "package.swift",
    "pom.xml",
    "gemfile",
    "composer.json",
    "mix.exs",
    "deno.json",
    "cmakelists.txt",
    "meson.build",
    "conanfile.txt",
    "vcpkg.json",
    "project.clj",
    "deps.edn",
    "build.sbt",
    "packages.config",
    "directory.packages.props",
}
_MANIFEST_RE = re.compile(r"(^requirements.*\.txt$|\.csproj$|\.fsproj$|\.podspec$|\.nimble$|\.cabal$)", re.I)
_SKIP = re.compile(
    r"(^|/)(node_modules|vendor|third[_-]party|external|deps|test|tests|__tests__|examples?|fixtures?|"
    r"samples?|docs?|benchmarks?|playwright|cypress|e2e)/",
    re.I,
)

SDKS: dict[str, re.Pattern[str]] = {
    "Sentry": re.compile(r"@sentry/|\bsentry[-_](sdk|flutter|android|cocoa|go|rust|dart|python|react|electron|tauri|kotlin)|io\.sentry|getsentry/|[\"']?sentry[\"']?\s*[=:]|\bpod ['\"]Sentry", re.I),
    "PostHog": re.compile(r"posthog", re.I),
    "Matomo": re.compile(r"matomo|piwik", re.I),
    "Firebase Analytics": re.compile(r"firebase[-_/]analytics|FirebaseAnalytics|@react-native-firebase/analytics", re.I),
    "Firebase Crashlytics": re.compile(r"crashlytics", re.I),
    "Google Analytics": re.compile(r"play-services-analytics|react-ga\b|react-ga4|vue-gtag|universal-analytics|@analytics/google", re.I),
    "Mixpanel": re.compile(r"mixpanel", re.I),
    "Amplitude": re.compile(r"@amplitude/|amplitude[-_](flutter|android|swift|ios|js|analytics|kotlin)|com\.amplitude|amplitude_flutter", re.I),
    "Segment": re.compile(r"@segment/|segment-analytics|analytics-android|com\.segment|segmentio", re.I),
    "Bugsnag": re.compile(r"bugsnag", re.I),
    "Datadog": re.compile(r"@datadog/|dd-sdk|com\.datadoghq|datadog", re.I),
    "Rollbar": re.compile(r"rollbar", re.I),
    "Countly": re.compile(r"countly", re.I),
    "App Center": re.compile(r"appcenter|app-center", re.I),
    "Instabug": re.compile(r"instabug", re.I),
    "Raygun": re.compile(r"raygun", re.I),
    "Honeybadger": re.compile(r"honeybadger", re.I),
    "New Relic": re.compile(r"newrelic", re.I),
    "LogRocket": re.compile(r"logrocket", re.I),
    "Heap": re.compile(r"heap-?analytics|@heap/", re.I),
    "Embrace": re.compile(r"io\.embrace|embrace-io", re.I),
    "Plausible": re.compile(r"plausible-tracker|@plausible", re.I),
    "Umami": re.compile(r"@umami/", re.I),
    "ACRA (crash reports)": re.compile(r"ch\.acra|\bacra[-_]", re.I),
}


def is_manifest(path: str) -> bool:
    if _SKIP.search(path):
        return False
    base = posixpath.basename(path).lower()
    return base in MANIFEST_NAMES or bool(_MANIFEST_RE.search(base))


def pick_manifests(paths: list[str], limit: int = 60) -> list[str]:
    found = [p for p in paths if is_manifest(p)]
    found.sort(key=lambda p: (p.count("/"), p))
    return found[:limit]


def scan_manifest(path: str, text: str) -> list[dict]:
    out = []
    for name, pat in SDKS.items():
        for line in text.splitlines():
            if pat.search(line):
                out.append({"sdk": name, "file": path, "match": line.strip()[:160]})
                break
    return out
