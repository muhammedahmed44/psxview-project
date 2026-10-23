import { useState } from 'react'
import { useData } from '../context/DataContext'
import { change, fmt, ICON, STRENGTH_LABEL } from '../utils'

interface Props {
  index: number
  onClose: () => void
  onOpenSource: () => void
}

const TAB_LABELS = ['Sources', 'How it was decided', 'Data used'] as const

// The "where this analysis comes from" modal with three tabs:
// Sources (expandable), How it was decided (steps + confidence), Data used.
export default function SourcesModal({ index, onClose, onOpenSource }: Props) {
  const [tab, setTab] = useState(0)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const { announcements, companies, sources } = useData()

  const a = announcements[index]
  const m = sources[index]
  const co = companies.find((c) => c.symbol === a.symbol)
  const { d, p } = co ? change(co) : { d: 0, p: 0 }
  const mo = co ? (co.series[89] / co.series[59] - 1) * 100 : 0
  const pe = co && co.eps > 0 ? co.price / co.eps : 0
  const level = STRENGTH_LABEL[a.strength]

  const toggle = (i: number) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })

  const metrics: Array<[string, string]> = [
    ['Price (close)', co ? `PKR ${fmt(co.price)}` : '—'],
    ['Day change', `${d >= 0 ? '▲' : '▼'} ${Math.abs(p).toFixed(1)}%`],
    ['Volume', co ? co.volume : '—'],
    ['P/E', pe > 0 ? `${pe.toFixed(1)}×` : 'N/A'],
    ['EPS', co && co.eps > 0 ? `PKR ${fmt(co.eps)}` : 'N/A'],
    ['30-day move', `${mo >= 0 ? '▲' : '▼'} ${Math.abs(mo).toFixed(1)}%`],
  ]

  return (
    <div
      className="modal open"
      id="smodal"
      role="dialog"
      aria-modal="true"
      aria-label="Sources"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="scard" id="sbody">
        <div className="sh">
          <div>
            <small>Where this analysis comes from</small>
            <h3>{a.headline}</h3>
          </div>
          <button className="x" aria-label="Close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="st" role="tablist">
          {TAB_LABELS.map((label, n) => (
            <button
              key={label}
              role="tab"
              aria-selected={tab === n}
              onClick={() => setTab(n)}
            >
              {label}
              {n === 0 ? ` (${m.sources.length})` : ''}
            </button>
          ))}
        </div>

        {/* Sources tab */}
        <div className={`sp${tab === 0 ? ' on' : ''}`}>
          <p className="note">Tap a source to see what the AI read from it.</p>
          {m.sources.map((s, i) => (
            <div className="si" key={i}>
              <button
                className="sih"
                aria-expanded={expanded.has(i)}
                onClick={() => toggle(i)}
              >
                <span className={`ty t-${s.type}`}>{s.type}</span>
                <b>{s.title}</b>
                <small>{s.time}</small>
                <i>▾</i>
              </button>
              <div className={`sib${expanded.has(i) ? ' on' : ''}`}>
                <p>{s.text}</p>
                {s.url ? (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn ghost"
                    style={{ display: 'inline-block', marginTop: '0.5rem', textDecoration: 'none', fontSize: '0.8rem' }}
                  >
                    Open original source ↗
                  </a>
                ) : (
                  <button onClick={onOpenSource}>Open original source</button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* How it was decided tab */}
        <div className={`sp${tab === 1 ? ' on' : ''}`}>
          <ol className="steps">
            <li>
              <span className="n">1</span>
              <div>
                <b>Read the announcement</b>
                <span>Collected the notice and filing text from the sources listed.</span>
              </div>
            </li>
            <li>
              <span className="n">2</span>
              <div>
                <b>Compared with history</b>
                <span>Checked how similar news moved {a.symbol} in the past.</span>
              </div>
            </li>
            <li>
              <span className="n">3</span>
              <div>
                <b>Checked market data</b>
                <span>Used the latest price, volume, P/E and EPS from the PSX data package.</span>
              </div>
            </li>
            <li>
              <span className="n">4</span>
              <div>
                <b>Rated the impact</b>
                <span>
                  {a.summary}: {a.detail}
                </span>
              </div>
            </li>
          </ol>
          <div className={`res ${a.dir}`}>
            <small>Final result</small>
            <strong>
              {ICON[a.dir]} {a.sentiment} · {level} strength
            </strong>
            <small>AI confidence {m.confidence}%</small>
            <div className="bar2">
              <div style={{ width: `${m.confidence}%` }} />
            </div>
          </div>
          <p className="note" style={{ marginTop: 12 }}>
            AI-generated summary. It is not investment advice.
          </p>
        </div>

        {/* Data used tab */}
        <div className={`sp${tab === 2 ? ' on' : ''}`}>
          <div className="dg">
            {metrics.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <b>{value}</b>
              </div>
            ))}
          </div>
          <p className="note" style={{ marginTop: 12 }}>
            Live values from the PSX Python package (psxdata).
          </p>
        </div>
      </div>
    </div>
  )
}
