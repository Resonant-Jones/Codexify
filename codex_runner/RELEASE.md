# Release Guide (`codexify-campaign-runner`)

This guide covers how to cut and publish a release to PyPI.

## 1. Prerequisites

- Python 3.11+
- Packaging tools:
  - `python -m pip install -U build twine`
- PyPI account + API token
- Optional but recommended: TestPyPI account + API token

Set tokens as environment variables:

```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="<pypi-token>"
```

For TestPyPI:

```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="<testpypi-token>"
```

## 2. Bump Version

Update version in:

- `pyproject.toml` -> `[project] version = "X.Y.Z"`

Use SemVer:

- Patch: bug fixes (`0.1.0` -> `0.1.1`)
- Minor: backwards-compatible features (`0.1.0` -> `0.2.0`)
- Major: breaking changes (`0.1.0` -> `1.0.0`)

## 3. Run Quality Checks

From this directory (`codex_runner/`):

```bash
pytest -q
```

## 4. Build Distributions

Clean and build:

```bash
rm -rf dist build *.egg-info
python -m build
python -m twine check dist/*
```

If your environment is offline, use:

```bash
python -m build --no-isolation
```

## 5. Publish to TestPyPI (recommended)

```bash
python -m twine upload --repository testpypi dist/*
```

Validate install in a clean virtualenv:

```bash
python -m venv /tmp/codex-runner-test
source /tmp/codex-runner-test/bin/activate
pip install -i https://test.pypi.org/simple/ codexify-campaign-runner
codex-runner --help
deactivate
```

## 6. Publish to PyPI

```bash
python -m twine upload dist/*
```

## 7. Post-release Verification

Install from PyPI:

```bash
python -m venv /tmp/codex-runner-prod
source /tmp/codex-runner-prod/bin/activate
pip install codexify-campaign-runner
codex-runner --help
deactivate
```

Confirm TUI starts in an interactive shell:

```bash
codex-runner --tui
```

## 8. Git Release Hygiene (recommended)

From repo root:

```bash
git add codex_runner/pyproject.toml codex_runner/RELEASE.md
git commit -m "Release codexify-campaign-runner vX.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```
