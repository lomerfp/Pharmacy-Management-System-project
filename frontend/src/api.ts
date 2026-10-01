const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

let accessToken: string | null = null
let refreshToken: string | null = null

export type StaffSummary = {
  id: number
  username: string
  display_name: string
  role: string | null
  permissions: string[]
}

type TokenPair = { access: string; refresh: string }

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  let response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (response.status === 401 && retry && refreshToken && path !== '/auth/token/refresh/') {
    const refreshResponse = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    })
    if (refreshResponse.ok) {
      const updated = await refreshResponse.json() as { access: string; refresh?: string }
      accessToken = updated.access
      if (updated.refresh) refreshToken = updated.refresh
      return request<T>(path, init, false)
    }
    clearTokens()
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json() as { detail?: string; [key: string]: unknown }
      detail = body.detail ?? Object.values(body).flat().join(' ')
    } catch { /* Response body is not JSON. */ }
    throw new ApiError(response.status, String(detail))
  }
  if (response.status === 204) return undefined as T
  if (response.headers.get('content-type')?.includes('text/csv')) return response.text() as Promise<T>
  return response.json() as Promise<T>
}

function clearTokens() {
  accessToken = null
  refreshToken = null
}

export async function login(username: string, password: string): Promise<StaffSummary> {
  const tokens = await request<TokenPair>('/auth/token/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, false)
  accessToken = tokens.access
  refreshToken = tokens.refresh
  try {
    return await request<StaffSummary>('/auth/me/')
  } catch (error) {
    clearTokens()
    throw error
  }
}

export async function getCurrentStaff(): Promise<StaffSummary | null> {
  if (!accessToken) return null
  try {
    return await request<StaffSummary>('/auth/me/')
  } catch {
    clearTokens()
    return null
  }
}

export async function logout(): Promise<void> {
  const token = refreshToken
  if (!token) return
  try {
    await request<void>('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh: token }) }, false)
  } finally {
    clearTokens()
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path)
}

export async function apiPost<T>(path: string, data: unknown, idempotencyKey?: string): Promise<T> {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey)
  return request<T>(path, { method: 'POST', headers, body: JSON.stringify(data) })
}

export async function apiPatch<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function apiDelete(path: string): Promise<void> {
  return request<void>(path, { method: 'DELETE' })
}

export async function requestPasswordReset(email: string): Promise<void> {
  await request<void>('/auth/password/reset/', { method: 'POST', body: JSON.stringify({ email }) }, false)
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  await request<void>('/auth/password/reset/confirm/', { method: 'POST', body: JSON.stringify({ token, new_password: newPassword }) }, false)
}

export async function submitSignup(data: { username: string; email: string; display_name: string; password: string }): Promise<{ detail: string }> {
  return request<{ detail: string }>('/auth/signup/', { method: 'POST', body: JSON.stringify(data) }, false)
}
