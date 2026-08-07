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

Local development uses PostgreSQL, MinIO, and Ollama through Docker Compose. Model inference and
all credentials stay server-side.

## Learning principles

1. Ask for an attempt before revealing a solution.
2. Provide progressive hints rather than an immediate finished answer.
3. Explain why an answer works or fails.
4. Reinforce learning with a related practice question.
5. Clearly communicate uncertainty and prototype limitations.

## Run locally

```bash
npm install
npm run dev
docker compose up --build
docker compose exec ollama ollama pull qwen3:4b
```

## Validate

```bash
npm run lint
npm run build
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
