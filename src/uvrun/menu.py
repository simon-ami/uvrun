"""A compact keyboard menu for interactive terminals."""

import asyncio
import shlex
from dataclasses import dataclass

import requests
from prompt_toolkit.application import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    HSplit,
    Layout,
    ScrollOffsets,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Label, TextArea

from .config import Config, Script
from .discover import fetch_script_list, normalize_repo_url


@dataclass(frozen=True)
class RunRequest:
    script: Script
    args: list[str]


class Menu:
    def __init__(self, config: Config):
        self.config = config
        self.tab = 0
        self.index = 0
        self.manage_index = 0
        self.chosen: Script | None = None
        self.pending_remove: str | None = None
        self.busy = False
        self.status = ""
        self.search = TextArea(height=1, prompt="Find  ", multiline=False)
        self.arguments = TextArea(height=1, multiline=False)
        self.repository = TextArea(
            height=1, prompt="URL  ", multiline=False, read_only=Condition(lambda: self.busy)
        )
        self.search.buffer.on_text_changed += self._search_changed
        self.run_control = FormattedTextControl(
            self._script_lines, get_cursor_position=lambda: Point(0, self.index)
        )
        self.manage_control = FormattedTextControl(
            self._manage_lines,
            focusable=True,
            get_cursor_position=lambda: Point(0, self.manage_index),
        )
        list_options = {
            "height": Dimension(min=3, max=10),
            "wrap_lines": False,
            "scroll_offsets": ScrollOffsets(top=1, bottom=1),
            "allow_scroll_beyond_bottom": False,
        }
        run_view = HSplit(
            [
                self.search,
                Window(self.run_control, **list_options),
                ConditionalContainer(
                    HSplit([Label(self._command_label), self.arguments]),
                    filter=Condition(lambda: self.chosen is not None),
                ),
            ]
        )
        add_view = HSplit(
            [
                Label("Add a GitHub repository of Python scripts."),
                Label("https://github.com/owner/repo"),
                self.repository,
            ]
        )
        manage_view = Window(self.manage_control, **list_options)
        layout = HSplit(
            [
                Label(self._tabs),
                Window(height=1, char="─", style="class:muted"),
                *[
                    ConditionalContainer(view, filter=Condition(lambda i=i: self.tab == i))
                    for i, view in enumerate([run_view, add_view, manage_view])
                ],
                Label(lambda: self.status, style="class:status"),
                Window(height=1, char="─", style="class:muted"),
                Label(self._hints, style="class:muted"),
            ]
        )
        self.app: Application[RunRequest | None] = Application(
            layout=Layout(layout, focused_element=self.search),
            key_bindings=self._bindings(),
            full_screen=False,
            erase_when_done=True,
            style=Style.from_dict(
                {
                    "title": "bold",
                    "active": "bold ansicyan underline",
                    "selected": "bold ansicyan",
                    "muted": "ansibrightblack",
                    "status": "ansiyellow",
                }
            ),
        )

    @property
    def scripts(self) -> list[Script]:
        query = self.search.text.casefold()
        return [
            script
            for script in self.config.get_scripts()
            if query in f"{script.name} {script.repo} {script.path}".casefold()
        ]

    @property
    def manage_rows(self) -> list[str | Script]:
        rows: list[str | Script] = []
        scripts = self.config.get_scripts(include_hidden=True)
        for repo in self.config.config["repos"]:
            rows.append(repo)
            rows.extend(script for script in scripts if script.repo == repo)
        return rows

    def _search_changed(self, _buffer):
        self.index = 0

    def _tabs(self):
        fragments = [("class:title", "uvrun   ")]
        for i, title in enumerate(["Run", "Add repository", "Manage"]):
            fragments.append(("class:active" if self.tab == i else "class:muted", title))
            fragments.append(("", "   "))
        return fragments

    def _script_lines(self):
        scripts = self.scripts
        if not scripts:
            text = "No matching scripts."
            if not self.config.get_scripts():
                text = "No visible scripts. Tab to add a repository or manage hidden scripts."
            return [("class:muted", text)]
        fragments = []
        for i, script in enumerate(scripts):
            selected = i == self.index
            fragments.extend(
                [
                    (
                        "class:selected" if selected else "",
                        f"{'›' if selected else ' '} {script.name}",
                    ),
                    ("class:muted", f"  {script.repo.removeprefix('https://github.com/')}"),
                    ("", "\n" if i < len(scripts) - 1 else ""),
                ]
            )
        return fragments

    def _manage_lines(self):
        rows = self.manage_rows
        if not rows:
            return [("class:muted", "No saved repositories. Tab to add one.")]
        fragments = []
        for i, row in enumerate(rows):
            style = "class:selected" if i == self.manage_index else ""
            marker = "›" if i == self.manage_index else " "
            text = row if isinstance(row, str) else f"  [{' ' if row.hidden else 'x'}] {row.path}"
            fragments.append((style, f"{marker} {text}"))
            if i < len(rows) - 1:
                fragments.append(("", "\n"))
        return fragments

    def _command_label(self):
        return f"{self.chosen.name if self.chosen else ''}  ·  arguments (shell quoting supported)"

    def _hints(self):
        if self.pending_remove:
            return "y remove repository · n/Esc cancel"
        if self.tab == 0:
            if self.app.layout.has_focus(self.arguments):
                return "Enter run · Esc back · Tab switch · Ctrl+C quit"
            return "↑/↓ select · type to filter · Enter/Insert choose · Tab switch · Esc quit"
        if self.tab == 1:
            return "Enter add · Tab switch · Shift+Tab previous · Esc quit"
        return "↑/↓ select · Space toggle · Enter on repo remove · Tab switch · Esc quit"

    def _switch_tab(self, step: int):
        self.tab = (self.tab + step) % 3
        self.status = "Loading repository…" if self.busy else ""
        target = [
            self.arguments if self.chosen else self.search,
            self.repository,
            self.manage_control,
        ][self.tab]
        self.app.layout.focus(target)

    def _select_script(self):
        scripts = self.scripts
        if not scripts:
            return
        script = scripts[self.index]
        if self.chosen != script:
            self.arguments.text = ""
        self.chosen = script
        self.status = ""
        self.app.layout.focus(self.arguments)

    def _clear_selection(self):
        self.chosen = None
        self.index = 0
        if self.tab == 0:
            self.app.layout.focus(self.search)

    def _manage_selected(self):
        rows = self.manage_rows
        if not rows:
            return
        row = rows[self.manage_index]
        if isinstance(row, str):
            self.pending_remove = row
            self.status = f"Remove {row} and its saved scripts? [y/n]"
        else:
            try:
                self.config.set_script_hidden(row.repo, row.name, not row.hidden)
            except OSError as error:
                self.status = f"Cannot save visibility: {error}"
            else:
                self._clear_selection()
                self.status = f"{row.name} {'shown' if row.hidden else 'hidden'}. Saved."

    async def _add_repository(self):
        if self.busy:
            return
        try:
            url = normalize_repo_url(self.repository.text)
        except ValueError as error:
            self.status = str(error)
            return
        self.busy = True
        self.status = "Loading repository…"
        self.app.invalidate()
        try:
            scripts = await asyncio.to_thread(fetch_script_list, url)
            self.config.add_repo(url, scripts)
        except (requests.RequestException, ValueError, OSError) as error:
            self.status = f"Cannot add repository: {error}"
        else:
            self.repository.text = ""
            self._clear_selection()
            self.manage_index = 0
            self.status = f"Saved {len(scripts)} scripts. Shift+Tab to run."
        finally:
            self.busy = False
            self.app.invalidate()

    def _bindings(self):
        bindings = KeyBindings()
        normal = Condition(lambda: self.pending_remove is None)
        browsing = normal & Condition(
            lambda: self.tab == 2
            or (self.tab == 0 and not self.app.layout.has_focus(self.arguments))
        )

        @bindings.add("tab", filter=normal, eager=True)
        def next_tab(event):
            self._switch_tab(1)

        @bindings.add("s-tab", filter=normal, eager=True)
        def previous_tab(event):
            self._switch_tab(-1)

        @bindings.add("up", filter=browsing)
        @bindings.add("down", filter=browsing)
        def move(event):
            step = -1 if event.key_sequence[0].key == "up" else 1
            if self.tab == 0 and self.scripts:
                self.index = (self.index + step) % len(self.scripts)
            elif self.tab == 2 and self.manage_rows:
                self.manage_index = (self.manage_index + step) % len(self.manage_rows)

        @bindings.add("insert", filter=normal & Condition(lambda: self.tab == 0))
        def insert(event):
            self._select_script()

        @bindings.add("enter", filter=normal, eager=True)
        def enter(event):
            if self.tab == 1 and self.busy:
                return
            self.status = ""
            if self.tab == 0:
                if self.chosen and self.app.layout.has_focus(self.arguments):
                    try:
                        args = shlex.split(self.arguments.text)
                    except ValueError as error:
                        self.status = f"Check argument quoting: {error}"
                    else:
                        self.app.exit(result=RunRequest(self.chosen, args))
                else:
                    self._select_script()
            elif self.tab == 1:
                if not self.busy:
                    self.app.create_background_task(self._add_repository())
            else:
                self._manage_selected()

        @bindings.add(" ", filter=normal & Condition(lambda: self.tab == 2))
        def toggle(event):
            rows = self.manage_rows
            if rows and isinstance(rows[self.manage_index], Script):
                self._manage_selected()

        @bindings.add("y", filter=~normal)
        def remove(event):
            try:
                self.config.remove_repo(self.pending_remove)
            except OSError as error:
                self.status = f"Cannot remove repository: {error}"
            else:
                self.status = "Repository removed."
                self._clear_selection()
                self.manage_index = 0
            self.pending_remove = None

        @bindings.add("n", filter=~normal)
        @bindings.add("escape", eager=True)
        def cancel(event):
            if self.pending_remove:
                self.pending_remove = None
                self.status = "Removal cancelled."
            elif self.tab == 0 and self.app.layout.has_focus(self.arguments):
                self.app.layout.focus(self.search)
            else:
                self.app.exit(result=None)

        @bindings.add("c-c", eager=True)
        @bindings.add("c-d", eager=True)
        def quit_menu(event):
            self.app.exit(result=None)

        return bindings

    def run(self) -> RunRequest | None:
        try:
            return self.app.run()
        except EOFError:
            return None


def open_menu(config: Config) -> RunRequest | None:
    return Menu(config).run()
