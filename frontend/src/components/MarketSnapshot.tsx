import { useData } from '../context/DataContext'
import CompanyCard from './CompanyCard'

const RANGES: Array<[string, number]> = [
  ['1W', 7],
  ['1M', 30],
  ['3M', 90],
]

interface Props {
  range: number
  onRangeChange: (n: number) => void
  highlightSymbol: string | null
}

// Home page market dashboard: hero banner, top-level metrics, range selector,
// and the live watchlist grid of company cards.
export default function MarketSnapshot({
  range,
  onRangeChange,
  highlightSymbol,
}: Props) {
  const { companies, asOf, loading, apiOnline } = useData()

  const advancing = companies.filter((c) => {
    const s = c.series
    return s.length >= 2 && s.at(-1)! >= s.at(-2)!
  }).length
  const declining = Math.max(companies.length - advancing, 0)
  const breadth = companies.length
    ? Math.round((advancing / companies.length) * 100)
    : 0

  const totalVolume = companies.reduce((sum, c) => {
    const raw = Number(c.volume.replace(/[^0-9.]/g, ''))
    return sum + (Number.isFinite(raw) ? raw : 0)
  }, 0)

  return (
    <main className="home-main">
      <section className="hero-panel">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            PSX MARKET INTELLIGENCE
          </div>
          <h1>See the market clearly.</h1>
          <p className="sub">
            A focused view of Pakistan's most watched companies, powered by live
            market data and intelligent news analysis.
          </p>
          <div className="stamp">
            <span className={apiOnline ? 'online' : 'offline'}>
              {apiOnline ? '● Live market feed' : '○ Feed reconnecting'}
            </span>
            <span>Last close: {asOf || '—'}</span>
          </div>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <b>PKX</b>
          <span>▲</span>
        </div>
      </section>

      <section className="market-overview" aria-label="Market overview">
        <div className="overview-breadth">
          <span>Market breadth</span>
          <strong>
            {companies.length ? advancing : '—'} <small>/ {companies.length || 7} advancing</small>
          </strong>
          <div className="breadth-track" aria-label={`${breadth}% of tracked symbols advancing`}>
            <i style={{ width: `${breadth}%` }} />
          </div>
          <em className={`metric-note ${breadth >= 50 ? 'positive' : ''}`}>
            {companies.length ? `${breadth}% positive` : 'Awaiting data'}
          </em>
        </div>
        <div>
          <span>Tracked symbols</span>
          <strong>
            {companies.length || '—'} <small>companies</small>
          </strong>
          <em className="metric-note">{declining} under pressure</em>
        </div>
        <div>
          <span>Session volume</span>
          <strong>
            {totalVolume ? `${totalVolume.toFixed(1)}M` : '—'} <small>shares</small>
          </strong>
          <em className="metric-note">Across watchlist</em>
        </div>
      </section>

      <div className="ph">
        <div>
          <p className="section-kicker">
            LIVE WATCHLIST <span className="live-badge">● LIVE</span>
          </p>
          <h2>Market snapshot</h2>
          <p className="section-caption">
            Track price action, volume, and momentum at a glance.
          </p>
        </div>
        <div className="rng" role="group" aria-label="Chart range">
          {RANGES.map(([label, n]) => (
            <button
              key={label}
              aria-pressed={n === range}
              onClick={() => onRangeChange(n)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid skeleton">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="co skel" aria-hidden="true">
              <div className="skel-line skel-title" />
              <div className="skel-line skel-price" />
              <div className="skel-chart" />
              <div className="skel-footer">
                <div className="skel-line" />
                <div className="skel-line" />
                <div className="skel-line" />
              </div>
            </div>
          ))}
        </div>
      ) : companies.length === 0 ? (
        <p className="hint">Unable to load live PSX data right now.</p>
      ) : (
        <div className="grid">
          {companies.map((c) => (
            <CompanyCard
              key={c.symbol}
              company={c}
              range={range}
              highlighted={highlightSymbol === c.symbol}
            />
          ))}
        </div>
      )}

      <p className="hint">Tip: hover over a graph to see each day's price.</p>
    </main>
  )
}
