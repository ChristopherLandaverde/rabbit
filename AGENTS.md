# Repository working instructions

## Environment

- Use Python 3.12 for backend development and CI.
- Create `.venv` at the repository root; it is gitignored.
- Prefer `uv` when it is installed. The standard `venv` and `pip` commands below are supported too.

## Exact commands

Install with `uv`:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Or install with standard Python:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The MCP server (`python -m src.mcp_server`) and its tests need the optional
`requirements-mcp.txt` too; CI installs it:

```bash
uv pip install --python .venv/bin/python -r requirements-mcp.txt
```

Run the complete test suite:

```bash
python -m pytest -q
```

`tests/known_failures.txt` lists baseline failing pytest node IDs as strict xfails
and collection-error modules to ignore. `tests/redis_required.txt` lists tests
that exercise the live Redis service; `conftest.py` probes the configured Redis
endpoint once per pytest session and skips those tests with `needs Redis` when
the endpoint cannot be reached. With Redis available, they run normally. A known
test that starts passing fails CI because the xfail is strict; delete its line
from the known-failure list when fixing it. New or previously passing tests that
fail remain ordinary failures.

Start the API from the repository root:

```bash
source .venv/bin/activate
python run.py
```

Check API health from another terminal:

```bash
curl http://127.0.0.1:8000/health
```

## Conventions

- `run.py` is the single backend entrypoint; do not add alternate entrypoints.
- Keep dependency pins compatible with Python 3.12 and installable from `requirements.txt`.
- Do not change attribution math without an explicit task. Preserve the five model outputs on `test_data.csv` when changing dependencies or surrounding code.
- Treat attribution as model-based association, not causal impact.
- Keep `.venv`, logs, uploaded files, and generated test artifacts out of version control.
- Record test baseline changes and known failures in `docs/b0-baseline.md`.

## Merging

Standing permission from the owner (Christopher Landaverde, 2026-10-30): agents merge their own pull requests, user-visible ones included, without asking, when all of these hold:
- CI is green on GitHub on the PR's latest commit (`gh pr checks <n>`; local runs don't count).
- An agent other than the author reviewed the diff and posted `Blocking findings: none`.
- The PR merges cleanly into `main`.

Merge with `gh pr merge <n> --squash --delete-branch`, then confirm `main` CI passes. Still stop and ask for: releases, tags, store or package publishing, deploys, repo settings or visibility, spending money, and deleting anything you didn't create. Never push directly to `main` or force-push a shared branch.
