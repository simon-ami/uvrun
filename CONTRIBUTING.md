# Contributing

## Development Setup

```bash
# Clone and install
git clone https://github.com/simonb97/uvrun.git
cd uvrun
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install --hook-type commit-msg
```

## Repository Setup (One-time)

1. GitHub releases use the workflow's built-in repository token.
   The release job grants it `contents: write`. No personal access token is needed.

2. Set up PyPI publishing:
   - Create account at https://pypi.org/account/register/
   - In repository settings:
     - Go to Settings → Environments
     - Create environment named `pypi`
     - No secrets needed (uses OIDC)

## Development Workflow

1. Write code
2. Commit with semantic prefix:
   ```bash
   fix: fix a bug           → PATCH version bump (1.0.0 → 1.0.1)
   feat: add new feature     → MINOR version bump (1.0.0 → 1.1.0)
   feat!: breaking change   → MAJOR version bump (1.0.0 → 2.0.0)
   ```
3. Push to main

The rest happens automatically:

- Version bump based on commit
- GitHub release creation
- Package build and PyPI publish

## Commit Guidelines

Format: `type(scope): description` or `type!: description` for breaking changes

Types:

- `fix`: Bug fix (PATCH)
- `feat`: New feature (MINOR)
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding/updating tests
- `build`: Build system changes
- `ci`: CI configuration changes
- `chore`: Other changes that don't modify src/test files

Breaking Changes:

- Add `!` after type: `feat!: breaking change`
- Or add `BREAKING CHANGE:` in commit body

Examples:

```bash
fix(config): handle missing config file
feat(gitlab): add support for gitlab repositories
feat!: change CLI interface
```

## Versioning

The next release is 0.1.6. Both version files are prepared for that version.
CI restores the missing v0.1.5 tag at its original published commit and forces
one patch release. Later releases use semantic version calculation from Git tags.
Do not infer the next release from version files alone.

Commits trigger automatic version bumps:

- `fix:` → Patch version (1.0.0 → 1.0.1)
- `feat:` → Minor version (1.0.0 → 1.1.0)
- `BREAKING CHANGE:` → Major version (1.0.0 → 2.0.0)

## Code Quality

Pre-commit hooks handle:

- Commit message format (commitlint)
- Code formatting (ruff)
- Import sorting (ruff)
- Basic checks (trailing whitespace, file size, etc)

Run manually: `pre-commit run --all-files`.
Run tests with `python -m unittest discover -s tests -v`.

Release CI installs Hatchling with the patched pip, then builds with
`python -m build --no-isolation`. This prevents isolated build environments
from bootstrapping an older pip certificate bundle.

If the PyPI upload fails, rerun only the failed publish job. It reuses the
stored distribution artifacts without creating another release. GitHub asset uploads
run in a separate job and do not block PyPI publishing.
