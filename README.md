# sweng861-crud-ekk5635

**Eungchan Kang**

SWENG 861 – Software Construction

## Planned CRUD App

A CRUD API and web UI where each user writes and maintains their own company
analysis notes. Financial figures are pulled from SEC EDGAR filings to support
each note.

## Backend — Hello/Health API (Week 1, Assignment 3)

FastAPI service in `week-01-setup/backend/`.

### Run locally

```bash
cd week-01-setup/backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Requires Python 3.10 or newer.

### Endpoints

| Method | Path | Response |
| ------ | ---- | -------- |
| GET | `/health` | `{"status": "ok"}` |
| GET | `/api/hello` | `{"message": "Hello, World!"}` |

Interactive API docs are served at `http://127.0.0.1:8000/docs`.

### Verify

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/api/hello
```

Both return `200 OK` with `content-type: application/json`.

### AI usage

The first draft of `main.py` was written with Claude Code. I reviewed the
routing and return types line by line, deliberately kept `/health` outside the
`/api` prefix because it is an infrastructure probe rather than an application
feature, and verified both endpoints with curl before committing.
