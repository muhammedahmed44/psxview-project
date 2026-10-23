import { useRef } from 'react'
import { fmt, toPath, toPoints } from '../utils'

interface Props {
  symbol: string
  data: number[] // sliced series for the selected range
  color: string // 'var(--up)' | 'var(--down)'
  range: number
}

// Interactive sparkline with a hover crosshair + tooltip, mirroring the
// prototype's mousemove/touchmove behaviour exactly.
export default function Sparkline({ symbol, data, color, range }: Props) {
  const cwRef = useRef<HTMLDivElement>(null)
  const vlRef = useRef<HTMLDivElement>(null)
  const dotRef = useRef<HTMLDivElement>(null)
  const tipRef = useRef<HTMLDivElement>(null)

  const pts = toPoints(data, 300, 90, 4)
  const line = toPath(pts)
  const gid = `g-${symbol}`

  const move = (clientX: number) => {
    const cw = cwRef.current
    if (!cw) return
    const r = cw.getBoundingClientRect()
    let n = Math.round(((clientX - r.left) / r.width) * (data.length - 1))
    n = Math.max(0, Math.min(data.length - 1, n))
    const q = pts[n]
    const x = (q[0] / 300) * 100
    const vl = vlRef.current
    const dt = dotRef.current
    const tp = tipRef.current
    if (!vl || !dt || !tp) return
    vl.style.left = x + '%'
    dt.style.left = x + '%'
    tp.style.left = x + '%'
    dt.style.top = (q[1] / 90) * 100 + '%'
    vl.style.display = dt.style.display = tp.style.display = 'block'
    tp.style.left = Math.max(18, Math.min(82, x)) + '%'
    tp.textContent =
      (n === data.length - 1 ? 'Close' : data.length - 1 - n + 'd ago') +
      ': ' +
      fmt(data[n])
  }

  const clear = () => {
    const vl = vlRef.current
    const dt = dotRef.current
    const tp = tipRef.current
    if (vl) vl.style.display = 'none'
    if (dt) dt.style.display = 'none'
    if (tp) tp.style.display = 'none'
  }

  return (
    <div
      className="cw"
      ref={cwRef}
      onMouseMove={(e) => move(e.clientX)}
      onTouchMove={(e) => move(e.touches[0].clientX)}
      onMouseLeave={clear}
    >
      <svg
        viewBox="0 0 300 90"
        preserveAspectRatio="none"
        role="img"
        aria-label={`${symbol} price, last ${range} days`}
      >
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={color} stopOpacity=".22" />
            <stop offset="1" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${line}L296 90L4 90Z`} fill={`url(#${gid})`} />
        <path
          d={line}
          fill="none"
          stroke={color}
          strokeWidth="2.2"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="vl" ref={vlRef} />
      <div className="dot" ref={dotRef} style={{ background: color }} />
      <div className="tip" ref={tipRef} />
    </div>
  )
}
