import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import call, patch

from click.testing import CliRunner
from uvrun.cli import cli
from uvrun.config import Config, Script
from uvrun.menu import RunRequest


class TerminalRunner(CliRunner):
    def __init__(self, stdin=True, stdout=True):
        super().__init__()
        self.stdin_tty = stdin
        self.stdout_tty = stdout

    @contextmanager
    def isolation(self, *args, **kwargs):
        with super().isolation(*args, **kwargs) as streams:
            with (
                patch("uvrun.cli.sys.stdin.isatty", return_value=self.stdin_tty),
                patch("uvrun.cli.sys.stdout.isatty", return_value=self.stdout_tty),
            ):
                yield streams


class MenuCLITests(unittest.TestCase):
    def test_bare_invocation_opens_menu_only_with_terminal_input_and_output(self):
        for stdin, stdout in ((False, False), (True, False), (False, True), (True, True)):
            with (
                self.subTest(stdin=stdin, stdout=stdout),
                patch("uvrun.cli.Config"),
                patch("uvrun.menu.open_menu", return_value=None) as menu,
                patch("uvrun.cli.checked_uv") as checked,
            ):
                result = TerminalRunner(stdin, stdout).invoke(cli)
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(menu.call_count, int(stdin and stdout))
                if not (stdin and stdout):
                    self.assertIn("Usage:", result.output)
                checked.assert_not_called()

    def test_menu_execution_checks_uv_and_propagates_script_exit(self):
        script = Script(
            "https://github.com/other/repo", "demo.py", "demo.py", "https://example.com/demo.py"
        )
        with (
            patch("uvrun.cli.Config"),
            patch("uvrun.menu.open_menu", return_value=RunRequest(script, ["a file", "--help"])),
            patch("uvrun.cli.shutil.which", return_value="/checked/uv"),
            patch("uvrun.cli.subprocess.run") as run,
        ):
            run.side_effect = [
                subprocess.CompletedProcess([], 0, stdout="uv 0.13.4"),
                subprocess.CompletedProcess([], 9),
            ]
            result = TerminalRunner().invoke(cli)
            self.assertEqual(result.exit_code, 9)
            self.assertEqual(
                run.call_args_list[-1], call(["/checked/uv", "run", script.url, "a file", "--help"])
            )

    def test_old_uv_cannot_run_menu_selection(self):
        script = Script("repo", "demo.py", "demo.py", "https://example.com/demo.py")
        with (
            patch("uvrun.cli.Config"),
            patch("uvrun.menu.open_menu", return_value=RunRequest(script, [])),
            patch("uvrun.cli.shutil.which", return_value="/checked/uv"),
            patch(
                "uvrun.cli.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, stdout="uv 0.13.3"),
            ) as run,
        ):
            result = TerminalRunner().invoke(cli)
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Upgrade uv", result.output)
            self.assertEqual(run.call_count, 1)

    def test_list_omits_hidden_scripts(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "uvrun.config.Path.home", return_value=Path(directory)
        ):
            config = Config()
            repo = "https://github.com/example/repo"
            config.add_repo(repo, {"hidden.py": "hidden.py", "visible.py": "visible.py"})
            config.set_script_hidden(repo, "hidden.py", True)
            with patch("uvrun.cli.refresh_repositories", return_value={}):
                result = CliRunner().invoke(cli, ["--list"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertNotIn("hidden.py", result.output)
            self.assertIn("visible.py", result.output)

    def test_explicit_options_do_not_open_menu(self):
        for args in (["--refresh"], ["--uv-args", ""], ["--list"], ["--help"]):
            with (
                self.subTest(args=args),
                patch("uvrun.cli.Config") as config,
                patch("uvrun.menu.open_menu") as menu,
            ):
                config.return_value.config = {"repos": {}}
                result = TerminalRunner().invoke(cli, args)
                self.assertEqual(result.exit_code, 0, result.output)
                menu.assert_not_called()
