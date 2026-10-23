import { useCallback, useEffect, useRef, useState } from 'react'
import AccountModal from './components/AccountModal'
import Header from './components/Header'
import MarketSnapshot from './components/MarketSnapshot'
import SourcesModal from './components/SourcesModal'
import Toast from './components/Toast'
import ValuationPage from './components/ValuationPage'
import ResearchAssistant from './components/ResearchAssistant'
import PortfolioPage from './components/PortfolioPage'
import AcademyPage from './components/AcademyPage'
import { AuthProvider } from './context/AuthContext'
import { DataProvider, useData } from './context/DataContext'
import type { AccountTab } from './types'

function AppContent() {
  const { announcements } = useData()

  const [active, setActive] = useState<number | null>(null)
  const [range, setRange] = useState(30)
  const [sourcesIndex, setSourcesIndex] = useState<number | null>(null)
  const [account, setAccount] = useState<{ open: boolean; tab: AccountTab }>({
    open: false,
    tab: 'login',
  })
  const [toast, setToast] = useState<string | null>(null)
  const [view, setView] = useState<'market' | 'valuation' | 'portfolio' | 'academy'>('market')

  const announcement = active !== null ? announcements[active] ?? null : null
  const highlightSymbol = announcement?.symbol ?? null
  const tickerPaused = active !== null

  const showToast = useCallback((msg: string, ms = 2400) => {
    setToast(msg)
    window.setTimeout(() => setToast(null), ms)
  }, [])

  const toggleAnnouncement = useCallback((index: number) => {
    setActive((prev) => (prev === index ? null : index))
  }, [])

  const openAccount = useCallback((tab: AccountTab) => {
    setActive(null)
    setAccount({ open: true, tab })
  }, [])

  // Refs hold the latest open-layer state for the global Escape handler.
  const sourcesRef = useRef(sourcesIndex)
  const accountRef = useRef(account)
  sourcesRef.current = sourcesIndex
  accountRef.current = account

  // Click outside the header and modals closes the announcement detail.
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null
      if (!t) return
      if (!t.closest('#hdr, #smodal, #modal')) setActive(null)
    }
    document.addEventListener('click', onDocClick)
    return () => document.removeEventListener('click', onDocClick)
  }, [])

  // Escape closes the topmost open layer: sources → account → detail.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (sourcesRef.current !== null) {
        setSourcesIndex(null)
        return
      }
      if (accountRef.current.open) {
        setAccount((a) => ({ ...a, open: false }))
        return
      }
      setActive(null)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <>
      <Header
        announcement={announcement}
        active={active}
        tickerPaused={tickerPaused}
        onTickerItemClick={toggleAnnouncement}
        onPortfolioClick={() => { setActive(null); setView('portfolio') }}
        onValuationClick={() => {
          setActive(null)
          setView('valuation')
        }}
        onAnnouncementsClick={() => {
          setView('market')
          window.scrollTo({ top: 0, behavior: 'smooth' })
          setActive(0)
        }}
        onLearningClick={() => { setActive(null); setView('academy') }}
        onOpenAccount={openAccount}
        onCloseAnnouncement={() => setActive(null)}
        onViewSources={() => {
          if (active !== null) setSourcesIndex(active)
        }}
      />

      {view === 'academy' ? <AcademyPage onNeedLogin={() => openAccount('login')} /> : view === 'portfolio' ? <PortfolioPage onNeedLogin={() => openAccount('login')} /> : view === 'market' ? (
        <>
          <ResearchAssistant />
          <MarketSnapshot
          range={range}
          onRangeChange={setRange}
          highlightSymbol={highlightSymbol}
          />
        </>
      ) : (
        <ValuationPage onNeedLogin={() => openAccount('login')} />
      )}

      {sourcesIndex !== null && (
        <SourcesModal
          index={sourcesIndex}
          onClose={() => setSourcesIndex(null)}
          onOpenSource={() =>
            showToast('Prototype: the original source link will open here.', 2200)
          }
        />
      )}

      <AccountModal
        open={account.open}
        tab={account.tab}
        onClose={() => setAccount((a) => ({ ...a, open: false }))}
      />

      <Toast message={toast} />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <DataProvider>
        <AppContent />
      </DataProvider>
    </AuthProvider>
  )
}
