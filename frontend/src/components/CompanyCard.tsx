import type { Company } from '../types'
import { change, fmt } from '../utils'
import Sparkline from './Sparkline'

interface Props {
  company: Company
  range: number
  highlighted: boolean
}

// One market-snapshot card: symbol, day-change pill, price, sparkline, and
// the Volume / P/E / EPS footer. Matches the prototype's .co markup.
export default function CompanyCard({ company, range, highlighted }: Props) {
  const { d, p } = change(company)
  const dir = d >= 0 ? 'up' : 'down'
  const color = d >= 0 ? 'var(--up)' : 'var(--down)'
  const data = company.series.slice(-range)
  const pe = company.eps > 0 ? company.price / company.eps : 0

  return (
    <article
      className={`co ${dir}${highlighted ? ' hl' : ''}`}
      data-t={company.symbol}
    >
      <div className="top">
        <b>{company.symbol}</b>
        <span className="pill">
          {d >= 0 ? '▲' : '▼'} {Math.abs(p).toFixed(1)}%
        </span>
      </div>
      <div className="px">PKR {fmt(company.price)}</div>
      <Sparkline symbol={company.symbol} data={data} color={color} range={range} />
      <dl>
        <div>
          <dt>Volume</dt>
          <dd>{company.volume}</dd>
        </div>
        <div>
          <dt>P/E</dt>
          <dd>{pe > 0 ? `${pe.toFixed(1)}×` : 'N/A'}</dd>
        </div>
        <div>
          <dt>EPS</dt>
          <dd>{company.eps > 0 ? fmt(company.eps) : 'N/A'}</dd>
        </div>
      </dl>
    </article>
  )
}
