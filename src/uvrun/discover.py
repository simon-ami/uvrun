from dataclasses import dataclass
from urllib.parse import urlsplit

import requests


def normalize_repo_url(value: str) -> str:
    value = value.strip()
    if value.startswith("github.com/"):
        value = "https://" + value
    parsed = urlsplit(value)
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.netloc.lower() != "github.com"
        or len(parts) != 2
        or not all(parts)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter a GitHub repository URL: https://github.com/owner/repo")
    owner, repo = parts
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not repo:
        raise ValueError("The GitHub repository name is missing")
    return f"https://github.com/{owner}/{repo}"


@dataclass(frozen=True)
class RepositoryScripts:
    scripts: dict[str, str]
    tree_sha: str


def fetch_repository(repo_url: str, previous: dict | None = None) -> RepositoryScripts:
    """Check the current tree; rescan scripts only when repository contents changed."""
    repo_url = normalize_repo_url(repo_url)
    repository = repo_url.removeprefix("https://github.com/")
    api_url = f"https://api.github.com/repos/{repository}/git/trees/main?recursive=1"
    response = requests.get(api_url, timeout=(5, 15))
    response.raise_for_status()
    tree = response.json()
    if tree.get("truncated"):
        raise ValueError("GitHub returned an incomplete file list for this repository")
    tree_sha = tree["sha"]
    if previous is not None and tree_sha == previous.get("tree_sha"):
        return RepositoryScripts(previous["scripts"], tree_sha)
    scripts = {}
    for item in tree["tree"]:
        if item["type"] == "blob" and item["path"].endswith(".py"):
            # Read the exact blob from this tree, even if main changes during discovery.
            blob_url = f"https://api.github.com/repos/{repository}/git/blobs/{item['sha']}"
            response = requests.get(
                blob_url, headers={"Accept": "application/vnd.github.raw+json"}, timeout=(5, 15)
            )
            response.raise_for_status()
            content = response.text
            if "# /// script" in content and "# ///" in content:
                name = item["path"].split("/")[-1]
                scripts[name] = item["path"]
    return RepositoryScripts(scripts, tree_sha)


def fetch_script_list(repo_url: str) -> dict[str, str]:
    """Fetch Python scripts with inline metadata from a GitHub repository."""
    return fetch_repository(repo_url).scripts
