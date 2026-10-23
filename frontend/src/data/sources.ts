import type { SourceItem, SourceRecord, SourceType } from '../types'

// One source record per announcement (same order as ANNOUNCEMENTS).
// `confidence` is the AI confidence percentage; `sources` is the list the AI read.
export const SOURCES: SourceRecord[] = [
  {
    confidence: 86,
    sources: [
      { title: 'PSX company notice', type: 'Official', time: 'Today, 9:12 AM', text: 'Board meeting result: interim cash dividend approved for the quarter.' },
      { title: 'OGDC quarterly report', type: 'Filing', time: 'Today, 9:30 AM', text: 'Profit and cash position are enough to support the payout.' },
      { title: 'Past dividend records', type: 'Data', time: 'Last 4 payouts', text: 'Amount is close to previous payouts, so the surprise is small.' },
    ],
  },
  {
    confidence: 72,
    sources: [
      { title: 'Regulator notification', type: 'Official', time: 'Today, 8:00 AM', text: 'Revised gas price notification for the sector.' },
      { title: 'PPL annual report', type: 'Filing', time: 'FY 2025', text: 'Gas price share in revenue is limited, so margin change is small.' },
      { title: 'Business news summary', type: 'News', time: 'Today, 8:40 AM', text: 'Analysts expect little change in earnings from this revision.' },
    ],
  },
  {
    confidence: 78,
    sources: [
      { title: 'Central bank statement', type: 'Official', time: 'Yesterday, 4:30 PM', text: 'Policy rate decision and guidance for the next quarters.' },
      { title: 'HBL financial statements', type: 'Filing', time: 'FY 2025', text: 'Interest income is a large part of earnings, so rate changes matter.' },
      { title: 'Banking sector note', type: 'News', time: 'Yesterday, 6:00 PM', text: 'Analysts discuss pressure on spreads for large banks.' },
    ],
  },
  {
    confidence: 81,
    sources: [
      { title: 'PSX company notice', type: 'Official', time: 'Yesterday, 11:00 AM', text: 'Scheduled plant maintenance completed.' },
      { title: 'ENGRO production update', type: 'Filing', time: 'Yesterday, 11:20 AM', text: 'Production restarted earlier than the planned date.' },
    ],
  },
  {
    confidence: 68,
    sources: [
      { title: 'Industry dispatch data', type: 'Data', time: '19 Oct', text: 'Local dispatches rose, exports fell during the month.' },
      { title: 'Cement sector news', type: 'News', time: '19 Oct, 2:30 PM', text: 'Mixed numbers, no strong change expected in earnings.' },
    ],
  },
  {
    confidence: 84,
    sources: [
      { title: 'PSX company notice', type: 'Official', time: '18 Oct, 5:10 PM', text: 'New gas well started commercial production.' },
      { title: 'MARI field update', type: 'Filing', time: '18 Oct, 5:30 PM', text: 'Added output increases expected sales volume.' },
      { title: 'Energy sector news', type: 'News', time: '18 Oct, 7:00 PM', text: 'Market expects a gradual price reaction over a few sessions.' },
    ],
  },
  {
    confidence: 70,
    sources: [
      { title: 'Industry offtake data', type: 'Data', time: '18 Oct', text: 'Urea offtake slowed compared with last month.' },
      { title: 'FFC sales update', type: 'Filing', time: '18 Oct, 1:10 PM', text: 'Lower offtake may trim next quarter sales slightly.' },
    ],
  },
]

// Re-export the source type tag so components can derive the `t-<type>` class.
export type { SourceType }
