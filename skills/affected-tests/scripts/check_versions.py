#!/usr/bin/env python3
"""Check published test-order plugin versions against what a project configures.

Usage: check_versions.py [--repo DIR]
Prints JSON:
  {"maven":  {"latest": "0.1.0", "configured": "0.1.0", "update_available": false},
   "gradle": {"published": false, "latest": null, "configured": null, "update_available": false}}
"latest" is null when the artifact isn't published (or the network is down: see "errors").
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

MAVEN_PLUGIN = "https://repo1.maven.org/maven2/me/bechberger/test-order-maven-plugin/maven-metadata.xml"
GRADLE_SOURCES = (
    # Plugin Portal marker artifact: what `plugins { id("me.bechberger.test-order") version "x" }` resolves.
    "https://plugins.gradle.org/m2/me/bechberger/test-order/me.bechberger.test-order.gradle.plugin/maven-metadata.xml",
    # Plain artifact on Central: what an init script's `classpath '...:test-order-gradle-plugin:x'` resolves.
    "https://repo1.maven.org/maven2/me/bechberger/test-order-gradle-plugin/maven-metadata.xml",
)


def latest_release(metadata_xml):
    m = re.search(r"<release>\s*([^<\s]+)\s*</release>", metadata_xml) or \
        re.search(r"<latest>\s*([^<\s]+)\s*</latest>", metadata_xml)
    return m.group(1) if m else None


def fetch(url, errors):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code != 404:  # 404 = not published, which is an answer, not an error
            errors.append(f"{url}: HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError) as e:
        errors.append(f"{url}: {e}")
    return None


def version_key(v):
    """Order 0.1.0 > 0.1.0-SNAPSHOT > 0.0.9; numeric parts compare as numbers."""
    base, _, qual = v.partition("-")
    nums = tuple(int(p) if p.isdigit() else 0 for p in base.split("."))
    return nums, qual == ""  # a release sorts after any qualified build of the same base


def newer(latest, configured):
    return bool(latest and configured and version_key(latest) > version_key(configured))


def maven_configured(repo):
    pom = repo / "pom.xml"
    if not pom.exists():
        return None
    text = pom.read_text(errors="ignore")
    m = re.search(r"<artifactId>\s*test-order-maven-plugin\s*</artifactId>\s*<version>\s*([^<\s]+)", text)
    if not m:
        return None
    v = m.group(1)
    prop = re.fullmatch(r"\$\{([^}]+)\}", v)
    if prop:  # shortcut: resolves properties from this pom only, not parents
        pm = re.search(rf"<{re.escape(prop.group(1))}>\s*([^<\s]+)\s*</", text)
        v = pm.group(1) if pm else v
    return v


def gradle_configured(repo):
    files = [*repo.glob("build.gradle*"), *repo.glob("settings.gradle*"), *repo.glob("*.gradle"),
             *repo.glob("gradle/*.toml")]
    for f in files:
        text = f.read_text(errors="ignore")
        for pat in (r"""me\.bechberger\.test-order['"]\)?\s*version\s*\(?['"]([^'"]+)""",
                    r"""test-order-gradle-plugin:([^'"\s]+)""",
                    r"""id\s*=\s*"me\.bechberger\.test-order"\s*,\s*version\s*=\s*"([^"]+)"""):
            m = re.search(pat, text)
            if m:
                return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    repo = Path(ap.parse_args().repo)
    errors = []
    mvn_latest = latest_release(fetch(MAVEN_PLUGIN, errors) or "")
    gradle_latest = None
    for url in GRADLE_SOURCES:
        gradle_latest = latest_release(fetch(url, errors) or "")
        if gradle_latest:
            break
    mvn_cfg, gr_cfg = maven_configured(repo), gradle_configured(repo)
    out = {
        "maven": {"latest": mvn_latest, "configured": mvn_cfg, "update_available": newer(mvn_latest, mvn_cfg)},
        "gradle": {"published": gradle_latest is not None, "latest": gradle_latest, "configured": gr_cfg,
                   "update_available": newer(gradle_latest, gr_cfg)},
    }
    if errors:
        out["errors"] = errors
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
