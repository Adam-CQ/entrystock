# Local infrastructure

Copy `.env.example` to `.env` and replace the local placeholder credentials.
The `.env` file is local configuration and must not be committed.

Start PostgreSQL and Redis in the background:

```bash
docker compose up -d
```

Check service status and health:

```bash
docker compose ps
docker compose logs postgres redis
```

Stop the services while retaining their named volumes:

```bash
docker compose stop
```

The application connection settings are `DATABASE_URL` for PostgreSQL and
`REDIS_URL` for Redis. The Compose services are named `postgres` and `redis`;
inside the Compose network, their default ports are `5432` and `6379`.

Celery uses `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`; both default to
`REDIS_URL` and may be set independently when required. For a local worker,
run `uv run celery -A config.celery worker --loglevel=INFO`. Analysis submission
returns a broker task handle immediately; the persisted `AnalysisRun` status
progresses from `created` to `queued`, `running`, and then `succeeded`,
`partially_evaluable`, or `failed`. Re-delivery of a terminal run is idempotent.

The PostgreSQL data is stored in `postgres_data` and Redis data in
`redis_data`, so ordinary restarts preserve local development data.
