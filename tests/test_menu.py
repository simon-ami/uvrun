import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from uvrun.config import Config
from uvrun.menu import Menu

REPO = "https://github.com/example/scripts"
OTHER_REPO = "https://github.com/other/scripts"


class MenuTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch("uvrun.config.Path.home", return_value=Path(directory)))
        self.config = Config()
        self.config.add_repo(REPO, {"alpha.py": "tools/alpha.py", "beta.py": "beta.py"})

    async def play(self, keys):
        with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
            menu = Menu(self.config)
            pipe.send_text(keys)
            result = await asyncio.wait_for(menu.app.run_async(), timeout=3)
            return menu, result

    async def wait_until(self, predicate):
        async def wait():
            while not predicate():
                await asyncio.sleep(0.01)

        await asyncio.wait_for(wait(), timeout=3)

    async def test_select_edit_quoted_arguments_and_run(self):
        _, request = await self.play('\x1b[B\r"a file.wav" --output "new folder"\r')
        self.assertEqual(request.script.name, "beta.py")
        self.assertEqual(request.args, ["a file.wav", "--output", "new folder"])

    async def test_filter_insert_and_run_without_arguments(self):
        _, request = await self.play("alpha\x1b[2~\r")
        self.assertEqual(request.script.name, "alpha.py")
        self.assertEqual(request.args, [])

    async def test_selection_wraps_and_duplicate_names_keep_repo_identity(self):
        self.config.add_repo(OTHER_REPO, {"alpha.py": "different/alpha.py"})
        _, request = await self.play("\x1b[A\r\r")
        self.assertEqual(
            request.script.url,
            "https://raw.githubusercontent.com/other/scripts/main/different/alpha.py",
        )

    async def test_unclosed_quote_keeps_editor_open(self):
        menu, result = await self.play('\r"unfinished\r\x03')
        self.assertIsNone(result)
        self.assertIn("quoting", menu.status)

    async def test_hidden_scripts_stay_hidden_after_reload(self):
        menu, _ = await self.play("\t\t\x1b[B \x03")
        self.assertIn("hidden", menu.status)
        self.assertEqual([s.name for s in Config().get_scripts()], ["beta.py"])
        self.assertIsNotNone(self.config.get_script_url("alpha"))

    async def test_hidden_script_can_be_shown_again(self):
        self.config.set_script_hidden(REPO, "alpha.py", True)
        await self.play("\t\t\x1b[B \x03")
        self.assertEqual(len(Config().get_scripts()), 2)

    async def test_repo_removal_requires_confirmation(self):
        await self.play("\t\t\rn\x03")
        self.assertIn(REPO, Config().config["repos"])
        await self.play("\t\t\ry\x03")
        self.assertEqual(Config().config["repos"], {})

    async def test_empty_library_can_switch_tabs_and_quit(self):
        self.config.remove_repo(REPO)
        menu, result = await self.play("\x1b[B\r\t\t\x1b[B\r\x03")
        self.assertIsNone(result)
        self.assertEqual(menu.tab, 2)

    async def test_add_repo_then_select_its_script(self):
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=DummyOutput()),
            patch("uvrun.menu.fetch_script_list", return_value={"gamma.py": "gamma.py"}),
        ):
            menu = Menu(self.config)
            task = asyncio.create_task(menu.app.run_async())
            try:
                pipe.send_text("\thttps://github.com/new/scripts.git/\r")
                await self.wait_until(lambda: menu.status.startswith("Saved"))
                pipe.send_text("\x1b[Zgamma\r--help\r")
                request = await asyncio.wait_for(task, timeout=3)
                self.assertEqual(request.script.repo, "https://github.com/new/scripts")
                self.assertEqual(request.args, ["--help"])
            finally:
                if not task.done():
                    menu.app.exit()
                    await task

    async def test_network_error_keeps_menu_usable_and_config_unchanged(self):
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=DummyOutput()),
            patch("uvrun.menu.fetch_script_list", side_effect=requests.ConnectionError("offline")),
        ):
            menu = Menu(self.config)
            task = asyncio.create_task(menu.app.run_async())
            try:
                pipe.send_text("\thttps://github.com/new/scripts\r")
                await self.wait_until(lambda: menu.status.startswith("Cannot add"))
                self.assertEqual(list(Config().config["repos"]), [REPO])
                pipe.send_text("\x03")
                self.assertIsNone(await asyncio.wait_for(task, timeout=3))
            finally:
                if not task.done():
                    menu.app.exit()
                    await task

    async def test_bad_url_is_not_fetched(self):
        with patch("uvrun.menu.fetch_script_list") as fetch:
            menu, _ = await self.play("\tno-repository\r\x03")
        fetch.assert_not_called()
        self.assertIn("GitHub repository URL", menu.status)

    async def test_async_add_restores_visible_focus_if_user_switches_to_run(self):
        import threading

        release = threading.Event()

        def fetch(_url):
            if not release.wait(2):
                raise TimeoutError("test did not release request")
            return {"gamma.py": "gamma.py"}

        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=DummyOutput()),
            patch("uvrun.menu.fetch_script_list", side_effect=fetch),
        ):
            menu = Menu(self.config)
            task = asyncio.create_task(menu.app.run_async())
            try:
                pipe.send_text("\thttps://github.com/new/repo\r")
                await self.wait_until(lambda: menu.busy)
                pipe.send_text("\x1b[Z\r")
                await self.wait_until(lambda: menu.chosen is not None)
                release.set()
                await self.wait_until(lambda: not menu.busy)
                self.assertTrue(menu.app.layout.has_focus(menu.search))
                pipe.send_text("gamma\r\r")
                request = await asyncio.wait_for(task, timeout=3)
                self.assertEqual(request.script.name, "gamma.py")
            finally:
                release.set()
                if not task.done():
                    menu.app.exit()
                    await task
