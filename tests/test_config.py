import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uvrun.config import Config
from uvrun.discover import normalize_repo_url


class ConfigTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch("uvrun.config.Path.home", return_value=Path(directory)))
        self.config = Config()
        self.repo = "https://github.com/example/scripts"
        self.scripts = {"demo.py": "tools/demo.py", "other.py": "other.py"}

    def test_loads_old_config_without_hidden_scripts(self):
        self.config.config_file.write_text(
            '[repos."https://github.com/example/scripts"]\n'
            'raw_base = "https://raw.githubusercontent.com/example/scripts/main"\n'
            '[repos."https://github.com/example/scripts".scripts]\n'
            '"demo.py" = "demo.py"\n'
        )
        loaded = Config()
        self.assertEqual(len(loaded.get_scripts()), 1)
        self.assertEqual(loaded.get_script_url("demo"), loaded.get_script_url("demo.py"))

    def test_refresh_preserves_hidden_scripts_and_discards_stale_paths(self):
        self.config.add_repo(self.repo, self.scripts)
        self.config.set_script_hidden(self.repo, "demo.py", True)
        self.config.add_repo(self.repo, self.scripts)
        self.assertEqual([s.name for s in Config().get_scripts()], ["other.py"])
        self.config.add_repo(self.repo, {"demo.py": "new/demo.py"})
        self.assertEqual(len(Config().get_scripts()), 1)

    def test_normalizes_repo_urls(self):
        for value in (
            self.repo,
            self.repo + "/",
            self.repo + ".git/",
            " github.com/example/scripts ",
        ):
            self.assertEqual(normalize_repo_url(value), self.repo)

    def test_rejects_non_repo_urls(self):
        for value in (
            "",
            "https://example.com/repo",
            "https://github.com/owner",
            "https://github.com/o/r/tree/main",
            "https://github.com.evil.test/o/r",
            "https://github.com/o/r?x=y",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_repo_url(value)

    def test_failed_save_does_not_change_memory_or_disk(self):
        self.config.add_repo(self.repo, self.scripts)
        with patch.object(self.config, "_save_config", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.config.set_script_hidden(self.repo, "demo.py", True)
            with self.assertRaises(OSError):
                self.config.remove_repo(self.repo)
            with self.assertRaises(OSError):
                self.config.add_repo(self.repo, {})
        self.assertEqual(len(self.config.get_scripts()), 2)
        self.assertEqual(len(Config().get_scripts()), 2)
