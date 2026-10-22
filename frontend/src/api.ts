import type { Announcement, Company, SourceRecord } from './types'

// ---------- market, auth + valuation (cookie session) ----------
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// One helper for every call: JSON in, JSON out, readable error messages.
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin', // sends the login cookie
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') msg = body.detail
      else if (Array.isArray(body.detail)) msg = body.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch {
      /* body was not JSON; keep default message */
    }
    throw new ApiError(res.status, msg)
  }
  return (await res.json()) as T
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export interface MarketResponse {
  companies: Company[]
  announcements: Announcement[]
  sources: SourceRecord[]
  asOf?: string
}

export const fetchMarket = () => request<MarketResponse>('/api/market')

export interface User {
  id: number
  name: string
  email: string
}

export const authApi = {
  register: (name: string, email: string, password: string) =>
    post<{ challenge_token: string }>('/api/auth/register', { name, email, password }),
  login: (email: string, password: string) =>
    post<{ challenge_token: string }>('/api/auth/login', { email, password }),
  resendOtp: (challenge_token: string) =>
    post<{ challenge_token: string }>('/api/auth/resend-otp', { challenge_token }),
  verifyOtp: (challenge_token: string, code: string) =>
    post<User>('/api/auth/verify-otp', { challenge_token, code }),
  me: () => request<User>('/api/auth/me'),
  logout: () => post<{ ok: boolean }>('/api/auth/logout'),
}

export interface ValuationBody {
  symbol: string
  eps: number
  price: number
  rf_pct: number
  erp_pct: number
  beta: number
  years: number
  growth_pct: number
  terminal_pct: number
}

export interface SavedItem {
  id: number
  symbol: string
  created_at: string
  inputs: ValuationBody
  result: { required_return_pct: number; implied_growth_pct: number | null; fair_value: number; upside_pct: number }
}

export const valuationApi = {
  save: (b: ValuationBody) => post<{ id: number }>('/api/valuation/saved', b),
  list: () => request<SavedItem[]>('/api/valuation/saved'),
  remove: (id: number) => request<{ ok: boolean }>(`/api/valuation/saved/${id}`, { method: 'DELETE' }),
  explain: (b: ValuationBody) => post<{ text: string; source: 'gemini' | 'fallback' }>('/api/valuation/explain', b),
}
