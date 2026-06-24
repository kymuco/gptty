# Release Checklist

This checklist is for publishing `gptty-web` to PyPI.

## Before Tagging

1. Confirm `pyproject.toml` has the intended version.
2. Confirm `CHANGELOG.md` has an entry for that version.
3. Confirm CI is green on `main`.
4. Confirm package metadata builds cleanly:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install build twine
   python -m build
   python -m twine check dist/*
   ```

5. Confirm the wheel installs and exposes the command:

   ```bash
   python -m pip install dist/*.whl
   gptty --version
   gptty auth status --auth missing-auth-data.json
   ```

   `gptty auth status` should run without optional auth-capture dependencies. It may exit with status 1 for a missing auth file; that is expected.

## PyPI Trusted Publishing

The publish workflow expects a PyPI trusted publisher for this repository:

- repository: `kymuco/gptty`
- workflow: `publish.yml`
- environment: `pypi`
- package name: `gptty-web`

The GitHub environment name must match the PyPI trusted publisher configuration.

## Publish

1. Merge the release-readiness PR.
2. Create and push a tag that matches the package version:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. Create a GitHub Release from the tag.
4. Publishing starts when the GitHub Release is published.
5. Confirm the package appears on PyPI.
6. Install from PyPI in a clean environment:

   ```bash
   python -m pip install gptty-web
   gptty --version
   ```

## Post-release Smoke Check

Use a real `auth_data.json` only locally. Never commit it.

```bash
gptty auth status
gptty ask "hello from gptty smoke test"
gptty attach https://chatgpt.com/c/...
gptty messages --last 1 --format json
```

If auth has expired, refresh it:

```bash
gptty auth refresh --mode wait
```
