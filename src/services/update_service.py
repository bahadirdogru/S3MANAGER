"""GitHub Releases update check."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from packaging.version import Version, InvalidVersion

from src.version import __version__, GITHUB_REPO

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"S3MANAGER/{__version__}"


@dataclass
class ReleaseInfo:
    version: str
    html_url: str
    body: str


def _parse_tag(tag_name: str) -> Optional[str]:
    match = re.match(r"^v?(\d+\.\d+\.\d+.*)$", tag_name.strip())
    if match:
        return match.group(1)
    return None


def fetch_latest_release() -> ReleaseInfo:
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    tag = data.get("tag_name", "")
    version = _parse_tag(tag)
    if not version:
        raise ValueError(f"Gecersiz surum etiketi: {tag}")

    return ReleaseInfo(
        version=version,
        html_url=data.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"),
        body=(data.get("body") or "").strip(),
    )


def is_newer_version(latest: str, current: str = __version__) -> bool:
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return latest != current
