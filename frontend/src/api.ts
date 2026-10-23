// ---------- auth + valuation (cookie session) ----------
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

export interface User {
  id: number
  name: string
  email: string
}

export interface AuthenticatorSetup {
  qr_code_data_url: string
  manual_key: string
  issuer: string
}

export interface AuthChallenge {
  challenge_token: string
  requires_setup: boolean
  setup: AuthenticatorSetup | null
}

export interface AuthResult extends User {
  recovery_codes: string[] | null
}

// Market response used by the home dashboard. Keeping this call in the same
// request helper preserves cookie credentials and the existing /api contract.
export interface MarketPayload {
  companies: import('./types').Company[]
  announcements: import('./types').Announcement[]
  sources: import('./types').SourceRecord[]
  asOf?: string
}

export const fetchMarket = () => request<MarketPayload>('/api/market')

export interface ResearchReply { answer: string; citations: { title: string; date: string; provenance: string }[]; provenance: { market: string; news: string; answer: 'gemini' | 'fallback' } }
export const researchApi = {
  ask: (question: string, conversation_id?: number) => post<ResearchReply>('/api/research/ask', { question, conversation_id }),
  conversations: () => request<{ id: number; title: string; messages: { role: string; content: string; citations: string }[] }[]>('/api/research/conversations'),
  createConversation: () => post<{ id: number; title: string }>('/api/research/conversations'),
}

export const authApi = {
  register: (name: string, email: string, password: string) =>
    post<AuthChallenge>('/api/auth/register', { name, email, password }),
  login: (email: string, password: string) =>
    post<AuthChallenge>('/api/auth/login', { email, password }),
  verifyTotp: (challenge_token: string, code: string) =>
    post<AuthResult>('/api/auth/verify-totp', { challenge_token, code }),
  me: () => request<User>('/api/auth/me'),
  logout: () => post<{ ok: boolean }>('/api/auth/logout'),
}

export interface Holding { id: number; symbol: string; quantity: number; average_price: number; latest_price: number | null; price_status: string; sector: string; invested: number; current_value: number | null; pnl: number | null }
export interface PortfolioPayload { holdings: Holding[]; metrics: { invested: number; current_value: number | null; pnl: number | null; pnl_pct: number | null }; sectors: { sector: string; value: number; percentage: number }[]; as_of: string }
export const portfolioApi = {
  list: () => request<PortfolioPayload>('/api/portfolio'),
  add: (symbol: string, quantity: number, average_price: number) => post<Holding>('/api/portfolio', { symbol, quantity, average_price }),
  update: (id: number, symbol: string, quantity: number, average_price: number) => request<Holding>(`/api/portfolio/${id}`, { method: 'PUT', body: JSON.stringify({ symbol, quantity, average_price }) }),
  remove: (id: number) => request<{ ok: boolean }>(`/api/portfolio/${id}`, { method: 'DELETE' }),
  analyze: () => post<{ text: string; source: string; facts: string[] }>('/api/portfolio/analyze'),
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

export const academyApi = { progress: (module_id:string, progress:number, score:number) => post<{ok:boolean}>('/api/academy/progress', {module_id, progress, score}), explain: (lesson:string, content:string, language:string, mode:string) => post<{text:string;source:string}>('/api/academy/explain', {lesson, content, language, mode}), status: () => request<Record<string,unknown>[]>('/api/academy/progress') }

export const valuationApi = {
  save: (b: ValuationBody) => post<{ id: number }>('/api/valuation/saved', b),
  list: () => request<SavedItem[]>('/api/valuation/saved'),
  remove: (id: number) => request<{ ok: boolean }>(`/api/valuation/saved/${id}`, { method: 'DELETE' }),
  explain: (b: ValuationBody) => post<{ text: string; source: 'gemini' | 'fallback' }>('/api/valuation/explain', b),
}
