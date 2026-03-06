import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const originalFetch = globalThis.fetch

type MockResponseInit = {
  ok?: boolean
  status?: number
  body?: unknown
}

function makeResponse({ ok = true, status = 200, body }: MockResponseInit): Response {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response
}

async function loadApp(apiBase = 'http://127.0.0.1:8010/api') {
  vi.resetModules()
  vi.stubEnv('VITE_API_BASE', apiBase)
  const module = await import('./App')
  return module.default
}

describe('App create case flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    globalThis.fetch = originalFetch
  })

  it('shows config error when VITE_API_BASE is missing', async () => {
    const App = await loadApp('')
    globalThis.fetch = vi.fn()

    render(<App />)

    const errors = await screen.findAllByText(/Frontend API is not configured\. Set VITE_API_BASE/i)
    expect(errors).not.toHaveLength(0)
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })

  it('creates a case, updates the list immediately, and shows success feedback', async () => {
    const fetchMock = vi.fn()
    globalThis.fetch = fetchMock

    fetchMock.mockResolvedValueOnce(
      makeResponse({
        body: {
          provider_mode: 'ollama',
          ollama_base_url: 'http://127.0.0.1:11434',
          ollama_model: 'llama3.1:8b',
        },
      }),
    )
    fetchMock.mockResolvedValueOnce(makeResponse({ body: [] }))
    fetchMock.mockResolvedValueOnce(
      makeResponse({
        status: 200,
        body: {
          id: 42,
          title: 'ER timeline review',
          description: 'overnight admit',
          created_at: '2026-03-06T17:00:00',
          updated_at: '2026-03-06T17:00:00',
        },
      }),
    )
    fetchMock.mockResolvedValueOnce(
      makeResponse({
        body: [
          {
            id: 42,
            title: 'ER timeline review',
            description: 'overnight admit',
            created_at: '2026-03-06T17:00:00',
            updated_at: '2026-03-06T17:00:00',
          },
        ],
      }),
    )
    fetchMock.mockResolvedValueOnce(
      makeResponse({
        body: {
          id: 42,
          title: 'ER timeline review',
          description: 'overnight admit',
          created_at: '2026-03-06T17:00:00',
          updated_at: '2026-03-06T17:00:00',
          documents: [],
          jobs: [],
          running_summary: null,
          final_summary: null,
        },
      }),
    )

    const App = await loadApp()
    render(<App />)

    await screen.findByText('No cases yet.')

    await userEvent.type(screen.getByPlaceholderText('ER timeline review'), 'ER timeline review')
    await userEvent.type(screen.getByPlaceholderText('Optional context for the digest'), 'overnight admit')
    await userEvent.click(screen.getByRole('button', { name: 'Create case' }))

    expect(await screen.findByText('Created case "ER timeline review".')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ER timeline review/i })).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8010/api/cases',
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  it('shows inline create error feedback when the request fails', async () => {
    const fetchMock = vi.fn()
    globalThis.fetch = fetchMock

    fetchMock.mockResolvedValueOnce(
      makeResponse({
        body: {
          provider_mode: 'ollama',
          ollama_base_url: 'http://127.0.0.1:11434',
          ollama_model: 'llama3.1:8b',
        },
      }),
    )
    fetchMock.mockResolvedValueOnce(makeResponse({ body: [] }))
    fetchMock.mockResolvedValueOnce(
      makeResponse({
        ok: false,
        status: 502,
        body: { detail: 'Upstream create failed' },
      }),
    )

    const App = await loadApp()
    render(<App />)

    await screen.findByText('No cases yet.')

    await userEvent.type(screen.getByPlaceholderText('ER timeline review'), 'ER timeline review')
    await userEvent.click(screen.getByRole('button', { name: 'Create case' }))

    expect(await screen.findByText('Create case failed: Upstream create failed', { selector: 'p' })).toBeInTheDocument()
  })
})
