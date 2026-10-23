import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w


@dataclass(frozen=True)
class Script:
    repo: str
    name: str
    path: str
    url: str
    hidden: bool = False


class Config:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "uvrun"
        self.config_file = self.config_dir / "config.toml"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_file.exists():
            default_config = {"repos": {}}
            self._save_config(default_config)
            return default_config
        return tomllib.loads(self.config_file.read_text())

    def _save_config(self, config: dict) -> None:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.config_dir, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(tomli_w.dumps(config))
            temporary.replace(self.config_file)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _replace_repos(self, repos: dict) -> None:
        updated = {**self.config, "repos": repos}
        self._save_config(updated)
        self.config = updated

    def add_repo(self, url: str, scripts: dict[str, str], *, tree_sha: str | None = None) -> None:
        previous = self.config["repos"].get(url, {})
        hidden = set(previous.get("hidden_scripts", [])) & set(scripts.values())
        info = {
            "raw_base": self._get_raw_url_base(url),
            "scripts": scripts,
            "hidden_scripts": sorted(hidden),
        }
        if tree_sha is not None:
            info["tree_sha"] = tree_sha
        self._replace_repos({**self.config["repos"], url: info})

    def get_scripts(self, include_hidden: bool = False) -> list[Script]:
        scripts = []
        for repo, info in self.config["repos"].items():
            hidden = info.get("hidden_scripts", [])
            for name, path in sorted(info["scripts"].items()):
                if include_hidden or path not in hidden:
                    scripts.append(
                        Script(repo, name, path, f"{info['raw_base']}/{path}", path in hidden)
                    )
        return scripts

    def set_script_hidden(self, repo: str, name: str, hidden: bool) -> None:
        info = self.config["repos"][repo]
        path = info["scripts"][name]
        paths = set(info.get("hidden_scripts", []))
        if hidden:
            paths.add(path)
        else:
            paths.discard(path)
        self._replace_repos(
            {**self.config["repos"], repo: {**info, "hidden_scripts": sorted(paths)}}
        )

    def remove_repo(self, url: str) -> None:
        repos = dict(self.config["repos"])
        del repos[url]
        self._replace_repos(repos)

    def get_script_url(self, script_name: str) -> str | None:
        if not script_name.endswith(".py"):
            script_name += ".py"
        for script in self.get_scripts(include_hidden=True):
            if script.name == script_name:
                return script.url
        return None

    def _get_raw_url_base(self, url: str) -> str:
        if "github.com/" in url:
            parts = url.split("github.com/", 1)[1].split("/")
            return f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/main"
        return url
