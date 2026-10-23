import type { Company, Direction } from './types'

export const fmt = (n: number) =>
  n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

// Day change: difference between the last two series points.
export const change = (c: Company) => {
  const s = c.series
  const d = s[89] - s[88]
  return { d, p: (d / s[88]) * 100 }
}

export const cls = (d: number): 'up' | 'down' => (d >= 0 ? 'up' : 'down')

export const ICON: Record<Direction, string> = { up: '▲', down: '▼', neu: '●' }

export const STRENGTH_LABEL = ['', 'Low', 'Medium', 'High'] as const

// Convert a value series to [x,y] points inside a w×h box with padding.
export const toPoints = (a: number[], w: number, h: number, pad: number) => {
  const mn = Math.min(...a)
  const mx = Math.max(...a)
  return a.map((v, i) => [
    pad + (i / (a.length - 1)) * (w - 2 * pad),
    pad + (1 - (v - mn) / (mx - mn || 1)) * (h - 2 * pad),
  ]) as Array<[number, number]>
}

// Build an SVG path `d` string from a list of [x,y] points.
export const toPath = (p: Array<[number, number]>) =>
  p.map((q, i) => (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1)).join('')
