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

The PostgreSQL data is stored in `postgres_data` and Redis data in
`redis_data`, so ordinary restarts preserve local development data.
