# CHANGELOG

## Unreleased

- Require certifi >= 2026.10.19 for repository discovery.
- Check the uv executable and reject versions below 0.13.4 before running scripts.
- Return script exit codes to the caller.
- Document existing installation upgrades and bootstrap release CI with verified pip.


## v0.1.3 (2025-01-20)

### Bug Fixes

- Rename uvrun_simonb97 package to uvrun
  ([`fd15720`](https://github.com/SimonB97/uvrun/commit/fd157207f2c9118adf878f2f87d0e3e3cceef339))

- Trigger pipeline test
  ([`836d352`](https://github.com/SimonB97/uvrun/commit/836d3527110bede9ce1622197b392197ce148c80))

- Trigger version bump for testing
  ([`aa69557`](https://github.com/SimonB97/uvrun/commit/aa695578b12528dc8fc9dd60b1c0d4001c70de90))

- **readme**: Update installation and usage instructions with metadata details
  ([`93c8ea7`](https://github.com/SimonB97/uvrun/commit/93c8ea7bd7759cc4f0a94da958d5b07f0a1dc2e0))

### Chores

- Bump version to 0.1.3
  ([`5400196`](https://github.com/SimonB97/uvrun/commit/540019698e319667c5d9e30a0f6432b3e8cb5abd))

- Bump version to 0.1.4
  ([`bf95a13`](https://github.com/SimonB97/uvrun/commit/bf95a13ac5cf5ef77b85298715f3f8fd71b2ea54))

- Bump version to 0.1.5
  ([`b227a12`](https://github.com/SimonB97/uvrun/commit/b227a121412cc9f7a95b42b6192debe2dbcf5b37))

- **ci**: Update publish workflow and configuration
  ([`7c84473`](https://github.com/SimonB97/uvrun/commit/7c844732e95fda98efe67d9956735eeb360a1212))

- **ci**: Update publish workflow and project configuration
  ([`c08461b`](https://github.com/SimonB97/uvrun/commit/c08461b95bd3af56135cf76c9ed60921e8e43e0a))

- **gitignore**: Add dist directory to ignored files
  ([`901dcf1`](https://github.com/SimonB97/uvrun/commit/901dcf110a56c353b4fd8b29ed014b300ae2b416))

- **release**: Update semantic release configuration for changelog and zero-major versions
  ([`5304656`](https://github.com/SimonB97/uvrun/commit/530465692c2bf80cf46cbf1366b380d55e2a9c9c))

### Continuous Integration

- Add build step and metadata verification for pypi publish
  ([`757fb34`](https://github.com/SimonB97/uvrun/commit/757fb3434e18d2af82cab1d76fef43e0cc424571))

- Streamline release and publish steps in workflow
  ([`f6a585f`](https://github.com/SimonB97/uvrun/commit/f6a585f0410a2c1e2923a3102d6a2b34f717029a))

- Update github action for publishing to pypi
  ([`dcec27f`](https://github.com/SimonB97/uvrun/commit/dcec27fc3eb513d7f7a3ed04dda25566b7a866aa))

- Update publish workflow to streamline versioning and release steps
  ([`4fac140`](https://github.com/SimonB97/uvrun/commit/4fac140b3d5e8fba668df0e4e5c26cb2dcdaf5ff))

- Update pypi url and action version in publish workflow
  ([`e84ee73`](https://github.com/SimonB97/uvrun/commit/e84ee73bef8f3af2ae6ca15d3760dbdedac73c3c))


## v0.1.2 (2025-01-19)

### Bug Fixes

- **project**: Update package name to uvrun_simonb97
  ([`26a0e26`](https://github.com/SimonB97/uvrun/commit/26a0e26f44f034c09b33c0a90c2a1e7199985d26))

### Chores

- Rename package from uvrun_simonb97 to uvrun
  ([`d01e079`](https://github.com/SimonB97/uvrun/commit/d01e0796f4da71d2e404d7ce1b54ae59419b31e5))

### Continuous Integration

- Add conditional publishing based on version change
  ([`4c70aaf`](https://github.com/SimonB97/uvrun/commit/4c70aaf7df293edd551806f74f6a7c24bfd76768))

- Simplify version change check in publish.yml
  ([`d959429`](https://github.com/SimonB97/uvrun/commit/d959429ac4430a71ce957fb881a98ec16a64b738))

### Documentation

- **contributing**: Update example for semantic commit messages
  ([`3e8f534`](https://github.com/SimonB97/uvrun/commit/3e8f53485e7e71ff44ea3e962aa6dbdc202061fa))


## v0.1.1 (2025-01-19)

### Bug Fixes

- **readme**: Correct uvrun command for adding a repository
  ([`70edde4`](https://github.com/SimonB97/uvrun/commit/70edde44050253ed9c4a206129c6ca1f4cff3d77))

### Continuous Integration

- Add manual workflow dispatch trigger
  ([`ece42c4`](https://github.com/SimonB97/uvrun/commit/ece42c42f3cefdc9411c389973db39d9c06dca96))

- Update publish workflow with environment and permissions settings
  ([`c1944d9`](https://github.com/SimonB97/uvrun/commit/c1944d9ee2225277befad18c62384cd994406d80))

- Update workflow for release and publish automation
  ([`d703cb5`](https://github.com/SimonB97/uvrun/commit/d703cb5a0852e9fbfab66298e42b7dd600d74a2c))


## v0.1.0 (2025-01-19)

### Build System

- Modify build requirements and command in pyproject.toml
  ([`2726818`](https://github.com/SimonB97/uvrun/commit/2726818395898ecfbc3b31a823365fdc204d7de7))

### Continuous Integration

- Update workflows and commitlint configuration
  ([`7f26f75`](https://github.com/SimonB97/uvrun/commit/7f26f754102daaf4f2e08c55b2d83b8c15c4a506))

### Features

- Add commit linting, automated publishing workflow, pre-commit hooks, and code quality tools
  ([`567d365`](https://github.com/SimonB97/uvrun/commit/567d3656510c6ca777b2786635eb83def775b72e))
