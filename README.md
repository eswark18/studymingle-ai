# StudyMingle AI

StudyMingle is a guided multimodal learning workspace for **Grades 6–12** and **engineering students**. It is designed to strengthen a learner’s reasoning through progressive hints, visual explanations, answer feedback, and practice—not simply generate finished homework.

## Prototype scope

The `feature/mvp-prototype` branch contains a frontend-only interactive prototype:

- School and engineering learning tracks
- Grade/year and subject selection
- PDF and image worksheet selection with local-only preview state
- Mock question extraction
- Guided tutoring flow with progressive hints
- Student answer feedback
- Educational force/vector diagram
- Responsive and keyboard-accessible interface
- Reduced-motion support

No uploaded files leave the browser. The prototype has no accounts, database, permanent storage, payments, or AI API integration.

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
- Cloudflare Pages (planned hosting)

StudyMingle is a ThoughtMingle learning prototype.
