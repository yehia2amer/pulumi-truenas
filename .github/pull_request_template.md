## What

Brief description of the change.

## Why

Motivation / linked issue.

## Checklist

- [ ] `uv run ruff check src tests scripts` passes
- [ ] `uv run ruff format --check src tests scripts` passes
- [ ] `uv run pyrefly check` passes
- [ ] `uv run pytest -q` passes
- [ ] No deployment-specific defaults added to the library
- [ ] Safety defaults preserved (no destructive-by-default deletes)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
