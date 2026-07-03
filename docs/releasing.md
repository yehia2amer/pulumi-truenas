# Releasing

Releases are automated via GitHub Actions using **PyPI trusted publishing**
(OIDC) — no API tokens are stored.

## One-time setup (before the first release)

1. Push this package to its own GitHub repository (done:
   `yehia2amer/pulumi-truenas`).
2. Create two GitHub **Environments**: `testpypi` and `pypi`.
3. Configure PyPI/TestPyPI **trusted publishers** pointing at this repo +
   `release.yml` workflow + the matching environment:
   - PyPI: https://pypi.org/manage/account/publishing/
   - TestPyPI: https://test.pypi.org/manage/account/publishing/
   Use project name `pulumi-truenas`, workflow `release.yml`.

## Cutting a release

1. Bump `version` in `pyproject.toml`.
2. Move `CHANGELOG.md` items from `[Unreleased]` into a new version section
   with today's date; update the compare/tag links.
3. Commit, then tag and push:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. The `Release` workflow runs: tests → build → clean-venv install check →
   publish to **TestPyPI** → publish to **PyPI**.

## Verifying

```bash
pip install pulumi-truenas
python -c "import pulumi_truenas as t; print(t.__version__)"
```
