# entrystock

## Development setup

Install the locked dependencies and run the test suite with:

```bash
uv sync
uv run pytest
```

The initial smoke test is intentionally independent of PostgreSQL, Redis, network access, and credentials.

Local PostgreSQL and Redis setup is documented in
[`_docs/local-development.md`](_docs/local-development.md).

Run the Django development server with:

```bash
uv run python manage.py runserver
```

The deterministic health page is available at `/health`.

Run the analytical service with:

```bash
uv run uvicorn api.main:app --reload
```

It exposes the same deterministic health contract at `/health` and publishes
versioned OpenAPI metadata.
