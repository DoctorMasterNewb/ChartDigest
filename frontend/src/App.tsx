import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { ApiRequestError, api, buildApiUrl, buildHealthUrl, resolveApiConfig } from './api'

type Settings = {
  provider_mode: string
  ollama_base_url: string
  ollama_model: string
}

type CaseItem = {
  id: number
  title: string
  description: string | null
  created_at: string
  updated_at: string
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

type FeedbackTone = 'success' | 'error' | 'info'

type FeedbackState = {
  tone: FeedbackTone
  message: string
} | null

type RequestState = {
  status: 'idle' | 'pending' | 'success' | 'error'
  message: string
  url: string
  httpStatus: number | null
}

function App() {
  const apiConfig = useMemo(() => resolveApiConfig(import.meta.env.VITE_API_BASE), [])
  const apiBase = apiConfig.apiBase
  const [settings, setSettings] = useState<Settings | null>(null)
  const [cases, setCases] = useState<CaseItem[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null)
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState<number | null>(null)
  const [selectedFileName, setSelectedFileName] = useState('')
  const [processing, setProcessing] = useState(false)
  const [creatingCase, setCreatingCase] = useState(false)
  const [providerTest, setProviderTest] = useState<string>('')
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelsError, setModelsError] = useState('')
  const [error, setError] = useState<string>('')
  const [createCaseFeedback, setCreateCaseFeedback] = useState<FeedbackState>(null)
  const [lastCreateCaseRequest, setLastCreateCaseRequest] = useState<RequestState>({
    status: apiBase ? 'idle' : 'error',
    message: apiConfig.configError ?? 'No request sent yet.',
    url: apiBase ? buildApiUrl(apiBase, '/cases') : 'not configured',
    httpStatus: null,
  })
  const activeJob = useMemo(() => caseDetail?.jobs[0] ?? null, [caseDetail])

  useEffect(() => {
    if (!apiBase) {
      setError(apiConfig.configError ?? 'Frontend API is not configured.')
      return
    }

    const currentApiBase = apiBase

    async function initialize() {
      try {
        await Promise.all([loadSettings(currentApiBase), loadCases(currentApiBase), loadOllamaModels(currentApiBase)])
      } catch (requestError) {
        setError(getErrorMessage(requestError, 'Failed to load initial app data'))
      }
    }

    void initialize()
  }, [apiBase, apiConfig.configError])

  useEffect(() => {
    if (!apiBase || selectedCaseId === null) {
      setCaseDetail(null)
      return
    }
    void loadCaseDetail(apiBase, selectedCaseId).catch((requestError) => {
      setError(getErrorMessage(requestError, 'Failed to load case detail'))
    })
  }, [apiBase, selectedCaseId])

  useEffect(() => {
    if (!apiBase || !activeJob || !['queued', 'running'].includes(activeJob.status)) {
      return
    }

    const timer = window.setInterval(() => {
      void loadCaseDetail(apiBase, selectedCaseId ?? activeJob.id).catch((requestError) => {
        setError(getErrorMessage(requestError, 'Failed to refresh job status'))
      })
    }, 1500)

    return () => window.clearInterval(timer)
  }, [activeJob, apiBase, selectedCaseId])

  async function loadSettings(currentApiBase: string) {
    const { data } = await api<Settings>(currentApiBase, '/settings')
    setSettings(data)
  }

  async function loadOllamaModels(currentApiBase: string) {
    setModelsLoading(true)
    setModelsError('')
    try {
      const { data } = await api<string[]>(currentApiBase, '/providers/ollama/models')
      setOllamaModels(data)
    } catch (requestError) {
      setModelsError(getErrorMessage(requestError, 'Unable to load Ollama models'))
      setOllamaModels([])
    } finally {
      setModelsLoading(false)
    }
  }

  async function loadCases(currentApiBase: string, preferredCaseId?: number) {
    const { data } = await api<CaseItem[]>(currentApiBase, '/cases')
    setCases(data)
    setSelectedCaseId((currentSelectedCaseId) => {
      if (preferredCaseId && data.some((item) => item.id === preferredCaseId)) {
        return preferredCaseId
      }
      if (currentSelectedCaseId && data.some((item) => item.id === currentSelectedCaseId)) {
        return currentSelectedCaseId
      }
      return data[0]?.id ?? null
    })
    return data
  }

  async function loadCaseDetail(currentApiBase: string, caseId: number) {
    const { data } = await api<CaseDetail>(currentApiBase, `/cases/${caseId}`)
    setCaseDetail(data)
    return data
  }

  async function handleCreateCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!apiBase) {
      const message = apiConfig.configError ?? 'Frontend API is not configured.'
      setCreateCaseFeedback({ tone: 'error', message })
      setLastCreateCaseRequest({
        status: 'error',
        message,
        url: 'not configured',
        httpStatus: null,
      })
      return
    }

    const trimmedTitle = title.trim()
    const trimmedDescription = description.trim()
    if (!trimmedTitle) {
      return
    }

    setError('')
    setCreateCaseFeedback({ tone: 'info', message: 'Creating case...' })
    setCreatingCase(true)
    setLastCreateCaseRequest({
      status: 'pending',
      message: 'Submitting create case request.',
      url: buildApiUrl(apiBase, '/cases'),
      httpStatus: null,
    })

    try {
      const { data: created, status, url } = await api<CaseItem>(apiBase, '/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: trimmedTitle, description: trimmedDescription || null }),
      })

      setCases((currentCases) => [created, ...currentCases.filter((item) => item.id !== created.id)])
      setSelectedCaseId(created.id)
      setCaseDetail({
        ...created,
        documents: [],
        jobs: [],
        running_summary: null,
        final_summary: null,
      })
      setTitle('')
      setDescription('')
      setCreateCaseFeedback({ tone: 'success', message: `Created case "${created.title}".` })
      setLastCreateCaseRequest({
        status: 'success',
        message: 'Create case request succeeded.',
        url,
        httpStatus: status,
      })

      await Promise.all([loadCases(apiBase, created.id), loadCaseDetail(apiBase, created.id)])
    } catch (requestError) {
      const message = getErrorMessage(requestError, 'Create case failed')
      setCreateCaseFeedback({ tone: 'error', message })
      setLastCreateCaseRequest({
        status: 'error',
        message,
        url: buildApiUrl(apiBase, '/cases'),
        httpStatus: requestError instanceof ApiRequestError ? requestError.status : null,
      })
    } finally {
      setCreatingCase(false)
    }
  }

  async function handleSaveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!apiBase || !settings) return
    setError('')
    try {
      const { data } = await api<Settings>(apiBase, '/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      setSettings(data)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Saving settings failed'))
    }
  }

  async function handleTestProvider() {
    if (!apiBase || !settings) return
    setProviderTest('Testing...')
    try {
      const { data } = await api<{ ok: boolean; message: string }>(apiBase, '/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ override_settings: settings }),
      })
      setProviderTest(data.message)
    } catch (requestError) {
      setProviderTest(getErrorMessage(requestError, 'Provider test failed'))
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!apiBase || !selectedCaseId) return

    const formEl = event.currentTarget
    const fileInput = formEl.elements.namedItem('document') as HTMLInputElement | null
    const file = fileInput?.files?.[0]
    if (!file) return

    setUploading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api(apiBase, `/cases/${selectedCaseId}/documents`, { method: 'POST', body: formData })
      formEl.reset()
      setSelectedFileName('')
      await loadCaseDetail(apiBase, selectedCaseId)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Upload failed'))
    } finally {
      setUploading(false)
    }
  }

  async function handleDeleteDocument(documentId: number) {
    if (!apiBase || !selectedCaseId) return
    setError('')
    setDeletingDocumentId(documentId)
    try {
      await api(apiBase, `/cases/${selectedCaseId}/documents/${documentId}`, { method: 'DELETE' })
      await loadCaseDetail(apiBase, selectedCaseId)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Delete failed'))
    } finally {
      setDeletingDocumentId(null)
    }
  }

  async function handleProcess() {
    if (!apiBase || !selectedCaseId || !settings) return
    setProcessing(true)
    setError('')
    try {
      await api(apiBase, `/cases/${selectedCaseId}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_mode: settings.provider_mode }),
      })
      await loadCaseDetail(apiBase, selectedCaseId)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Processing failed'))
    } finally {
      setProcessing(false)
    }
  }

  const createCaseStatusClassName =
    createCaseFeedback?.tone === 'success'
      ? 'feedback success'
      : createCaseFeedback?.tone === 'error'
        ? 'feedback error'
        : 'feedback info'

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
          <strong>{apiBase ? buildHealthUrl(apiBase) : 'not configured'}</strong>
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
                <select
                  value={settings.ollama_model}
                  onChange={(event) => setSettings({ ...settings, ollama_model: event.target.value })}
                >
                  {ollamaModels.map((modelName) => (
                    <option key={modelName} value={modelName}>
                      {modelName}
                    </option>
                  ))}
                  {!ollamaModels.includes(settings.ollama_model) ? (
                    <option value={settings.ollama_model}>{settings.ollama_model} (current)</option>
                  ) : null}
                </select>
              </label>
              <div className="actions">
                <button type="submit">Save settings</button>
                <button type="button" className="secondary" onClick={handleTestProvider}>
                  Test connection
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => apiBase && void loadOllamaModels(apiBase)}
                  disabled={modelsLoading}
                >
                  {modelsLoading ? 'Refreshing models...' : 'Refresh models'}
                </button>
              </div>
              {modelsError ? <p className="error">{modelsError}</p> : null}
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
            <button type="submit" disabled={!title.trim() || creatingCase || !apiBase}>
              {creatingCase ? 'Creating...' : 'Create case'}
            </button>
            {createCaseFeedback ? (
              <p className={createCaseStatusClassName} aria-live="polite">
                {createCaseFeedback.message}
              </p>
            ) : null}
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
                <div className="doc-item-row">
                  <div>
                    <strong>{document.filename}</strong>
                    <span>
                      {document.extension} · {document.text_length} chars
                    </span>
                  </div>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => handleDeleteDocument(document.id)}
                    disabled={deletingDocumentId === document.id}
                  >
                    {deletingDocumentId === document.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
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

      {import.meta.env.DEV ? (
        <section className="panel diagnostics">
          <div className="toolbar">
            <div>
              <h2>Diagnostics</h2>
              <p className="hint">Visible in development only. Helps catch frontend/backend target mismatches quickly.</p>
            </div>
          </div>
          <dl className="diagnostics-grid">
            <div>
              <dt>Active API base</dt>
              <dd>{apiBase ?? 'not configured'}</dd>
            </div>
            <div>
              <dt>Last create status</dt>
              <dd>{lastCreateCaseRequest.status}</dd>
            </div>
            <div>
              <dt>Last create URL</dt>
              <dd>{lastCreateCaseRequest.url}</dd>
            </div>
            <div>
              <dt>HTTP status</dt>
              <dd>{lastCreateCaseRequest.httpStatus ?? 'n/a'}</dd>
            </div>
            <div>
              <dt>Last create message</dt>
              <dd>{lastCreateCaseRequest.message}</dd>
            </div>
          </dl>
        </section>
      ) : null}

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

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiRequestError) {
    return `${fallback}: ${error.message}`
  }
  if (error instanceof Error && error.message) {
    return `${fallback}: ${error.message}`
  }
  return fallback
}
