# StudyMingle AI

StudyMingle is a guided multimodal learning workspace for **Grades 6–12** and **engineering students**. It is designed to strengthen a learner’s reasoning through progressive hints, visual explanations, answer feedback, and practice—not simply generate finished homework.

## Current scope

- School and engineering learning tracks
- Grade/year and subject selection
- Account-owned PDF and image uploads with deletion controls
- Native PDF extraction and Tesseract OCR
- Reviewable extracted questions with immutable OCR source text
- PostgreSQL-backed tutor sessions, attempts, and hints
- Self-hosted open-source tutoring through Ollama
- Structured, age-aware progressive guidance and attempt feedback
- Educational force/vector diagram
- Responsive and keyboard-accessible interface
- Reduced-motion support

Local development uses PostgreSQL, MinIO, and Ollama through Docker Compose. Model inference and all credentials stay server-side.

## Learning principles

1. Ask for an attempt before revealing a solution.
2. Provide progressive hints rather than an immediate finished answer.
3. Explain why an answer works or fails.
4. Reinforce learning with a related practice question.
5. Clearly communicate uncertainty and prototype limitations.

## Run locally

### Prerequisites

Install the following before starting:

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose
- [Node.js](https://nodejs.org/) 20 or newer

Docker should have enough free memory to run PostgreSQL, MinIO, the FastAPI backend, and the local Ollama model.

### 1. Clone the repository

```bash
git clone https://github.com/eswark18/studymingle-ai.git
cd studymingle-ai
```

### 2. Start the backend services

```bash
docker compose up --build -d
```

This starts:

- FastAPI at `http://localhost:8000`
- PostgreSQL at `localhost:5432`
- MinIO API at `http://localhost:9000`
- MinIO console at `http://localhost:9001`
- Ollama at `http://localhost:11434`

The API container applies the Alembic database migrations automatically when it starts.

Check that all containers are running:

```bash
docker compose ps
```

Check the backend:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### 3. Download the local tutor model

Run this once after the Ollama container starts:

```bash
docker compose exec ollama ollama pull qwen3:4b
```

The model is stored in a Docker volume, so it does not need to be downloaded every time.

Confirm that it is available:

```bash
docker compose exec ollama ollama list
```

### 4. Install and start the frontend

Open another terminal in the repository root:

```bash
npm install
npm run dev
```

Open `http://localhost:5173` in a browser. Register a local account, upload a PDF, PNG, or JPEG worksheet, review the extracted questions, and start the guided tutor flow.

Turnstile is not required in the default development environment.

## Try the included sample worksheet

Download [StudyMingle Sample Worksheet](docs/samples/studymingle-sample-worksheet.pdf) and upload it from the learning workspace. The one-page PDF contains five clean Engineering Mechanics questions:

1. Resolve a 10 N force acting 30 degrees above the horizontal into horizontal and vertical components.
2. Find the magnitude and direction of the resultant of perpendicular 6 N and 8 N forces.
3. Calculate the weight and normal reaction of a 20 kg box using `g = 9.81 m/s^2`.
4. Calculate acceleration and distance when velocity changes from 5 m/s to 25 m/s in 10 seconds.
5. Determine the two support reactions for a simply supported beam with a central 12 kN load.

Recommended test flow:

1. Create a local account and upload the sample PDF.
2. Wait for OCR, confirm that five questions were extracted, and edit any OCR text if necessary.
3. Select Question 1 and start the Study Coach.
4. Submit an attempt such as `Fx = 8 N and Fy = 6 N` to test corrective feedback.
5. Reveal progressive hints, or enter `solve it` to test the complete numbered explanation.
6. Confirm that the final response uses readable plain-text mathematics, including `Fx = 10 × cos(30°) = 8.66 N` and `Fy = 10 × sin(30°) = 5 N`.

### 5. View logs or stop the application

Follow backend logs:

```bash
docker compose logs -f api
```

Stop the frontend with `Ctrl+C`. Stop the Docker services while keeping their data:

```bash
docker compose down
```

To also delete the local database, worksheet files, and downloaded Ollama model, run:

```bash
docker compose down -v
```

> Warning: `docker compose down -v` permanently removes all StudyMingle development data stored in Docker volumes.

### Troubleshooting

If the API is not ready, inspect its logs:

```bash
docker compose logs api
```

If tutor requests fail, confirm that Ollama is running and the model exists:

```bash
docker compose ps ollama
docker compose exec ollama ollama list
```

If a port is already in use, stop the conflicting local service or change the corresponding host port in `compose.yaml`.

## Validate

Frontend checks:

```bash
npm run lint
npm run build
```

Backend checks:

```bash
docker compose exec api ruff check .
docker compose exec api pytest -q
```

## Planned phases

1. UX prototype
2. Secure worksheet upload and OCR/question extraction
3. Guided tutoring chat
4. Answer checking and practice generation
5. Educational diagram generation
6. Privacy, safety, evaluations, and usage controls
7. Public demo at `study.thoughtmingle.com`

## Technology

- React
- TypeScript
- Vite
- FastAPI and PostgreSQL
- S3-compatible private storage
- Ollama with a configurable open-source model
- Cloudflare Pages frontend

StudyMingle is a ThoughtMingle learning prototype.

## Branch and demonstration strategy

- `main` is the canonical open-source development branch. Developers clone this branch and run the complete React, FastAPI, PostgreSQL, MinIO, Ollama, and OCR stack locally.
- `production` is the Cloudflare Pages deployment branch. It remains a complete repository snapshot so changes from `main` can be merged safely, but Cloudflare builds only the Vite frontend and Pages Functions.
- Local development does not use the production availability gate. Setting `VITE_DEPLOYMENT_MODE=production` enables the gate for the public site.

The public frontend checks `VITE_API_BASE_URL/health` when it loads. If the locally hosted API and Cloudflare Tunnel are available, the complete workspace opens. If the API is offline or does not respond within eight seconds, visitors see a maintenance page and can request a scheduled private demonstration.

### Cloudflare Pages production settings

Configure the Pages project to deploy the `production` branch with:

```text
Build command: npm run build
Build output directory: dist
Root directory: /
```

Copy the values described in `.env.production.example` into the Cloudflare Pages production environment. Store `TURNSTILE_SECRET_KEY` and `RESEND_API_KEY` as encrypted secrets. `VITE_API_BASE_URL` should point to the named Cloudflare Tunnel hostname connected to the MacBook API, such as `https://api.study.thoughtmingle.com`.

The demo request form is a Cloudflare Pages Function and therefore remains available while the MacBook is offline. It verifies Turnstile and sends the request through Resend. Verify `thoughtmingle.com` in Resend before using `demo@thoughtmingle.com` as the sender.

### Start a scheduled demonstration

1. Connect the MacBook to power and prevent it from sleeping.
2. Start the complete local stack:

   ```bash
   docker compose up --build -d
   docker compose exec ollama ollama list
   ```

3. Confirm the backend is ready:

   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```

4. Start the named Cloudflare Tunnel that maps the public API hostname to `http://localhost:8000`.
5. Open `https://study.thoughtmingle.com` and confirm that the full workspace appears.
6. At the end of the session, stop the tunnel and run `docker compose down`. Cloudflare Pages will automatically return visitors to the maintenance and demo-request experience.

For the first release, scheduled access is coordinated by email. Temporary access codes, automatic expiry, session capacity, and payment-provider integration remain planned production controls; they are not represented as completed security features.
