import type { Announcement } from '../types'

// One announcement per company, mirroring the prototype's ANN array.
// Fields: symbol, time, headline, dir, sentiment, strength, summary, detail.
export const ANNOUNCEMENTS: Announcement[] = [
  {
    symbol: 'OGDC',
    time: 'Today, 9:40 AM',
    headline: 'Board approves interim cash dividend for the quarter',
    dir: 'up',
    sentiment: 'Positive',
    strength: 3,
    summary: 'Dividend support',
    detail:
      'Payout is in line with last year, so buyers may step in. Expect a modest move up, not a big jump.',
  },
  {
    symbol: 'PPL',
    time: 'Today, 8:15 AM',
    headline: 'Gas price notification revised by regulator',
    dir: 'neu',
    sentiment: 'Neutral',
    strength: 1,
    summary: 'Limited effect',
    detail:
      'Revision is small and margins stay mostly flat. Sector circular debt news can still add short-term swings.',
  },
  {
    symbol: 'HBL',
    time: 'Yesterday, 4:50 PM',
    headline: 'Central bank announces policy rate decision',
    dir: 'down',
    sentiment: 'Negative',
    strength: 2,
    summary: 'Margin pressure',
    detail:
      'A lower rate can squeeze interest margins in the coming quarters. Watch guidance in the next results.',
  },
  {
    symbol: 'ENGRO',
    time: 'Yesterday, 11:20 AM',
    headline: 'Fertilizer plant completes scheduled maintenance',
    dir: 'up',
    sentiment: 'Positive',
    strength: 2,
    summary: 'Output back early',
    detail:
      'Production resumes earlier than planned, which supports volumes and quarterly earnings.',
  },
  {
    symbol: 'LUCK',
    time: '19 Oct, 2:05 PM',
    headline: 'Monthly cement dispatches reported',
    dir: 'neu',
    sentiment: 'Neutral',
    strength: 1,
    summary: 'Mixed numbers',
    detail:
      'Local sales rose while exports slipped. Net effect on earnings should be small.',
  },
  {
    symbol: 'MARI',
    time: '18 Oct, 5:30 PM',
    headline: 'New gas well enters production',
    dir: 'up',
    sentiment: 'Positive',
    strength: 3,
    summary: 'Higher output',
    detail:
      'Added production lifts expected revenue. Market may price this in over the next few sessions.',
  },
  {
    symbol: 'FFC',
    time: '18 Oct, 1:10 PM',
    headline: 'Urea offtake slows during the month',
    dir: 'down',
    sentiment: 'Negative',
    strength: 1,
    summary: 'Slight softness',
    detail:
      'Lower offtake may trim next quarter sales a little. Impact stays small unless it continues.',
  },
]
