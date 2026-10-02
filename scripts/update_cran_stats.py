#!/usr/bin/env python3
"""Refresh the CRAN versions and download counts shown on software.html.

The package list is read from the page itself, so adding a row to one of the
tables is enough for it to be picked up here. Nothing is written unless every
figure was fetched successfully, so a failed run leaves the page as it was
rather than replacing numbers with blanks.

Run locally with:  py scripts/update_cran_stats.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, timezone, datetime
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "software.html"
CRANLOGS = "https://cranlogs.r-pkg.org/downloads/total/{start}:{end}/{pkgs}"
CRAN_PAGE = "https://cran.r-project.org/web/packages/{pkg}/index.html"

# cranlogs has data from 2012; this start date simply predates every release.
START = "2012-10-01"
UA = {"User-Agent": "anthonychristidis.github.io stats updater"}
TIMEOUT = 60

# A table row: package name comes from the CRAN link, then the version cell,
# then the downloads cell. DOTALL so the row can span lines.
#
# Every group is named. Mixing named and positional groups here is what broke
# the first version of this script: the named groups shift the numbering, so
# the positional references pulled the old cell values back in instead of the
# separators between them.
ROW = re.compile(
    r'(?P<head><td class="pkg-name"><a href="https://cran\.r-project\.org/package='
    r'(?P<pkg>[A-Za-z0-9._]+)".*?'
    r'<td class="pkg-num">)'
    r"(?P<version>[^<]*)"
    r'(?P<mid></td>\s*<td class="pkg-num">)'
    r"(?P<downloads>[^<]*)"
    r"(?P<tail></td>)",
    re.DOTALL,
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def downloads_for(packages: list[str]) -> dict[str, int]:
    """Total downloads per package, in one request."""
    url = CRANLOGS.format(
        start=START,
        end=date.today().isoformat(),
        pkgs=",".join(packages),
    )
    rows = json.loads(fetch(url))
    counts = {r["package"]: int(r["downloads"]) for r in rows}
    missing = [p for p in packages if p not in counts]
    if missing:
        raise RuntimeError(f"cranlogs returned no rows for: {', '.join(missing)}")
    # A package that has fallen off CRAN reports 0; treat that as suspect
    # rather than silently publishing a zero.
    zeros = [p for p, n in counts.items() if n == 0]
    if zeros:
        raise RuntimeError(f"cranlogs reported zero downloads for: {', '.join(zeros)}")
    return counts


def version_for(pkg: str) -> str:
    html = fetch(CRAN_PAGE.format(pkg=pkg))
    m = re.search(r"<td>Version:</td>\s*<td>([^<]+)</td>", html)
    if not m:
        raise RuntimeError(f"could not read a version for {pkg} from CRAN")
    return m.group(1).strip()


def main() -> int:
    original = PAGE.read_text(encoding="utf-8")

    packages = [m.group("pkg") for m in ROW.finditer(original)]
    if not packages:
        print("No package rows found in software.html; markup may have changed.")
        return 1
    print(f"Found {len(packages)} packages: {', '.join(packages)}")

    try:
        counts = downloads_for(packages)
        versions = {p: version_for(p) for p in packages}
    except (urllib.error.URLError, OSError, ValueError, RuntimeError) as exc:
        print(f"Fetch failed, leaving the page untouched: {exc}")
        return 1

    def replace_row(m: re.Match) -> str:
        pkg = m.group("pkg")
        return (
            m.group("head")
            + versions[pkg]
            + m.group("mid")
            + f"{counts[pkg]:,}"
            + m.group("tail")
        )

    updated = ROW.sub(replace_row, original)

    total = sum(counts.values())
    updated = re.sub(
        r'(<span class="stat__num">)[\d,]+(</span><span class="stat__label">CRAN downloads)',
        lambda m: m.group(1) + f"{total:,}" + m.group(2),
        updated,
    )

    today = datetime.now(timezone.utc).date()
    stamp = f"{today.day} {today:%B %Y}"
    updated = re.sub(
        r"(are current as of )[^.]+(\.)",
        lambda m: m.group(1) + stamp + m.group(2),
        updated,
    )

    if updated == original:
        print(f"No change. Total is {total:,}.")
        return 0

    PAGE.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Updated. Total is {total:,} as of {stamp}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
