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

### Single-launch helper (starts backend + frontend)

```bash
cd /home/daniel/VibeProjects/ChartDigest
./scripts/launch_local.sh
```

By default this uses backend `:8010` (to avoid conflicts) and frontend `:5173`.
Override if needed:

```bash
CHARTDIGEST_BACKEND_PORT=8000 CHARTDIGEST_FRONTEND_PORT=5174 ./scripts/launch_local.sh
```

Stop both:

```bash
./scripts/stop_local.sh
```

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
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8010 --reload
```

Backend URLs:

- API root: `http://127.0.0.1:8010/api`
- Health: `http://127.0.0.1:8010/health`

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

- Create Case does nothing or the list does not update:
  Check the dev-only `Diagnostics` panel in the UI. `Active API base` must match the backend you actually started, for example `http://127.0.0.1:8010/api`. The frontend now refuses to silently fall back to `:8000`; if `VITE_API_BASE` is missing or wrong, the app shows an inline configuration error instead of failing quietly.
- Backend and frontend are running, but the wrong server still answers:
  This machine may already have another app listening on `127.0.0.1:8000`. Use the provided helper or set `VITE_API_BASE` explicitly so the frontend points at the intended Chart Digest backend.
- `launch_local.sh` says the frontend is already running, but the expected port is not serving:
  The helper now ignores empty/invalid PID files, but older stale runtime files can still exist from prior sessions. Stop local services and relaunch so the frontend binds the strict port again.
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
