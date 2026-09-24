# Publish runbook — laya-ultrafast 0.1.0

Version discipline: single source in `pyproject.toml` (`version =
"0.1.0"`), mirrored in `ultrafast/__init__.py` (`__version__`).
CHANGELOG `0.1.0` matches. Bump all three together; CI has no
version gate, so check by hand before tagging.

Name status (2026-09-23): `laya-ultrafast` is FREE on PyPI
(`https://pypi.org/pypi/laya-ultrafast/json` → 404). No `.pypirc`
on this machine; upload needs a PyPI API token (never commit it).

## Dry run (verified 2026-09-23, twine 7.0.0)

```bash
uv build
uv run --with twine twine check dist/*
# dist-only dry upload, no credentials leave the machine:
uv run --with twine twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

`twine check` passes on both wheel + sdist. Upload dry-run verified
2026-09-23: `twine upload --repository-url
https://test.pypi.org/legacy/ dist/*` with a dummy token reaches the
server and gets a clean auth 403 (packaging valid, credentials
rejected as expected) — no credentials on this machine, nothing
published. First real upload goes to TestPyPI, verify the page +
`uv pip install -i https://test.pypi.org/simple/ laya-ultrafast` in
a clean venv, then PyPI.

## Pre-publish checklist

- `uv run ruff check . && uv run ruff format --check . && uv run pytest`
- `uv run python scripts/bench_mock.py --runs 5` regenerates
  `docs/benchmarks.md` + `benchmarks.json` (commit both)
- `git tag v0.1.0` only when the tree is clean and CI is green
- sdist hygiene: `dist/` is gitignored; the sdist bundles
  `uv.lock` (harmless) but excludes `dist/`, `recordings/`,
  `.env`, `__pycache__`, demo mp4/gif via `docs/demo.*`
  force-add (tracked files ship regardless of gitignore)
