import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Settings = {
  provider_mode: string
  ollama_base_url: string
  ollama_model: string
}

type CaseItem = {
  id: number
  title: string
  description: string | null
}

type DocumentItem = {
  id: number
  filename: string
  extension: string
  status: string
  text_length: number
}

type JobItem = {
  id: number
  status: string
  progress: number
  current_step: string | null
  error_message: string | null
  running_summary: string | null
  final_summary: string | null
}

type CaseDetail = CaseItem & {
  documents: DocumentItem[]
  jobs: JobItem[]
  running_summary: string | null
  final_summary: string | null
}

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api'

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

function App() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [cases, setCases] = useState<CaseItem[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const [selectedFileName, setSelectedFileName] = useState('')
  const [processing, setProcessing] = useState(false)
  const [providerTest, setProviderTest] = useState<string>('')
  const [error, setError] = useState<string>('')
  const activeJob = useMemo(() => caseDetail?.jobs[0] ?? null, [caseDetail])

  useEffect(() => {
    void Promise.all([loadSettings(), loadCases()])
  }, [])

  useEffect(() => {
    if (selectedCaseId === null) {
      setCaseDetail(null)
      return
    }
    void loadCaseDetail(selectedCaseId)
  }, [selectedCaseId])

  useEffect(() => {
    if (!activeJob || !['queued', 'running'].includes(activeJob.status)) {
      return
    }

    const timer = window.setInterval(() => {
      void loadCaseDetail(selectedCaseId ?? activeJob.id)
    }, 1500)

    return () => window.clearInterval(timer)
  }, [activeJob, selectedCaseId])

  async function loadSettings() {
    const payload = await api<Settings>('/settings')
    setSettings(payload)
  }

  async function loadCases() {
    const payload = await api<CaseItem[]>('/cases')
    setCases(payload)
    if (!selectedCaseId && payload.length > 0) {
      setSelectedCaseId(payload[0].id)
    }
  }

  async function loadCaseDetail(caseId: number) {
    const payload = await api<CaseDetail>(`/cases/${caseId}`)
    setCaseDetail(payload)
  }

  async function handleCreateCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const created = await api<CaseItem>('/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description }),
    })
    setTitle('')
    setDescription('')
    await loadCases()
    setSelectedCaseId(created.id)
  }

  async function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!settings) return
    setError('')
    const updated = await api<Settings>('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    })
    setSettings(updated)
  }

  async function handleTestProvider() {
    if (!settings) return
    setProviderTest('Testing...')
    try {
      const result = await api<{ ok: boolean; message: string }>('/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ override_settings: settings }),
      })
      setProviderTest(result.message)
    } catch (requestError) {
      setProviderTest(requestError instanceof Error ? requestError.message : 'Provider test failed')
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedCaseId) return

    const fileInput = event.currentTarget.elements.namedItem('document') as HTMLInputElement | null
    const file = fileInput?.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api(`/cases/${selectedCaseId}/documents`, { method: 'POST', body: formData })
      event.currentTarget.reset()
      setSelectedFileName('')
      await loadCaseDetail(selectedCaseId)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleProcess() {
    if (!selectedCaseId || !settings) return
    setProcessing(true)
    setError('')
    try {
      await api(`/cases/${selectedCaseId}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_mode: settings.provider_mode }),
      })
      await loadCaseDetail(selectedCaseId)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Processing failed')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <main className="shell">
      <section className="panel hero">
        <div>
          <p className="eyebrow">Chart Digest Prototype</p>
          <h1>Local-first chronology summarization with Ollama</h1>
          <p className="lede">
            Create a case, ingest text or text-based PDF records, process them in order, and watch the running digest
            update as chunks complete.
          </p>
        </div>
        <div className="status-card">
          <span>Health target</span>
          <strong>{API_BASE}/health</strong>
          <span>Provider mode</span>
          <strong>{settings?.provider_mode ?? 'loading'}</strong>
        </div>
      </section>

      <section className="grid">
        <div className="panel">
          <h2>Settings</h2>
          {settings ? (
            <form className="stack" onSubmit={handleSaveSettings}>
              <label>
                Provider mode
                <select
                  value={settings.provider_mode}
                  onChange={(event) => setSettings({ ...settings, provider_mode: event.target.value })}
                >
                  <option value="ollama">Ollama (local)</option>
                </select>
              </label>
              <label>
                Ollama base URL
                <input
                  value={settings.ollama_base_url}
                  onChange={(event) => setSettings({ ...settings, ollama_base_url: event.target.value })}
                />
              </label>
              <label>
                Model
                <input
                  value={settings.ollama_model}
                  onChange={(event) => setSettings({ ...settings, ollama_model: event.target.value })}
                />
              </label>
              <div className="actions">
                <button type="submit">Save settings</button>
                <button type="button" className="secondary" onClick={handleTestProvider}>
                  Test connection
                </button>
              </div>
              {providerTest ? <p className="hint">{providerTest}</p> : null}
            </form>
          ) : (
            <p>Loading settings...</p>
          )}
        </div>

        <div className="panel">
          <h2>Create case</h2>
          <form className="stack" onSubmit={handleCreateCase}>
            <label>
              Title
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="ER timeline review" />
            </label>
            <label>
              Description
              <textarea
                rows={4}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Optional context for the digest"
              />
            </label>
            <button type="submit" disabled={!title.trim()}>
              Create case
            </button>
          </form>
        </div>
      </section>

      <section className="grid">
        <div className="panel">
          <h2>Cases</h2>
          <div className="case-list">
            {cases.map((item) => (
              <button
                key={item.id}
                className={item.id === selectedCaseId ? 'case-button active' : 'case-button'}
                onClick={() => setSelectedCaseId(item.id)}
              >
                <strong>{item.title}</strong>
                <span>{item.description ?? 'No description'}</span>
              </button>
            ))}
            {cases.length === 0 ? <p>No cases yet.</p> : null}
          </div>
        </div>

        <div className="panel">
          <h2>Documents</h2>
          <form className="stack" onSubmit={handleUpload}>
            <div className="file-picker-card">
              <p className="hint">Choose local chart file (.txt, .md, .pdf)</p>
              <label className="file-picker-label" htmlFor="document-input">
                <span>{selectedFileName || 'Select local chart file'}</span>
              </label>
              <input
                id="document-input"
                name="document"
                type="file"
                accept=".txt,.md,.pdf"
                onChange={(event) => setSelectedFileName(event.target.files?.[0]?.name ?? '')}
              />
            </div>
            <button type="submit" disabled={!selectedCaseId || uploading || !selectedFileName}>
              {uploading ? 'Uploading...' : 'Upload selected file'}
            </button>
          </form>
          {!selectedCaseId ? <p className="hint">Create/select a case to enable upload.</p> : null}
          <div className="doc-list">
            {caseDetail?.documents.map((document) => (
              <article key={document.id} className="doc-item">
                <strong>{document.filename}</strong>
                <span>
                  {document.extension} · {document.text_length} chars
                </span>
              </article>
            ))}
            {selectedCaseId && caseDetail?.documents.length === 0 ? <p>No documents uploaded.</p> : null}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="toolbar">
          <div>
            <h2>Processing</h2>
            <p className="hint">Jobs run in the background and update the running digest after each chunk.</p>
          </div>
          <button onClick={handleProcess} disabled={!selectedCaseId || processing || !caseDetail?.documents.length}>
            {processing ? 'Starting...' : 'Start processing'}
          </button>
        </div>
        {activeJob ? (
          <div className="job-card">
            <div className="job-meta">
              <span>Status: {activeJob.status}</span>
              <span>Progress: {activeJob.progress}%</span>
              <span>{activeJob.current_step ?? 'Idle'}</span>
            </div>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${activeJob.progress}%` }} />
            </div>
            {activeJob.error_message ? <p className="error">{activeJob.error_message}</p> : null}
          </div>
        ) : (
          <p>No jobs yet.</p>
        )}
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="grid">
        <div className="panel">
          <h2>Running summary</h2>
          <pre>{activeJob?.running_summary ?? caseDetail?.running_summary ?? 'No running summary yet.'}</pre>
        </div>
        <div className="panel">
          <h2>Final summary</h2>
          <pre>{activeJob?.final_summary ?? caseDetail?.final_summary ?? 'No final summary yet.'}</pre>
        </div>
      </section>
    </main>
  )
}

export default App
