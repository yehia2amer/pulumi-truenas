# Contributing to pulumi-truenas

Thanks for your interest! This is a Python Pulumi component library.

## Development setup

```bash
git clone https://github.com/yehia2amer/pulumi-truenas
cd pulumi-truenas
uv sync
```

## Checks (run before opening a PR)

```bash
uv run ruff check src tests scripts     # lint
uv run ruff format src tests scripts    # format
uv run pyrefly check                     # type check
uv run pytest -q                         # tests
```

CI runs the same checks on Python 3.9–3.13 plus a clean-venv build/install
smoke test.

## Guidelines

- Keep the library **generic** — no deployment-specific defaults (hosts, users,
  paths). Deployment specifics belong in `examples/`.
- `values` for catalog apps stay **pass-through** (per-app, per-version
  schemas). Don't hardcode app schemas in the library.
- New resources need `check`, `create`, `read` (import-safe), `diff`, `update`,
  `delete`, plus unit tests.
- Preserve **safety defaults**: no volume/dataset/directory destruction by
  default.
- Update `CHANGELOG.md` under `[Unreleased]`.

## Testing against a real TrueNAS

Most tests use fakes and need no NAS. To run manual live checks, use
`scripts/preflight.py` against a test host. Never commit API keys.

## Releasing (maintainers)

1. Update `version` in `pyproject.toml` and `CHANGELOG.md`.
2. Tag `vX.Y.Z` and push — the release workflow builds, publishes to TestPyPI,
   then PyPI via OIDC trusted publishing.
