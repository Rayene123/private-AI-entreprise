# Backend

FastAPI foundation for the Private Enterprise AI Platform.

## Local Setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` for local development and fill values outside source control.

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```

## Health

```text
GET /health
```

Returns:

```json
{"status": "ok"}
```
