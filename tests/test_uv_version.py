import subprocess
import unittest
from unittest.mock import call, patch

from click.testing import CliRunner
from uvrun.cli import cli


class UVVersionTests(unittest.TestCase):
    def invoke(self, output="uv 0.13.4", error=None, executable="/test/bin/uv", returncode=0):
        with (
            patch("uvrun.cli.Config") as config,
            patch("uvrun.cli.shutil.which", return_value=executable),
            patch("uvrun.cli.subprocess.run") as run,
        ):
            config.return_value.get_script_url.return_value = "https://example.com/script.py"
            run.side_effect = error or [
                subprocess.CompletedProcess([], 0, stdout=output),
                subprocess.CompletedProcess([], returncode),
            ]
            result = CliRunner().invoke(cli, ["--refresh", "--uv-args", "--offline", "demo", "arg"])
            return result, run.call_args_list

    def test_supported_versions_run_checked_executable(self):
        for version in ("0.13.4", "0.13.5", "0.13.10", "0.14.0", "1.0.0"):
            with self.subTest(version=version):
                result, calls = self.invoke(f"uv {version} (abcdef 2026-10-20)\n")
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(
                    calls,
                    [
                        call(
                            ["/test/bin/uv", "--version"],
                            capture_output=True,
                            text=True,
                            check=True,
                        ),
                        call(
                            [
                                "/test/bin/uv",
                                "--offline",
                                "run",
                                "--refresh",
                                "https://example.com/script.py",
                                "arg",
                            ]
                        ),
                    ],
                )

    def test_script_failure_is_returned_to_the_caller(self):
        result, calls = self.invoke(returncode=7)
        self.assertEqual(result.exit_code, 7)
        self.assertEqual(len(calls), 2)

    def test_old_and_prerelease_versions_do_not_run_scripts(self):
        for version in ("0.6.0", "0.13.3", "0.13.4rc1", "0.13.4.dev0"):
            with self.subTest(version=version):
                result, calls = self.invoke(f"uv {version}")
                self.assertEqual(result.exit_code, 1)
                self.assertIn("Upgrade uv", result.output)
                self.assertEqual(len(calls), 1)

    def test_malformed_output_does_not_run_scripts(self):
        for output in ("", "uv", "other 99.0", "uv garbage"):
            with self.subTest(output=output):
                result, calls = self.invoke(output)
                self.assertEqual(result.exit_code, 1)
                self.assertEqual(len(calls), 1)

    def test_failed_version_command_does_not_run_scripts(self):
        for error in (
            OSError("cannot execute"),
            subprocess.CalledProcessError(1, ["uv", "--version"]),
        ):
            with self.subTest(error=error):
                result, calls = self.invoke(error=error)
                self.assertEqual(result.exit_code, 1)
                self.assertIn("Cannot check uv version", result.output)
                self.assertEqual(len(calls), 1)

    def test_missing_uv(self):
        result, calls = self.invoke(executable=None)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("add it to PATH", result.output)
        self.assertEqual(calls, [])

    def test_help_list_and_add_do_not_require_uv(self):
        for args in (["--help"], ["--list"], ["--add", "https://github.com/example/repo"]):
            with (
                self.subTest(args=args),
                patch("uvrun.cli.Config") as config,
                patch("uvrun.cli.fetch_script_list", return_value={}),
                patch("uvrun.cli.shutil.which") as which,
                patch("uvrun.cli.subprocess.run") as run,
            ):
                config.return_value.config = {"repos": {}}
                result = CliRunner().invoke(cli, args)
                self.assertEqual(result.exit_code, 0, result.output)
                which.assert_not_called()
                run.assert_not_called()
