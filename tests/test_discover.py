import unittest
from unittest.mock import Mock, patch

import requests
from uvrun.discover import fetch_script_list


class DiscoveryTests(unittest.TestCase):
    @patch("uvrun.discover.requests.get")
    def test_uses_normalized_repo_and_checks_downloads(self, get):
        tree = Mock()
        tree.json.return_value = {
            "sha": "current-tree",
            "tree": [
                {"type": "tree", "path": "folder.py"},
                {"type": "blob", "path": "demo.py", "sha": "demo.py-blob"},
                {"type": "blob", "path": "ordinary.py", "sha": "ordinary.py-blob"},
            ],
        }
        script = Mock(text="# /// script\n# dependencies = []\n# ///\n")
        ordinary = Mock(text='print("hello")')
        get.side_effect = [tree, script, ordinary]
        self.assertEqual(
            fetch_script_list("https://github.com/example/repo.git/"), {"demo.py": "demo.py"}
        )
        self.assertEqual(
            get.call_args_list[0].args[0],
            "https://api.github.com/repos/example/repo/git/trees/main?recursive=1",
        )
        self.assertEqual(
            get.call_args_list[1].args[0],
            "https://api.github.com/repos/example/repo/git/blobs/demo.py-blob",
        )
        self.assertEqual(
            get.call_args_list[1].kwargs["headers"],
            {"Accept": "application/vnd.github.raw+json"},
        )
        for response in (tree, script, ordinary):
            response.raise_for_status.assert_called_once()
        for request in get.call_args_list:
            self.assertEqual(request.kwargs["timeout"], (5, 15))

    @patch("uvrun.discover.requests.get")
    def test_failed_script_download_is_not_saved_as_empty_repository(self, get):
        tree = Mock()
        tree.json.return_value = {
            "sha": "current-tree",
            "tree": [{"type": "blob", "path": "demo.py", "sha": "demo.py-blob"}],
        }
        download = Mock()
        download.raise_for_status.side_effect = requests.HTTPError("download failed")
        get.side_effect = [tree, download]
        with self.assertRaises(requests.HTTPError):
            fetch_script_list("https://github.com/example/repo")

    @patch("uvrun.discover.requests.get")
    def test_incomplete_tree_does_not_replace_saved_scripts(self, get):
        get.return_value.json.return_value = {"tree": [], "truncated": True}
        with self.assertRaisesRegex(ValueError, "incomplete"):
            fetch_script_list("https://github.com/example/repo")
