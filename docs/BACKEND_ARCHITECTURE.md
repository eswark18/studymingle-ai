# StudyMingle backend foundation

## Scope

This phase introduces a portable Python backend without changing the production frontend.

- FastAPI application packaged as a Docker image
- PostgreSQL 16 for local development
- SQLAlchemy async database access
- Alembic schema migrations
- Initial `users` and `sessions` tables
- Health and database-readiness endpoints
- Test and lint configuration

OCR, AI tutoring, authentication delivery, Turnstile, and R2 uploads are intentionally deferred.

## Local services

| Service | Address | Purpose |
| --- | --- | --- |
| FastAPI | `http://localhost:8000` | Backend API |
| OpenAPI | `http://localhost:8000/docs` | Development API documentation |
| Health | `http://localhost:8000/health` | Process health |
| Readiness | `http://localhost:8000/ready` | PostgreSQL connectivity |
| PostgreSQL | `localhost:5432` | Local durable database |

## Commands

```bash
docker compose up --build
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker compose down
```

Use `docker compose down -v` only when intentionally deleting the local database volume.

## Production direction

The backend image is designed to run on a standard container platform, including Cloudflare
Containers. Production data must use managed PostgreSQL, and uploaded worksheets must use a
private R2 bucket rather than the container filesystem.

Secrets such as database credentials, Turnstile keys, mail-provider keys, and AI-provider keys
must be injected by the hosting platform and must never be committed.
