// Same math as backend/dcf.py. Runs in the browser so sliders feel instant.
// The server recomputes on Save, so the browser numbers are never trusted.

export interface DcfInputs {
  eps: number
  price: number
  rfPct: number
  erpPct: number
  beta: number
  years: number
  growthPct: number
  terminalPct: number
}

export interface DcfResult {
  requiredReturnPct: number
  impliedGrowthPct: number | null // null = needs more than 500%
  fairValue: number
  upsidePct: number
  growthAxis: number[] // 0,2,...,36
  upsideCurve: number[]
}

const REVERSE_TERMINAL = 0.035

export function dcfValue(fcf0: number, g: number, r: number, gT: number, years: number): number {
  let pv = 0
  let fcfN = fcf0
  for (let t = 1; t <= years; t++) {
    fcfN = fcf0 * Math.pow(1 + g, t)
    pv += fcfN / Math.pow(1 + r, t)
  }
  const tv = (fcfN * (1 + gT)) / (r - gT)
  return pv + tv / Math.pow(1 + r, years)
}

export function solveImplied(price: number, fcf0: number, r: number, years: number): number | null {
  if (fcf0 <= 0 || price <= 0 || r <= REVERSE_TERMINAL) return null
  if (dcfValue(fcf0, 5.0, r, REVERSE_TERMINAL, years) < price) return null
  let lo = -0.99
  let hi = 5.0
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2
    if (dcfValue(fcf0, mid, r, REVERSE_TERMINAL, years) < price) lo = mid
    else hi = mid
    if (hi - lo < 1e-9) break
  }
  return (lo + hi) / 2
}

/** Throws if required return <= terminal growth (math breaks). Catch it in the UI. */
export function computeAll(i: DcfInputs): DcfResult {
  const r = i.rfPct / 100 + i.beta * (i.erpPct / 100)
  const gT = i.terminalPct / 100
  if (r <= gT) throw new Error('Required return must be higher than terminal growth')
  const implied = solveImplied(i.price, i.eps, r, i.years)
  const fair = dcfValue(i.eps, i.growthPct / 100, r, gT, i.years)
  const growthAxis = Array.from({ length: 19 }, (_, k) => k * 2)
  return {
    requiredReturnPct: r * 100,
    impliedGrowthPct: implied === null ? null : implied * 100,
    fairValue: fair,
    upsidePct: ((fair - i.price) / i.price) * 100,
    growthAxis,
    upsideCurve: growthAxis.map((g) => ((dcfValue(i.eps, g / 100, r, gT, i.years) - i.price) / i.price) * 100),
  }
}