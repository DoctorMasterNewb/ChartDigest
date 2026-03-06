export type ApiConfig = {
  apiBase: string | null
  configError: string | null
}

export type ApiResult<T> = {
  data: T
  status: number
  url: string
}

export class ApiRequestError extends Error {
  status: number
  url: string

  constructor(message: string, status: number, url: string) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.url = url
  }
}

export function normalizeApiBase(rawValue: string): string {
  const trimmed = rawValue.trim()
  if (!trimmed) {
    throw new Error('VITE_API_BASE is empty.')
  }

  const url = new URL(trimmed)
  return url.toString().replace(/\/$/, '')
}

export function resolveApiConfig(rawValue: string | undefined): ApiConfig {
  if (!rawValue) {
    return {
      apiBase: null,
      configError:
        'Frontend API is not configured. Set VITE_API_BASE to the backend /api URL, for example http://127.0.0.1:8010/api.',
    }
  }

  try {
    return {
      apiBase: normalizeApiBase(rawValue),
      configError: null,
    }
  } catch (error) {
    return {
      apiBase: null,
      configError: error instanceof Error ? error.message : 'VITE_API_BASE is invalid.',
    }
  }
}

export function buildApiUrl(apiBase: string, path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${apiBase}${normalizedPath}`
}

export function buildHealthUrl(apiBase: string): string {
  return buildApiUrl(apiBase.replace(/\/api$/, ''), '/health')
}

export async function api<T>(apiBase: string, path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const url = buildApiUrl(apiBase, path)
  const response = await fetch(url, init)

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new ApiRequestError(payload?.detail ?? `Request failed: ${response.status}`, response.status, url)
  }

  let data: T
  if (response.status === 204) {
    data = undefined as T
  } else {
    data = (await response.json()) as T
  }

  return {
    data,
    status: response.status,
    url,
  }
}
