Minimal backend to accept command POSTs.

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/app.py
```

The server listens on port 8000 and exposes `POST /api/command`.
