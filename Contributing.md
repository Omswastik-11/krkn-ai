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

Follow Conventional Commits for individual commits where possible — release tooling (release-please) uses commit types to determine version bumps:

- `feat:` -> minor bump
- `fix:` -> patch bump
- `BREAKING CHANGE:` -> major bump

Example commit message:

```
feat(api): add enhanced health-check endpoint

Add timeout and retry behavior to the health endpoint.
```

If you cannot follow the format for a small or WIP change, ensure the PR title is correct before merging.

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

### Labels and automation

This project uses automated labeling (path-based) and a semantic PR check for PR titles. Labels are applied by `.github/labeler.yml` based on changed paths. The semantic PR workflow will block merge until a valid title is provided.

Release automation is handled by `googleapis/release-please-action` which reads commit messages and PRs to create changelogs and release PRs. To ensure correct release behavior, prefer `feat:` and `fix:` commit types when the changes match those categories.

### PR template and CONTRIBUTING improvements

Tip: We recommend adding a PR template at `.github/pull_request_template.md` to remind contributors about the title format and checklist items (tests, changelog, etc.).

### Reporting issues

For bugs or feature requests, open an issue and include steps to reproduce, expected and actual behavior, and relevant logs or configuration.

### Maintainers & contacts

If you're unsure about how to classify a change, ask a maintainer on the PR or open a short issue describing the intended change.

---
Thank you for contributing — we appreciate your time and help!
