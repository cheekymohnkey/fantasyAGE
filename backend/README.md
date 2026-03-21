Minimal backend to accept command POSTs.

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m backend.app
```

The server listens on port 8000 and exposes `POST /api/command`.

Migrations & config
-------------------

- Migrations are applied by `work-process/scripts/migrate.py`. Run it before starting the server to bootstrap the DB schema and seed `runtime_config`:

```bash
python3 work-process/scripts/migrate.py
```

- The app reads a `SESSION_DB` environment variable to override the default DB path (useful for tests or alternate runtimes). Example:

```bash
SESSION_DB=/tmp/session.db python3 -m backend.app
```

Response contract
-----------------

- The command endpoint returns a small canonical payload to help frontends normalize results. Example fields returned on success:

```
{
	"status": "ok",
	"action_id": "NO_OP",
	"action": "NO_OP",
	"idempotency_key": "...",
	"idempotency": "...",
	"action_result": {},
	"action_result_json": "{}",
	"event": null
}
```
