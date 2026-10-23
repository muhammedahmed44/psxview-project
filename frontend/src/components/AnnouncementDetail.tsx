import type { CSSProperties } from 'react'
import type { Announcement } from '../types'
import { useData } from '../context/DataContext'
import { change, fmt, ICON, STRENGTH_LABEL } from '../utils'

interface Props {
  announcement: Announcement | null
  onClose: () => void
  onViewSources: () => void
}

// The announcement impact dropdown that opens under the ticker.
export default function AnnouncementDetail({
  announcement,
  onClose,
  onViewSources,
}: Props) {
  const { companies } = useData()
  if (!announcement) return <div id="detail" />

  const co = companies.find((c) => c.symbol === announcement.symbol)
  const { d, p } = co ? change(co) : { d: 0, p: 0 }
  const upDir = d >= 0
  const pillStyle = {
    '--c': `var(--${upDir ? 'up' : 'down'})`,
    '--soft': `var(--${upDir ? 'up' : 'down'}-soft)`,
  } as CSSProperties

  return (
    <div id="detail" className="open" aria-live="polite">
      <div
        className={`dcard ${announcement.dir}`}
        role="dialog"
        aria-label="Announcement impact"
      >
        <div className="dtop">
          <span className="tag">{announcement.symbol}</span>
          <div>
            <h3>{announcement.headline}</h3>
            <time>{announcement.time}</time>
          </div>
          <button className="x" aria-label="Close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="ban">
          <div className="arrow">{ICON[announcement.dir]}</div>
          <div>
            <small>Expected impact: {announcement.summary}</small>
            <strong>{announcement.sentiment}</strong>
          </div>
          <div className="meter">
            <div>
              {[1, 2, 3].map((n) => (
                <i key={n} className={n <= announcement.strength ? 'on' : ''} />
              ))}
            </div>
            {STRENGTH_LABEL[announcement.strength]} strength
          </div>
        </div>
        <div className="dbody">
          <p>{announcement.detail}</p>
          <div className="rel">
            <span>
              {co ? (
                <>
                  {announcement.symbol} now: PKR {fmt(co.price)}{' '}
                  <span className="pill" style={pillStyle}>
                    {upDir ? '▲' : '▼'} {Math.abs(p).toFixed(1)}%
                  </span>
                </>
              ) : (
                <span>Market / Sector Impact</span>
              )}
            </span>
            <button className="src" onClick={onViewSources}>
              View sources
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
