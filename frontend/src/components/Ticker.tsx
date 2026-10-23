import { useData } from '../context/DataContext'

interface Props {
  paused: boolean
  active: number | null
  onItemClick: (index: number) => void
}

// Scrolling "Latest news" marquee. Items are duplicated so the slide animation
// can loop seamlessly (translateX -50%), just like the prototype's .move.
export default function Ticker({ paused, active, onItemClick }: Props) {
  const { announcements } = useData()
  const items = [...announcements, ...announcements]
  return (
    <div className={`ticker${paused ? ' paused' : ''}`}>
      <div className="live">
        <i />Latest news
      </div>
      <div className="track">
        <div className="move">
          {items.map((a, i) => {
            const realIndex = i % announcements.length
            return (
              <button
                key={i}
                className="item"
                aria-expanded={active === realIndex}
                onClick={() => onItemClick(realIndex)}
              >
                <b>{a.symbol}</b>
                {a.headline}
                <span>{a.time}</span>
                <em>Tap for impact</em>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
