# uvrun

[![PyPi Version](https://img.shields.io/pypi/v/uvrun.svg)](https://pypi.python.org/pypi/uvrun/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/uvrun?style=flat)

Run Python scripts with inline metadata directly from URLs. This simple tool integrates with [uv](https://github.com/astral-sh/uv) to provide a seamless experience for running Python scripts from GitHub repositories.

## Interactive menu

Run `uvrun` without arguments in a terminal to open the menu:

- **Run:** use ↑/↓ or type to filter scripts. Enter or Insert selects a script.
  Append arguments, then press Enter to run. Quote paths with spaces, for example
  `"my audio.wav" --output "new folder"`. Escape returns to the script list.
- **Add repository:** paste a GitHub repository URL and press Enter.
- **Manage:** select a script and press Space or Enter to show or hide it.
  Select a repository and press Enter, then `y` to remove it or `n` to cancel.

Tab and Shift+Tab switch views. Ctrl+C exits. Escape exits from a view's main input.
Saved repositories are checked automatically when opening the menu, listing scripts,
or running a script by name. New, renamed, and removed scripts are detected without
re-adding the repository. Unchanged repositories reuse their saved script lists.
If GitHub is unavailable or rate-limits requests, uvrun warns and uses the last saved list.
Visibility choices are preserved and saved in `~/.config/uvrun/config.toml`. Hidden scripts are omitted
from the Run tab and `uvrun --list`, but can still be run by name.
Removing a repository only removes it from uvrun's saved configuration.
The menu closes before the script starts, so the script gets normal terminal input and output.
Outside an interactive terminal, bare `uvrun` prints help instead.

## Features

- Run Python scripts directly from GitHub repositories
- Manage multiple script repositories
- Smart script discovery with inline metadata
- Pass arguments directly to scripts and uv
- List available scripts with a nice directory structure

## Installation

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) >= 0.13.4
and make it available on `PATH`. uvrun checks this executable before running scripts.

```bash
pip install uvrun
```

## Security update: October 2026

The [emSign certificate incident](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
affects both Requests' certificate bundle and uv's separate certificate bundle.

For existing installations:

1. Follow the notice's hash-verified bootstrap to update pip to >= 26.2.2.
2. In the Python environment containing uvrun, run:
   ```bash
   python -m pip install --upgrade uvrun "certifi>=2026.10.19"
   ```
3. Upgrade uv using its original installation method. Check `uv --version`;
   it must be >= 0.13.4. For standalone installations, with an updated OS trust store:
   ```bash
   UV_SYSTEM_CERTS=true uv self update
   ```

Updating certifi does not update uv. Update separate pipx or uv tool environments
as well. Scripts with their own HTTPS dependencies need updated certificate
bundles in their own environments.

## Usage

Add a repository:

```bash
uvrun --add https://github.com/username/repo
```

List available scripts:

```bash
uvrun --list
```

Run a script:

```bash
uvrun script_name arg1 arg2
```

(Note: both script_name and script_name.py are valid)

With specific Python version:

```bash
uvrun script_name --uv-args "--refresh"
```

## Script Metadata

To make a script discoverable by uvrun, add the following [inline metadata](https://peps.python.org/pep-0723/) at the top of the file:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask>=2.0.0",
#     "requests>=2.31.0",
# ]
# ///
```

## License

[MIT License](LICENSE)
