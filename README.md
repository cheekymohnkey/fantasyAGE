# FantasyAGE

Home for my Fantasy AGE game notes and source material.

Contents:
- `source_material/2nD eDITIOn.md` — core source material.

Quick start:

1. Clone: `git clone git@github.com:cheekymohnkey/fantasyAGE.git`
2. Edit or add files, then `git add`, `git commit`, `git push`.

Developer notes (local run & tests):

- Apply DB migrations (creates `work-process/runtime/session.db` by default):

```bash
python3 work-process/scripts/migrate.py
```

- Run backend (uses `work-process/runtime/session.db` by default):

```bash
python3 backend/app.py
```

- Override DB path with the `SESSION_DB` env var (useful in tests):

```bash
SESSION_DB=/tmp/session.db python3 backend/app.py
```

- Run the Python test suite (requires `pytest`):

```bash
python3 -m pip install -r backend/requirements.txt  # if present
python3 -m pip install pytest requests Flask Flask-Cors
python3 -m pytest -q
```

- Run backend lint and type checks:

```bash
ruff check backend tests
mypy --config-file pyproject.toml backend
```

- Run frontend tests:

```bash
cd frontend
npm install
npm test -- --run
```

License: Add a `LICENSE` file if you want this repository to be licensed.
