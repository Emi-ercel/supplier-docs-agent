# Contributing

Before opening a pull request, run the same checks CI runs:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

If you change the generator, run `uv run generate-data` and commit the files in `data/`. A test fails if they are out of date.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `feat(scope): ...`, `fix: ...`, `test: ...`, `docs: ...`, `ci: ...`, `chore: ...`.
