# AI

A minimal full-stack **AI chat demo** used to validate the Cloud Agent development environment end to end. The assistant is fully offline and deterministic — no API keys, no network egress required.

## Stack

- **Backend:** Node.js + [Express](https://expressjs.com/) (`src/server.js`)
- **AI engine:** deterministic, rule-based responder (`src/aiEngine.js`)
- **Frontend:** static modern chat UI (`public/`)
- **Tests:** Node's built-in test runner + [supertest](https://github.com/ladjs/supertest)
- **Lint:** ESLint (flat config)

## Requirements

- Node.js >= 20 (developed against Node 22)

## Getting started

```bash
npm ci        # install dependencies
npm run dev   # start the dev server with file watching
# or
npm start     # start the server
```

Then open http://localhost:3000 and send a message. Try:

- `reverse hello world`
- `count words in this sentence`
- `hello`

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the server with `--watch` auto-reload |
| `npm start` | Start the server |
| `npm test` | Run the automated test suite |
| `npm run lint` | Lint the codebase with ESLint |

## API

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/api/health` | – | `{ "status": "ok", "uptime": <seconds> }` |
| `POST` | `/api/chat` | `{ "message": "..." }` | `{ "reply": "...", "tokens": <n> }` |

## Cloud Agent environment

The development environment is described in `.cursor/environment.json`: it installs
dependencies with `npm ci` and runs the dev server in a `server` terminal on port 3000.
