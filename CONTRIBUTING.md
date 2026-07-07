# Contributing

## Branch strategy

- `main` — stable, deployable
- `develop` — integration branch (optional)
- Feature branches: `feat/<short-description>`
- Bug fixes: `fix/<short-description>`

## Development workflow

1. Branch off `main`:

   ```bash
   git checkout -b feat/my-feature
   ```

2. Make your changes, then **before committing**, run this sequence:

   **Python — fix, format, verify:**

   ```bash
   uv run ruff check . --fix
   uv run ruff format .
   uv run pyright backend/ agent/
   uv run pylint backend/ agent/
   ```

   Then do a final dry run to confirm what CI will see:

   ```bash
   uv run ruff check .              # should print: All checks passed.
   uv run ruff format --check .     # should print: N files already formatted
   uv run pyright backend/ agent/   # should print: 0 errors
   uv run pylint backend/ agent/    # should print: 10.00/10
   ```

   **Frontend:**

   ```bash
   npm run lint                     # ESLint + TypeScript
   npm run test                     # Vitest
   ```

   **Python tests:**

   ```bash
   uv run pytest
   ```

3. Push and open a pull request against `main`. The CI pipeline runs automatically and will fail if lint or format checks don't pass.
4. Squash-merge after approval.

> **Note on unused imports (`F401`):** ruff's `--fix` intentionally skips removing unused imports because `__init__.py` files use them for re-exports. If ruff reports an `F401` violation after running `--fix`, remove that import manually.

## CI checks

- **What runs:** The repository's CI (GitHub Actions) runs linting, formatting checks, type checking, and tests for both backend and frontend on pull requests.
- **Must pass:** Pull requests should pass CI before merging; branch protection may require a green CI status.
- **Run locally:** To reproduce CI checks locally, run the same commands described above (use `uv` for Python tasks and `npm` for frontend):

```bash
# Python checks
uv run ruff check . --fix
uv run ruff format --check .
uv run pyright backend/ agent/
uv run pylint backend/ agent/
uv run pytest backend/ agent/ -v

# Frontend checks
npm run setup
npm run lint
npm run test
```

Add these checks to your local workflow or pre-commit hooks if you want to catch issues earlier.

## Commit message format

```text
<type>: <short summary>

Types: feat, fix, chore, docs, refactor, test
```

Examples:

- `feat: add DNS bulk import endpoint`
- `fix: handle null site_id in downtime creation`
- `docs: update API_USAGE with rollback endpoints`

## Adding a new agent skill

1. Create a folder under `agent/skills/<skill-name>/`
2. Add a `SKILL.md` describing the skill's purpose, inputs, and outputs
3. Register the skill in `agent/filesystem/subagents.py`
4. Add a brief entry in `API_USAGE.md` if it exposes new agent behaviour

## Code style

**Frontend:** ESLint + TypeScript (`npm run lint`). Config lives in `frontend/`.

**Python:** [ruff](https://docs.astral.sh/ruff/) handles both linting and formatting. Config lives in `pyproject.toml` under `[tool.ruff]`. Active rule sets:

| Set       | What it catches                                              |
| --------- | ------------------------------------------------------------ |
| `E / W`   | PEP 8 style errors                                           |
| `F`       | Undefined names, unused imports                              |
| `I`       | Import ordering (isort-compatible)                           |
| `UP`      | Syntax that can be modernised for Python 3.13                |
| `B`       | Common bug patterns (bare`except`, mutable defaults, etc.)   |
| `ASYNC`   | Blocking calls inside`async def`                             |
| `SIM`     | Simplifiable expressions                                     |
| `RUF`     | Ruff-native best practices                                   |

General guidelines:

- Line length: 100 characters
- Double quotes throughout (matches existing codebase)
- Keep functions small and focused; avoid files over ~300 lines
