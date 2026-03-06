# Chart Digest

Local-first prototype for chronology-aware case summarization using FastAPI, React, SQLite, the local filesystem, and Ollama.

## Implemented in this pass

- Work Orders 1-3: monorepo scaffold, backend/frontend setup, SQLite models, Alembic migration, and ingestion for `.txt`, `.md`, and text-based `.pdf`.
- Minimal runnable backbone for Work Orders 4-8: chronology-aware chunking, provider abstraction, working Ollama adapter, provider connection test, background job processing, polling, and a frontend flow for case creation, upload, process start, and live summary viewing.
- Tests for chunking, Ollama adapter behavior, and the happy-path processing pipeline.

## Project layout

- `backend/`: FastAPI API, SQLAlchemy models, Alembic migration, ingestion and processing services, tests.
- `frontend/`: Vite + React + TypeScript UI.
- `data/`: runtime SQLite DB plus uploaded/extracted files. Created automatically.

## Local run

### 1. Start Ollama

Make sure Ollama is running locally or on your LAN and that the chosen model is available.

Example:

```bash
ollama serve
ollama pull llama3.1:8b
```

If Ollama is on another machine, use its reachable base URL in the app settings, for example `http://192.168.1.50:11434`.

### 2. Install backend dependencies

```bash
cd /home/daniel/VibeProjects/ChartDigest
python3 -m venv .venv
.venv/bin/pip install -e 'backend[dev]'
```

### 3. Install frontend dependencies

```bash
cd /home/daniel/VibeProjects/ChartDigest/frontend
npm install
```

### 4. Run backend

```bash
cd /home/daniel/VibeProjects/ChartDigest
.venv/bin/uvicorn app.main:app --app-dir backend --reload
```

Backend URLs:

- API root: `http://127.0.0.1:8000/api`
- Health: `http://127.0.0.1:8000/health`

### 5. Run frontend

```bash
cd /home/daniel/VibeProjects/ChartDigest/frontend
cp .env.example .env
npm run dev
```

Frontend URL:

- `http://127.0.0.1:5173`

## Usage flow

1. Open the frontend.
2. In Settings, confirm `Ollama base URL` and `Model`.
3. Click `Test connection`.
4. Create a case.
5. Upload a `.txt`, `.md`, or text-based `.pdf`.
6. Start processing.
7. Polling updates the job state, running summary, and final summary.

## Test commands

```bash
cd /home/daniel/VibeProjects/ChartDigest
.venv/bin/pytest backend/app/tests
cd frontend
npm run build
```

## Troubleshooting

- Provider test fails:
  Verify Ollama is running and the base URL is reachable from this machine. Check `curl http://HOST:11434/api/tags`.
- Model errors:
  Pull the configured model first with `ollama pull <model>`.
- PDF uploads fail:
  This prototype only supports text-based PDFs. Scanned/image PDFs need OCR, which is not included in this pass.
- Summaries are slow:
  Smaller local models or remote LAN Ollama hosts can change latency significantly.
- Existing DB schema mismatch after pulling changes:
  Remove `data/chart_digest.db` for a fresh local prototype reset.

## Notes on architecture

- Provider selection is routed through a provider factory and `ProviderConfig`, so cloud adapters can be added without replacing the job pipeline.
- Job execution is intentionally lightweight and in-process for this prototype. A durable worker/queue is still a v1 hardening item.
