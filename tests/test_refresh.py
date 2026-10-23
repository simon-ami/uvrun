import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from click.testing import CliRunner
from test_menu_cli import TerminalRunner
from uvrun.cli import cli
from uvrun.config import Config
from uvrun.discover import RepositoryScripts
from uvrun.refresh import refresh_repositories

REPO = "https://github.com/example/scripts"
SECOND_REPO = "https://github.com/other/scripts"


class RefreshTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch("uvrun.config.Path.home", return_value=Path(directory)))
        self.config = Config()
        self.saved = {"gone.py": "gone.py", "hidden.py": "hidden.py"}
        self.config.add_repo(REPO, self.saved, tree_sha="old-tree")
        self.config.set_script_hidden(REPO, "hidden.py", True)
        self.changed = RepositoryScripts(
            {"new.py": "tools/new.py", "hidden.py": "hidden.py"}, "new-tree"
        )

    def test_updates_list_and_preserves_hidden_scripts(self):
        with patch("uvrun.refresh.fetch_repository", return_value=self.changed):
            self.assertEqual(refresh_repositories(self.config), {})
        loaded = Config()
        self.assertEqual([s.name for s in loaded.get_scripts()], ["new.py"])
        self.assertIsNone(loaded.get_script_url("gone"))
        self.assertIsNotNone(loaded.get_script_url("hidden"))
        self.assertEqual(loaded.config["repos"][REPO]["tree_sha"], "new-tree")

    @patch("uvrun.discover.requests.get")
    def test_unchanged_tree_uses_one_request_and_does_not_rewrite_config(self, get):
        get.return_value.json.return_value = {"sha": "old-tree", "tree": [], "truncated": False}
        with patch.object(self.config, "_save_config") as save:
            self.assertEqual(refresh_repositories(self.config), {})
        self.assertEqual(get.call_count, 1)
        save.assert_not_called()
        self.assertEqual(self.config.config["repos"][REPO]["scripts"], self.saved)

    @patch("uvrun.discover.requests.get")
    def test_changed_tree_rescans_metadata_in_existing_python_files(self, get):
        tree = Mock()
        tree.json.return_value = {
            "sha": "new-tree",
            "tree": [
                {"type": "blob", "path": "new.py", "sha": "new.py-blob"},
                {"type": "blob", "path": "no-longer-script.py", "sha": "no-longer-script.py-blob"},
            ],
        }
        get.side_effect = [
            tree,
            Mock(text="# /// script\n# dependencies = []\n# ///"),
            Mock(text='print("no inline metadata")'),
        ]
        self.assertEqual(refresh_repositories(self.config), {})
        self.assertEqual([s.name for s in Config().get_scripts()], ["new.py"])

    def test_failed_refresh_preserves_saved_list_and_tree_id(self):
        for error in (
            requests.ConnectionError("offline"),
            requests.HTTPError("rate limited"),
            ValueError("incomplete tree"),
        ):
            with self.subTest(error=error), patch(
                "uvrun.refresh.fetch_repository", side_effect=error
            ):
                failures = refresh_repositories(self.config)
                self.assertIn(REPO, failures)
                self.assertEqual(self.config.config["repos"][REPO]["scripts"], self.saved)
                self.assertEqual(Config().config["repos"][REPO]["tree_sha"], "old-tree")

    def test_failed_save_preserves_old_snapshot(self):
        with (
            patch("uvrun.refresh.fetch_repository", return_value=self.changed),
            patch.object(self.config, "_save_config", side_effect=OSError("disk full")),
        ):
            self.assertIn(REPO, refresh_repositories(self.config))
        self.assertEqual(self.config.config["repos"][REPO]["scripts"], self.saved)
        self.assertEqual(Config().config["repos"][REPO]["tree_sha"], "old-tree")

    def test_refresh_continues_after_one_repo_fails(self):
        self.config.add_repo(SECOND_REPO, {}, tree_sha="second-tree")
        with patch(
            "uvrun.refresh.fetch_repository",
            side_effect=[requests.ConnectionError("offline"), self.changed],
        ):
            self.assertEqual(set(refresh_repositories(self.config)), {REPO})
        self.assertEqual(Config().config["repos"][SECOND_REPO]["scripts"], self.changed.scripts)

    def test_removed_all_scripts_clears_the_saved_list(self):
        with patch(
            "uvrun.refresh.fetch_repository", return_value=RepositoryScripts({}, "empty-tree")
        ):
            self.assertEqual(refresh_repositories(self.config), {})
        self.assertEqual(Config().get_scripts(include_hidden=True), [])

    def test_list_refreshes_before_display(self):
        with patch("uvrun.refresh.fetch_repository", return_value=self.changed) as fetch:
            result = CliRunner().invoke(cli, ["--list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("new.py", result.output)
        self.assertNotIn("gone.py", result.output)
        self.assertNotIn("hidden.py", result.output)
        fetch.assert_called_once()

    def test_run_discovers_new_names_before_lookup(self):
        with (
            patch("uvrun.refresh.fetch_repository", return_value=self.changed),
            patch("uvrun.cli.run_script") as run,
        ):
            result = CliRunner().invoke(cli, ["new", "argument"])
        self.assertEqual(result.exit_code, 0, result.output)
        run.assert_called_once_with(
            "https://raw.githubusercontent.com/example/scripts/main/tools/new.py",
            ["argument"],
            None,
            False,
        )

    def test_menu_sees_refreshed_script_list(self):
        def open_menu(config):
            self.assertEqual([s.name for s in config.get_scripts()], ["new.py"])

        with (
            patch("uvrun.refresh.fetch_repository", return_value=self.changed) as fetch,
            patch("uvrun.menu.open_menu", side_effect=open_menu),
        ):
            result = TerminalRunner().invoke(cli)
        self.assertEqual(result.exit_code, 0, result.output)
        fetch.assert_called_once()

    def test_no_refresh_for_help_version_or_noninteractive_bare_invocation(self):
        with patch("uvrun.refresh.fetch_repository") as fetch:
            for args in (["--help"], ["--version"], []):
                result = CliRunner().invoke(cli, args)
                self.assertEqual(result.exit_code, 0, result.output)
            fetch.assert_not_called()

    def test_failed_refresh_warns_and_retains_list(self):
        with patch(
            "uvrun.refresh.fetch_repository", side_effect=requests.ConnectionError("offline")
        ):
            result = CliRunner().invoke(cli, ["--list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Using its saved script list", result.output)
        self.assertIn("gone.py", result.output)

    def test_adding_and_listing_does_not_fetch_same_repo_twice(self):
        with (
            patch("uvrun.cli.fetch_script_list", return_value={"new.py": "new.py"}) as added,
            patch("uvrun.refresh.fetch_repository") as refreshed,
        ):
            result = CliRunner().invoke(cli, ["--add", REPO, "--list"])
        self.assertEqual(result.exit_code, 0, result.output)
        added.assert_called_once()
        refreshed.assert_not_called()
        self.assertIn("new.py", result.output)
