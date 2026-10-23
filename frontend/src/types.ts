export type Direction = 'up' | 'down' | 'neu'

export type Sentiment = 'Positive' | 'Negative' | 'Neutral'

export type SourceType = 'Official' | 'Filing' | 'News' | 'Data'

export interface Company {
  symbol: string
  price: number
  volume: string
  series: number[] // 90 daily values
  eps: number
}

export interface Announcement {
  symbol: string
  time: string
  headline: string
  dir: Direction
  sentiment: Sentiment
  strength: 1 | 2 | 3
  summary: string
  detail: string
}

export interface SourceItem {
  title: string
  type: SourceType
  time: string
  text: string
  url?: string
}

export interface SourceRecord {
  confidence: number
  sources: SourceItem[]
}

export type AccountTab = 'login' | 'signup'
