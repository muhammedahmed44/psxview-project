import { useAuth } from '../context/AuthContext'
import type { Announcement, AccountTab } from '../types'
import AnnouncementDetail from './AnnouncementDetail'
import Ticker from './Ticker'

interface Props {
  announcement: Announcement | null
  active: number | null
  tickerPaused: boolean
  onTickerItemClick: (index: number) => void
  onValuationClick: () => void
  onPortfolioClick: () => void
  onAnnouncementsClick: () => void
  onLearningClick: () => void
  onOpenAccount: (tab: AccountTab) => void
  onCloseAnnouncement: () => void
  onViewSources: () => void
}

// Sticky app header: brand bar, top-level navigation, scrolling news ticker,
// and the expandable announcement impact card beneath the ticker.
export default function Header({
  announcement,
  active,
  tickerPaused,
  onTickerItemClick,
  onValuationClick,
  onPortfolioClick,
  onAnnouncementsClick,
  onLearningClick,
  onOpenAccount,
  onCloseAnnouncement,
  onViewSources,
}: Props) {
  const { user, logout } = useAuth()

  return (
    <header id="hdr">
      <div className="bar">
        <div className="logo">
          PSX<span>view</span>AI
        </div>

        <nav className="nav" aria-label="Primary">
          <button className="btn ghost" onClick={onAnnouncementsClick}>
            Announcements
          </button>
          <button className="btn ghost" onClick={onValuationClick}>Valuation</button>
          <button className="btn ghost" onClick={onPortfolioClick}>Portfolio</button>
          <button className="btn ghost" onClick={onLearningClick}>
            Learn
          </button>
        </nav>

        <div className="user">
          {user ? (
            <>
              <span className="who" aria-label="Logged in as">
                {user.name}
              </span>
              <button
                className="btn ghost"
                onClick={() => {
                  void logout()
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <button className="btn prime" onClick={() => onOpenAccount('login')}>
              Account
            </button>
          )}
        </div>
      </div>

      <Ticker
        paused={tickerPaused}
        active={active}
        onItemClick={onTickerItemClick}
      />

      <AnnouncementDetail
        announcement={announcement}
        onClose={onCloseAnnouncement}
        onViewSources={onViewSources}
      />
    </header>
  )
}
