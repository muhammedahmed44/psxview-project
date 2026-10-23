# PSXviewAI Data Sources (initial notes)

This document captures initial assumptions and constraints around external data
sources. It will evolve as concrete adapters are implemented.

## 1. Market data

- The preferred approach is to wrap approved PSX data sources behind the
  `MarketDataProvider` interface defined in `backend/app/ingestion/market_data.py`.
- The `psxdata` Python package is a candidate provider but must be evaluated in
  a later phase using its documentation and real responses. Until then we make
  **no assumptions** about:
  - Whether quotes are live, delayed, or end-of-day.
  - Coverage of instruments or corporate actions.
  - Availability of historical data or a news feed.
- Every stored market snapshot must include:
  - `source` – name of provider (e.g. `psxdata`).
  - `as_of` – market timestamp for the quote.
  - `retrieved_at` – when our system fetched it.
  - `is_delayed` – explicit flag if the provider states that data is delayed.

UI must always show the source and timestamp and must not label stale data as
"live".

## 2. News and documents

Planned sources include (subject to licensing and robots.txt):

- PSX announcements and disclosures.
- Regulatory sources (SECP, SBP, PBS).
- Reputable Pakistani business news outlets.

Ingestion adapters will:

- Respect robots and terms of service.
- Store publication and retrieval timestamps separately.
- Deduplicate by URL or content hash and map items to companies and sectors.
- Treat all scraped text as untrusted data and avoid executing or following
  embedded instructions.

## 3. Financial reports

- Official company filings (annual and quarterly reports) are the primary
  source for structured metrics (revenue, EPS, debt, etc.).
- Reports will be stored as `Document` records with stable IDs, source URLs,
  checksums, and reporting periods.
- Parsed metrics will be linked to `EvidenceItem` records so that every
  financial figure in a valuation can be traced back to a filing page and
  period.

## 4. AI models

- A hosted LLM will be used through the `AIProvider` interface. Provider and
  model selection (e.g. OpenAI, Anthropic) will be made in a later phase after
  verifying pricing, data usage terms, and availability.
- No API keys or credentials are committed to the repo; they will be supplied
  via environment variables and referenced only from server-side code.

## 5. Data-quality and safety constraints

Across all external sources:

- Treat responses as untrusted; validate schemas, types, and plausible ranges
  before storing.
- Preserve original timestamps and distinguish `published_at`, `as_of`,
  `retrieved_at`, and `processed_at`.
- Avoid conflating multiple sources; when they disagree, store conflicting
  evidence rather than overwriting.

These principles support PSXviewAI's goal of auditable, evidence-backed
research rather than opaque AI guesses.
