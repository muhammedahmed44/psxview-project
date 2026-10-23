import { computeAll } from './dcf'

const base = { rfPct: 11, erpPct: 6, beta: 1, years: 5, growthPct: 8, terminalPct: 3.5 }
const a = computeAll({ ...base, eps: 22.1, price: 97.42 })
const b = computeAll({ ...base, eps: 26.08, price: 212.74 })
const eq = (x: number, y: number, what: string) => {
  if (x !== y) throw new Error(`${what}: got ${x}, expected ${y}`)
}
eq(Number(a.impliedGrowthPct!.toFixed(1)), -10.5, 'KOHC implied')
eq(Number(b.impliedGrowthPct!.toFixed(1)), 5.1, 'DGKC implied')
eq(Math.round(a.fairValue), 201, 'KOHC fair')
eq(Math.round(b.fairValue), 237, 'DGKC fair')
console.log('OK')