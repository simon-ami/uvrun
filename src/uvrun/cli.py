import shlex
import shutil
import subprocess

import click
from packaging.version import InvalidVersion, Version
from rich.console import Console

from .config import Config
from .discover import fetch_script_list

console = Console()

MIN_UV_VERSION = Version("0.13.4")


def checked_uv() -> str:
    """Check the executable that will download and run the script."""
    executable = shutil.which("uv")
    if executable is None:
        raise click.ClickException(
            f"uv >= {MIN_UV_VERSION} is required. Install uv and add it to PATH."
        )
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise click.ClickException(f"Cannot check uv version: {error}") from error

    fields = result.stdout.split()
    if len(fields) < 2 or fields[0] != "uv":
        raise click.ClickException(f"Unexpected uv version output: {result.stdout.strip()!r}")
    try:
        version = Version(fields[1])
    except InvalidVersion as error:
        raise click.ClickException(f"Invalid uv version: {fields[1]!r}") from error
    if version < MIN_UV_VERSION:
        raise click.ClickException(
            f"uv {version} is affected by the emSign certificate incident. "
            f"Upgrade uv to >= {MIN_UV_VERSION} with its installation method. "
            "See https://docs.astral.sh/uv/getting-started/installation/#upgrading-uv"
        )
    return executable


@click.command(help="Run Python scripts with inline metadata directly from URLs")
@click.version_option()
@click.option("--add", "-a", help="Add a GitHub repository URL containing Python scripts")
@click.option("--list", "-l", "show_list_flag", is_flag=True, help="List all available scripts")
@click.argument("script_and_args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--uv-args", "-ua", help="Arguments to pass to uv run command, e.g. '--ua \"--python 3.11\"'"
)
@click.option("--refresh", is_flag=True, help="Pass --refresh flag to uv run command")
def cli(
    add: str | None,
    show_list_flag: bool,
    script_and_args: tuple,
    uv_args: str | None,
    refresh: bool,
) -> None:
    config = Config()

    if add:
        try:
            scripts = fetch_script_list(add)
            config.add_repo(add, scripts)
            script_count = len(scripts)
            console.print(
                f"[green]Found {script_count} script{'s' if script_count != 1 else ''} "
                "in repository[/green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to add repository: {e}[/red]")
            return

    if show_list_flag:
        show_list()
        return

    if script_and_args:
        script_name = script_and_args[0]
        script_args = list(script_and_args[1:])

        script_url = config.get_script_url(script_name)
        if script_url:
            cmd = [checked_uv()]
            if uv_args:
                cmd.extend(shlex.split(uv_args))
            cmd.extend(["run"])
            if refresh:
                cmd.append("--refresh")
            cmd.extend([script_url] + script_args)
            raise click.exceptions.Exit(subprocess.run(cmd).returncode)
        else:
            console.print(f"[red]Script {script_name} not found[/red]")


def show_list():
    config = Config()
    console.print("[dim]Note: Scripts can be run with or without .py extension[/dim]\n")
    for repo_url, repo_info in config.config["repos"].items():
        console.print(f"[bold blue]{repo_url}[/bold blue]")
        scripts_by_dir = {}
        for script_path in sorted(repo_info["scripts"].values()):
            dir_name = script_path.rsplit("/", 1)[0] if "/" in script_path else ""
            if dir_name not in scripts_by_dir:
                scripts_by_dir[dir_name] = []
            scripts_by_dir[dir_name].append(script_path)

        for dir_name, scripts in sorted(scripts_by_dir.items()):
            if dir_name:
                console.print(f"  [dim]{dir_name}/[/dim]")
            for script_path in scripts:
                script_name = script_path.split("/")[-1]
                padding = "    " if dir_name else "  "
                console.print(f"{padding}[green]{script_name}[/green]")


def main():
    cli()
