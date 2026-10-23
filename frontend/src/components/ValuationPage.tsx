import { useEffect, useMemo, useState } from 'react'
import { valuationApi, type SavedItem, type ValuationBody } from '../api'
import { useAuth } from '../context/AuthContext'
import { useData } from '../context/DataContext'
import { computeAll } from '../lib/dcf'
import ValuationChart from './ValuationChart'
import './valuation.css'

function Slider(p: {
  label: string
  value: number
  min: number
  max: number
  step: number
  suffix: string
  onChange: (v: number) => void
}) {
  return (
    <div className="v-slider">
      <div className="v-row">
        <span>{p.label}</span>
        <b>
          {p.value.toFixed(p.step < 1 ? 1 : 0)}
          {p.suffix}
        </b>
      </div>
      <input
        type="range"
        min={p.min}
        max={p.max}
        step={p.step}
        value={p.value}
        onChange={(e) => p.onChange(parseFloat(e.target.value))}
        aria-label={p.label}
      />
    </div>
  )
}

export default function ValuationPage({ onNeedLogin }: { onNeedLogin: () => void }) {
  const { companies } = useData()
  const { user, checking } = useAuth()

  const [symbol, setSymbol] = useState('')
  const [eps, setEps] = useState('')
  const [price, setPrice] = useState('')
  const [rf, setRf] = useState(11)
  const [erp, setErp] = useState(6)
  const [beta, setBeta] = useState(1)
  const [years, setYears] = useState(5)
  const [growth, setGrowth] = useState(8)
  const [terminal, setTerminal] = useState(3.5)

  const [saved, setSaved] = useState<SavedItem[]>([])
  const [aiText, setAiText] = useState('')
  const [aiSource, setAiSource] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  // Pick a company from the live list -> fill price + EPS (user can still edit).
  function pickCompany(sym: string) {
    setSymbol(sym)
    const c = companies.find((x) => x.symbol === sym)
    if (c) {
      setPrice(String(c.price))
      setEps(c.eps > 0 ? String(c.eps) : '')
    }
    setAiText('')
  }

  const calc = useMemo(() => {
    const e = parseFloat(eps)
    const p = parseFloat(price)
    if (!(e > 0 && p > 0)) return { ok: false as const, msg: 'Enter EPS and price above zero.' }
    try {
      return {
        ok: true as const,
        res: computeAll({ eps: e, price: p, rfPct: rf, erpPct: erp, beta, years, growthPct: growth, terminalPct: terminal }),
      }
    } catch (err) {
      return { ok: false as const, msg: (err as Error).message }
    }
  }, [eps, price, rf, erp, beta, years, growth, terminal])

  const body = (): ValuationBody => ({
    symbol: symbol || 'CUSTOM',
    eps: parseFloat(eps),
    price: parseFloat(price),
    rf_pct: rf,
    erp_pct: erp,
    beta,
    years,
    growth_pct: growth,
    terminal_pct: terminal,
  })

  const loadSaved = () => valuationApi.list().then(setSaved).catch(() => setSaved([]))
  useEffect(() => {
    if (user) void loadSaved()
    else setSaved([])
  }, [user])

  async function run(fn: () => Promise<void>) {
    setBusy(true)
    setNote('')
    try {
      await fn()
    } catch (e) {
      setNote((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (checking) return <main className="vwrap"><p>Loading…</p></main>
  if (!user)
    return (
      <main className="vwrap">
        <div className="v-card v-center">
          <h2>Valuation tool</h2>
          <p>Log in to use the reverse-DCF valuation tool and save your work.</p>
          <button className="vbtn" onClick={onNeedLogin}>Login / Sign up</button>
        </div>
      </main>
    )

  const res = calc.ok ? calc.res : null
  return (
    <main className="vwrap">
      <h1>Reverse DCF valuation</h1>
      <p className="v-sub">See what growth the current price already assumes, then test your own estimate.</p>

      <section className="v-card">
        <h3>1. Company</h3>
        <div className="v-grid3">
          <label>Symbol
            <select value={symbol} onChange={(e) => pickCompany(e.target.value)}>
              <option value="">Custom…</option>
              {companies.map((c) => <option key={c.symbol} value={c.symbol}>{c.symbol}</option>)}
            </select>
          </label>
          <label>EPS / FCF per share (Rs)
            <input type="number" min="0" step="0.5" value={eps} onChange={(e) => setEps(e.target.value)} />
          </label>
          <label>Current price (Rs)
            <input type="number" min="0" step="1" value={price} onChange={(e) => setPrice(e.target.value)} />
          </label>
        </div>
      </section>

      <section className="v-card">
        <h3>2. Required return (CAPM)</h3>
        <div className="v-grid3">
          <Slider label="Risk-free rate" value={rf} min={5} max={22} step={0.5} suffix="%" onChange={setRf} />
          <Slider label="Equity risk premium" value={erp} min={2} max={14} step={0.5} suffix="%" onChange={setErp} />
          <Slider label="Beta" value={beta} min={0.3} max={2.5} step={0.1} suffix="×" onChange={setBeta} />
        </div>
        <div className="v-years">
          {[3, 5, 10].map((y) => (
            <button key={y} className={y === years ? 'on' : ''} onClick={() => setYears(y)}>{y} years</button>
          ))}
        </div>
      </section>

      {!res ? (
        <p className="v-warn">{calc.ok ? '' : calc.msg}</p>
      ) : (
        <>
          <section className="v-card v-results">
            <div className="v-big">
              <small>Price already implies</small>
              <strong>{res.impliedGrowthPct === null ? '>500%' : `${res.impliedGrowthPct.toFixed(1)}%`}</strong>
              <small>yearly growth · required return {res.requiredReturnPct.toFixed(1)}%</small>
            </div>
            <div className="v-big">
              <small>Fair value at your estimate</small>
              <strong>Rs {res.fairValue.toFixed(0)}</strong>
              <small className={res.upsidePct >= 0 ? 'up' : 'down'}>
                {res.upsidePct >= 0 ? '+' : ''}{res.upsidePct.toFixed(0)}% vs price
              </small>
            </div>
          </section>

          <section className="v-card">
            <h3>3. Your estimate</h3>
            <div className="v-grid2">
              <Slider label="FCF growth" value={growth} min={0} max={100} step={0.5} suffix="%" onChange={setGrowth} />
              <Slider label="Terminal growth" value={terminal} min={0} max={8} step={0.5} suffix="%" onChange={setTerminal} />
            </div>
            <ValuationChart growthAxis={res.growthAxis} upsideCurve={res.upsideCurve} impliedGrowthPct={res.impliedGrowthPct} />
          </section>

          <section className="v-card">
            <div className="v-actions">
              <button className="vbtn" disabled={busy} onClick={() => run(async () => {
                await valuationApi.save(body()); await loadSaved(); setNote('Saved.')
              })}>Save</button>
              <button className="vbtn alt" disabled={busy} onClick={() => run(async () => {
                const r = await valuationApi.explain(body()); setAiText(r.text); setAiSource(r.source)
              })}>Explain with AI</button>
            </div>
            {note && <p className="v-note">{note}</p>}
            {aiText && (
              <div className="v-ai">
                <p>{aiText}</p>
                <small>{aiSource === 'gemini' ? 'Written by AI' : 'Basic summary (AI unavailable)'}</small>
              </div>
            )}
          </section>
        </>
      )}

      <section className="v-card">
        <h3>Saved valuations</h3>
        {saved.length === 0 ? <p className="v-sub">Nothing saved yet.</p> : (
          <ul className="v-saved">
            {saved.map((s) => (
              <li key={s.id}>
                <b>{s.symbol}</b>
                <span>fair Rs {s.result.fair_value.toFixed(0)} · implied {s.result.implied_growth_pct === null ? '>500' : s.result.implied_growth_pct.toFixed(1)}%</span>
                <button className="linkbtn" onClick={() => run(async () => { await valuationApi.remove(s.id); await loadSaved() })}>Delete</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="v-disc">Educational tool only. Not a buy or sell recommendation. Inputs are user-supplied. Not for banks or insurers.</p>
    </main>
  )
}