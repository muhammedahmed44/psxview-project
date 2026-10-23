import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { fetchMarket } from '../api'
import { ANNOUNCEMENTS } from '../data/announcements'
import { SOURCES } from '../data/sources'
import type { Announcement, Company, SourceRecord } from '../types'

interface DataContextValue {
  companies: Company[]
  announcements: Announcement[]
  sources: SourceRecord[]
  asOf: string
  apiOnline: boolean
  loading: boolean
}

const DataContext = createContext<DataContextValue>({
  companies: [],
  announcements: ANNOUNCEMENTS,
  sources: SOURCES,
  asOf: '',
  apiOnline: false,
  loading: true,
})

// Hydrates from the FastAPI backend on mount. Company prices/series come
// live from the psxdata Python package, so we start empty and render real
// data once /api/market responds — no hard-coded prices are shown first.
export function DataProvider({ children }: { children: ReactNode }) {
  const [companies, setCompanies] = useState<Company[]>([])
  const [announcements, setAnnouncements] = useState<Announcement[]>(ANNOUNCEMENTS)
  const [sources, setSources] = useState<SourceRecord[]>(SOURCES)
  const [asOf, setAsOf] = useState('')
  const [apiOnline, setApiOnline] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    fetchMarket()
      .then((d) => {
        if (!mounted) return
        setCompanies(d.companies)
        setAnnouncements(d.announcements)
        setSources(d.sources)
        setAsOf(d.asOf ?? '')
        setApiOnline(true)
      })
      .catch(() => {
        if (mounted) setApiOnline(false)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  return (
    <DataContext.Provider
      value={{ companies, announcements, sources, asOf, apiOnline, loading }}
    >
      {children}
    </DataContext.Provider>
  )
}

export const useData = () => useContext(DataContext)
