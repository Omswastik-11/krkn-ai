## 🤝 Contributing

Thanks for your interest in contributing to this project! The goal of this document is to make contributing straightforward and to explain the conventions the project uses for commits and PRs so automation (labels and releases) works reliably.

### Quick start

1. Fork the repository.
2. Create a feature branch using a descriptive name, e.g. `feature/amazing-feature` or `fix/issue-123-bug`.
3. Make changes in your branch and run the checks locally (see **Checks & tests** below).
4. Commit your changes using the Conventional Commit style described below.
5. Push your branch: `git push origin <branch-name>`
6. Open a Pull Request against `main` and ensure the PR title follows the semantic format (see **PR title format**).

### PR title format (required)

We use a semantic PR/title convention to enable automatic labeling and to drive automated releases. The `amannn/action-semantic-pull-request` workflow validates PR titles — it will fail the check if the title doesn't match the allowed types. The allowed types are:

- feat
- fix
- docs
- style
- refactor
- perf
- test
- build
- ci
- chore
- revert

Format examples:

- `feat: add support for multi-namespace experiments`
- `fix(cli): handle missing kubeconfig path`
- `docs: update README examples`

Scope is optional (e.g. `fix(cli): ...`) but helpful. If the PR title check fails, update the PR title to match one of the types above.

### Commit messages

Follow Conventional Commits for individual commits where possible — release tooling (release-please) uses commit types to determine version bumps. See the specification for details: https://www.conventionalcommits.org/en/v1.0.0/

Common types and short examples:

- `feat(scope): description` — Adds a new feature.
	- Example: `feat(parser): add support for YAML configs`
- `fix(scope): description` — Bug fix.
	- Example: `fix(auth): handle token refresh failure`
- `docs(scope): description` — Documentation only changes.
	- Example: `docs(readme): clarify installation steps`
- `style: description` — Formatting, missing semi-colons, etc; no code change.
	- Example: `style: format code with black`
- `refactor(scope): description` — Code change that neither fixes a bug nor adds a feature.
	- Example: `refactor(core): split runner into smaller modules`
- `perf(scope): description` — Performance improvement.
	- Example: `perf(db): reduce query latency by adding index`
- `test(scope): description` — Add or update tests.
	- Example: `test(api): add integration tests for endpoints`
- `build: description` — Changes that affect the build system or external dependencies.
	- Example: `build: update pyproject metadata`
- `ci: description` — CI configuration changes.
	- Example: `ci: update GitHub Actions workflow node version`
- `chore: description` — Other changes that do not modify src or test files.
	- Example: `chore: bump development dependencies`
- `revert: description` — Revert a previous commit.
	- Example: `revert: revert "feat: add experimental API"`

Using scope is optional but recommended for clarity (e.g. `fix(cli): ...`).

BREAKING CHANGES

If your change introduces a breaking API change, include a `BREAKING CHANGE:` section in the commit body or include an exclamation mark after the type (e.g. `feat!: description`). Example:

```
feat(api): change config schema

BREAKING CHANGE: `kubeconfig_file_path` renamed to `kubeconfig_path`.
```

Release mapping (how `release-please` treats commits):

- `feat` -> minor version bump
- `fix` -> patch version bump
- `BREAKING CHANGE` -> major version bump

Example full commit message:

```
feat(api): add enhanced health-check endpoint

Add timeout and retry behavior to the health endpoint to improve stability when the cluster is under load.

BREAKING CHANGE: the previous health-check endpoint path `/health` now returns structured JSON.
```

If you have WIP commits while developing, it's fine to use informal messages locally, but ensure the final commits (or at least the PR title) follow the convention before merging.

### Signing commits

We recommend signing commits for contributor verification. You can sign with GPG or use GitHub's CLI/commit signing features. Example:

```
git commit -S -m "fix: correct typo in logger"
```

Or use `-s` to add a signed-off-by line when required by maintainers.

### Checks & tests

Run the test suite and pre-commit hooks before opening a PR:

```bash
# Install dev deps (if not installed)
pip install -e .[dev]

# Run all pre-commit hooks locally
pre-commit run --all-files

# Run tests
pytest -q
```

The repository's CI runs `pre-commit` on changed files and runs the test suite; fixing issues locally will help your PR pass CI faster.

### Opening a Pull Request

- Base branch: `main`
- Ensure the PR title follows the semantic format described above.
- Provide a short description of the change and list any steps required to validate it.
- If your change affects public APIs or configuration, document the change and any migration steps in the PR description.


### Reporting issues

For bugs or feature requests, open an issue and include steps to reproduce, expected and actual behavior, and relevant logs or configuration.

### Maintainers & contacts

If you're unsure about how to classify a change, ask a maintainer on the PR or open a short issue describing the intended change.

---
Thank you for contributing — we appreciate your time and help!
