"""Refresh discovery metadata without discarding usable lists on network failure."""

import requests

from .config import Config
from .discover import fetch_repository


def refresh_repositories(config: Config, *, skip: str | None = None) -> dict[str, str]:
    failures = {}
    for url, previous in config.config["repos"].items():
        if url == skip:
            continue
        try:
            discovered = fetch_repository(url, previous)
            if discovered.tree_sha != previous.get("tree_sha"):
                config.add_repo(url, discovered.scripts, tree_sha=discovered.tree_sha)
        except (requests.RequestException, ValueError, OSError) as error:
            failures[url] = str(error)
    return failures
