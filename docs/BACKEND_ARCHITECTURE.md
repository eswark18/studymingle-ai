# StudyMingle backend foundation

## Scope

This phase introduces a portable Python backend without changing the production frontend.

- FastAPI application packaged as a Docker image
- PostgreSQL 16 for local development
- SQLAlchemy async database access
- Alembic schema migrations
- Initial `users` and `sessions` tables
- Registration, sign-in, sign-out, current-user, and account-deletion APIs
- Argon2 password hashing and opaque server-side sessions
- Optional Turnstile verification in development; required in production
- Authenticated private worksheet uploads with ownership metadata
- S3-compatible object storage using MinIO locally and Cloudflare R2 in production
- Native PDF text extraction with Tesseract OCR fallback for scanned PDFs and images
- Persistent OCR job state and editable, account-owned extracted questions
- Persistent tutor sessions, attempts, and progressive hints
- A server-side provider interface backed by self-hosted Ollama
- Validated structured model responses, timeouts, and per-user request limits
- Health and database-readiness endpoints
- Test and lint configuration

Email verification, password recovery, production R2 wiring, and distributed rate limiting are
intentionally deferred.

## Authentication endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `DELETE /api/v1/auth/account`

Authentication uses an HTTP-only session cookie. Only a SHA-256 digest of the random session
token is stored. Account deletion anonymizes personal profile fields and revokes active sessions.

## Worksheet endpoints

- `POST /api/v1/worksheets` accepts one PDF, PNG, or JPEG up to 10 MB
- `GET /api/v1/worksheets` lists the authenticated user's active worksheets
- `GET /api/v1/worksheets/{id}/download` creates a five-minute private download URL
- `DELETE /api/v1/worksheets/{id}` removes both the object and its ownership record

File extensions are never trusted. The API validates magic bytes, computes a SHA-256 digest,
uses an opaque storage key, and never exposes another user's worksheet metadata.

## OCR endpoints

- `POST /api/v1/worksheets/{id}/extract` queues extraction for an owned worksheet
- `GET /api/v1/ocr-jobs/{id}` returns extraction status and reviewable questions
- `POST /api/v1/ocr-jobs/{id}/retry` retries a failed extraction
- `PATCH /api/v1/questions/{id}` saves the learner's corrected question text

The extractor first reads embedded PDF text. PDFs without useful embedded text are rendered with
Poppler and processed with Tesseract; PNG and JPEG files use Tesseract directly. PostgreSQL stores
job state and question text, while the original private file remains in S3-compatible object
storage. The configured page limit protects CPU and memory usage.

FastAPI background tasks execute OCR in the current single-container milestone. The job boundary is
deliberately persisted so the executor can move to Cloudflare Queues or another durable worker
without changing the browser API. Until that replacement, a container restart can interrupt an
in-flight job; the failed/stale-job recovery policy must be added before production scale-out.

## Tutor endpoints

- `POST /api/v1/questions/{id}/tutor-sessions` starts guidance for an owned question
- `GET /api/v1/tutor-sessions/{id}` restores the learner's tutor history
- `POST /api/v1/tutor-sessions/{id}/hints` requests one progressive hint
- `POST /api/v1/tutor-sessions/{id}/attempts` checks and stores the learner's reasoning

The tutor uses the reviewed question text while preserving `extracted_text` as immutable OCR
evidence. The browser never calls a model directly. FastAPI sends age-, track-, and subject-aware
prompts to a self-hosted Ollama API and validates every response against a Pydantic JSON schema
before it is stored or returned. The teaching policy allows at most three progressively specific
hints and avoids a completed answer before a meaningful learner attempt.

`TutorProvider` is deliberately provider-neutral. The current implementation is open-source
Ollama; a later vLLM or Hugging Face implementation can satisfy the same interface without changing
the browser API or database model. The in-memory limiter protects this single API process; use a
shared Redis-backed limiter before horizontally scaling the service.

## Local services

| Service | Address | Purpose |
| --- | --- | --- |
| FastAPI | `http://localhost:8000` | Backend API |
| OpenAPI | `http://localhost:8000/docs` | Development API documentation |
| Health | `http://localhost:8000/health` | Process health |
| Readiness | `http://localhost:8000/ready` | PostgreSQL connectivity |
| PostgreSQL | `localhost:5432` | Local durable database |
| MinIO API | `localhost:9000` | Local private object storage |
| MinIO console | `localhost:9001` | Local storage administration |
| Ollama | `localhost:11434` | Local open-source tutor inference |

## Commands

```bash
docker compose up --build
docker compose exec ollama ollama pull qwen3:4b
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
