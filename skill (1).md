---
name: psxviewai-development
description: >
  On-demand implementation workflows for the PSXviewAI evidence-backed Pakistan Stock
  Exchange research application. Use when implementing ingestion jobs, financial
  statement extraction, valuation calculators, stored-evidence research, APIs,
  portfolio features, verification, testing, or deployment. Consult SPEC.md for
  product requirements and AGENTS.md for repository-wide coding conduct.
---

# PSXviewAI Development Skill

This is a **technical how-to guide**, not a competing specification. `SPEC.md` owns all 11 features, their priority and acceptance criteria. `AGENTS.md` owns coding-agent operating rules. Use only the procedure relevant to the current task. A 48-hour demo may prioritize features using `SPEC.md`'s P0/P1/P2 addendum, but **must not silently redefine P1/P2 features as forbidden or out of scope forever**.

## 1. Implementation strategy and boundaries

**Build in vertical slices:** one supported company and a complete data → storage → API → UI path first; then extend to the selected 2–3-company demo universe from `SPEC.md`. More companies can be added only when they have legitimate, dated evidence and tested metrics. The originally uploaded skill's “5–10 companies” is an optional later expansion, not a hard MVP requirement.

**Preferred technical defaults, only if the repository has not already settled them:**

| Layer | Preferred starting point | Reason |
|---|---|---|
| UI | React + TypeScript + Vite + Tailwind; Recharts where it materially helps | Simple typed dashboard |
| Backend | Python + FastAPI + Pydantic + SQLAlchemy | Typed APIs and testable financial logic |
| Structured and vector data | PostgreSQL + pgvector | A single database can store exact metrics and searchable evidence |
| Financial document parsing | LlamaParse behind a `DocumentParser` adapter | Replaceable PDF extraction; requires valid access/credentials |
| LLM and embeddings | One permitted hosted model and one consistent embedding model behind adapters | Reuse models for logical roles; avoid provider lock-in |
| Original files | Local/object storage with stable IDs; R2 only if suitable | Preserve official PDFs and parsed artifacts |
| Hosting | Compatible frontend/static host + Python backend + managed PostgreSQL | Minimize operational complexity |

Do not migrate an established working stack simply to match these defaults. Confirm provider data rights, current model availability, quotas and deployment limits before relying on them. **No trading, execution, or broker integration is added by this skill.**

## 2. Application roles versus backend jobs

`SPEC.md` defines six **logical research roles**: **News & Events, Financial Reports, Valuation, Macro Impact, Verification, Synthesis**. Treat these as prompt/tool responsibilities selected by a lightweight **code router**. They may share one LLM provider and do not require independent services or unconstrained agent-to-agent conversation.

The following are **not additional conversational agents**; they are deterministic or scheduled components:

- **Market-data ingestion job:** fetch, normalize and timestamp source market snapshots.
- **News ingestion job:** collect approved source items, deduplicate, classify/link events and store retrievable evidence.
- **Report ingestion job:** download, parse, validate and store filing evidence and exact financial metrics.
- **Finance/valuation service:** pure functions computing valuation, ratios, corporate-action effects and exposure.
- **Retrieval and verification services:** company-scoped evidence lookups and machine-checkable validation before final synthesis.

**Technical routing pattern:** request → decide whether lookup/calculation is sufficient → retrieve stored records and run deterministic tools → invoke only needed research role(s) → check citations, units, periods and support → synthesize approved answer. Do **not** run every role on every request. Scheduled ingestion is outside the request path.

## 3. Repository and contracts

Use the existing structure if present. Suggested locations for a new repo:

```text
frontend/src/{pages,components,services,types}/
backend/app/{api,models,schemas,db,services,ingestion,parsers,retrieval,valuation,research}/
backend/tests/
scripts/
docs/
.env.example
SPEC.md
AGENTS.md
skill.md
```

Create typed API response models early. Prefer a consistent error shape (`code`, `message`, optional `details`) and shared frontend types. Implement the conceptual records and provenance fields defined in `SPEC.md` instead of inventing a second competing schema in this file.

**Storage responsibilities:**

- PostgreSQL is authoritative for company identities, holdings, timestamps, numeric financial metrics, input overrides, valuation runs, extracted evidence metadata, claims and user-specific features.
- pgvector finds relevant narrative and table context; its similarity score is **not** an authoritative numeric source. Fetch exact EPS, revenue, price, debt or valuation from structured records.
- Original documents retain a stable document ID, source URL/reference, document checksum, publisher, publication date, retrieval time, reporting period and page/section mappings where available.
- Record ownership and authorization relationships for portfolios, conversations, theses, alerts and saved research responses.

Use database migrations for schema changes. Preserve exact units (`PKR`, `PKR million`, shares, per-share), fiscal/quarterly periods and data origins. Never conflate *published at*, *market timestamp*, *retrieved at*, and *processed at*.

**Initial API surface:** adjust names to established API contracts if they exist.

```text
GET    /api/companies
GET    /api/stocks/{ticker}/overview
GET    /api/stocks/{ticker}/financials
GET    /api/stocks/{ticker}/valuation
GET    /api/stocks/{ticker}/news
POST   /api/chat

# Add as corresponding SPEC features are implemented:
GET/POST /api/portfolios
GET/POST /api/portfolios/{id}/holdings
GET/POST /api/watchlist
GET     /api/alerts
GET/POST /api/theses
GET     /api/conversations
```

Use Pydantic models for payloads. Add authorization to user-specific routes. Treat admin ingestion triggers as privileged operations.

## 4. Market-data ingestion procedure

1. Select a legitimate data source and document whether quotes are delayed or end-of-day; record licensing and API restrictions.
2. Map symbol aliases to a unique company ID; validate price, previous close, currency, price change, volume and *market* timestamp.
3. Upsert daily/latest snapshots idempotently using stable company/source/timestamp keys. Preserve `retrieved_at` separately.
4. Serve a latest **available** snapshot via API, including explicit stale/unavailable states; do not imply live pricing.
5. Display timestamp, provenance and market freshness on the dashboard and holding views.

**When scheduling is built:** run the market job once after the market closes on a **PSX trading day**, using the correct trading calendar and `Asia/Karachi` timezone. Avoid continuous polling or fake updates on market holidays. During the hackathon an explicit admin-trigger or preingested, clearly timestamped authentic snapshot can support the demo if automatic scheduling is not yet implemented; mark scheduler work pending against `SPEC.md`.

## 5. News, macro and event ingestion procedure

1. Configure approved source adapters, prioritizing official company filings/exchange notices, regulators (PSX/SECP/SBP/PBS), then reputable business news.
2. Store a source item with publisher, URL, publication/retrieval dates, lawful excerpt/summary, checksum and relevant document/source ID; respect copyright, robots and provider terms.
3. Deduplicate by source ID/URL/content hash and group reports of the same event without dropping alternative viewpoints.
4. Map companies and sectors via ticker, official name, aliases, subsidiaries and sector tags; ambiguous mappings require corroboration or an uncertainty label.
5. Determine relevance/impact mechanism, time horizon and `positive | negative | mixed | uncertain` classification. Preserve competing interpretations and underlying source IDs.
6. Store searchable text/chunks with `company_id`, `event_id`, `source_id`, `published_at` and `knowledge_as_of` filtering metadata.
7. Compare new events with holdings and saved theses **only when** those features have been implemented, then generate real stored alerts/briefs from changed records.

**When scheduling is built:** news ingestion runs **three times daily** with configurable times, not when a chatbot question arrives. Persist job start/finish/status, counts, errors and last successful run. Ingestion must be retryable and idempotent.

## 6. Financial-report ingestion procedure

1. Download an official annual/quarterly report for a supported PSX company; store the original PDF, URL, issuer, filing period and checksum.
2. Parse through `DocumentParser.parse(file) -> ParsedDocument`. Use **LlamaParse** as the preferred implementation from the uploaded skill; keep the adapter so provider outages do not force architecture changes.
3. Preserve page/section references with extracted text, tables and statement rows. Flag missing tables or failed parsing rather than guessing values.
4. Extract income statement, balance sheet and cash flow rows into normalized structured records; retain raw extracted strings as well as verified numeric values.
5. Verify currency/scaling, negative signs, annual versus quarter versus YTD period, EPS basis, total/subtotal arithmetic and assets ≈ liabilities + equity.
6. Store exact values with evidence IDs, report page, unit, covered period, extraction status and origin; reject/flag unreconciled values.
7. Chunk narrative sections and relevant table explanations, embed each version once, and attach provenance metadata.
8. If a source value is corrected by the user, store an attributed override, preserve the original, and re-run only dependent deterministic outputs.

**When scheduling is built:** check for new/changed reports **once daily**, process only unseen or changed documents, and prevent duplicate re-parsing. During the initial demo, processing selected authentic PDFs manually through the same pipeline is valid as an implementation milestone, not evidence that the scheduled job is live.

## 7. Finance and valuation workflow

Keep the valuation service callable without an LLM. The research **Valuation role** explains these outputs; it never substitutes its own numeric guesses.

1. Choose a company/sector-appropriate method consistent with `SPEC.md` (e.g., DCF for suitable stable cash generators, price-to-book/residual income for banks, normalized multiples for cyclicals).
2. Build typed `ValuationInputs` carrying source metric IDs, reporting periods, currency, units and assumption provenance (`from_filing`, `user_override`, `analyst_assumption`).
3. Implement pure, versioned Python functions for the selected method plus **bear, base and bull** scenarios. Build sensitivity/reverse valuation only at the `SPEC.md` priority assigned to those features.
4. Use an exact numeric type or an explicit rounding policy for PKR/per-share precision. Guard against division by zero, missing inputs, currency mismatches, extreme assumptions and irrelevant sector formulas.
5. Compute comparable upside/downside using the latest **available** price (with time and corporate-action context):

   `((estimated_fair_value - reference_market_price) / reference_market_price) * 100`

6. Apply dividends/bonus/rights/splits and other applicable adjustments **before** comparing per-share amounts or returns; preserve the adjustment event source.
7. Store input IDs, assumptions, method/version, outputs, source/market dates, limitations and calculation receipt; connect recalculation to changed verified inputs.
8. Unit-test known cases, boundaries and identical-input determinism before connecting charts/UX.

**User-facing wording:** *Estimated Fair Value*, with method, assumptions, valuation date and uncertainty. Never use “actual value” or imply a guaranteed outcome. If a method lacks verified inputs, show “unavailable” with a reason rather than fabricating numbers.

## 8. Stored-evidence RAG, application roles and verification

1. **Scope:** accept a selected company/holding/portfolio and a `knowledge_as_of` time. Reject unauthorized portfolio context.
2. **Route:** recognize exact-metric questions (SQL first), document interpretation, event impact, macro impact and valuation explanation. Skip unnecessary roles/tools.
3. **Retrieve:** apply company/source/time filters before or alongside pgvector similarity; retrieve stored report chunks, structured metrics, dated event evidence and saved valuation receipts. Do not retrieve outside sources in this path.
4. **Draft structured claims:** each claim identifies `fact | calculation | interpretation` and its exact evidence IDs and/or calculation IDs, source period and relevance.
5. **Verify:** check company match, support, quote accuracy, dates, unit and period consistency, stale data and conflicts. Use `supported | partially_supported | unsupported | stale | conflicting`; block unsupported numerical/factual assertions.
6. **Synthesize:** present a clear answer followed by evidence, mechanism/interpretation and limitations, showing `knowledge_as_of` and source dates. Interpretations must be labelled as interpretations rather than converted into factual certainty.
7. **Persist when implemented:** save conversation/answer, references, run ID and user owner only through authorized routes.

Example minimal output envelope (adapt names to actual contracts):

```json
{
  "answer": "...",
  "knowledge_as_of": "ISO-8601 timestamp",
  "claims": [
    {
      "type": "fact",
      "status": "supported",
      "evidence_ids": ["evidence-id"],
      "calculation_ids": []
    }
  ],
  "limitations": [],
  "run_id": "id"
}
```

**Test negative paths:** wrong-company matches, a question about an unavailable period, contradictory filings, stale prices, missing numerical sources, malicious instructions inside parsed reports, and unapproved cross-user holdings. Expected behavior is a safe evidence-gap or conflicting-evidence response, not a plausible fabricated answer.

## 9. UI and complete feature integration

Implement pages/components by the **feature matrix in `SPEC.md`**, rather than treating the old skill's “four pages only” as an exclusion of other features. For a reliable first slice, connect:

```text
Auth/demo isolation -> portfolio/holdings/watchlist -> company overview
-> sourced metrics + dated events -> deterministic scenarios
-> stock/portfolio question -> verified evidence panel
```

Wire education, saved research, alerts and thesis tracking at their assigned `SPEC.md` priorities. These are not prohibited; they are separate implementations with their own acceptance tests. Mark unimplemented UI entry points honestly, or hide them until functional. The source/evidence drawer should navigate to the actual document/page or licensed article URL; display a limitation when a reference cannot be opened.

At UI level, implement loading/error/empty/stale states; clear PKR units and source periods; distinguish price changes from valuation upside; avoid color-only meaning. Prefer simple research cards and measured charts over trading-terminal controls.

## 10. Vertical-slice execution checklist (48 hours)

Use this as a dependency order, **not as human task allocation**. `SPEC.md` determines actual P0/P1/P2 acceptance; do not silently demote any requirement.

| Stage | Build and inspect | Exit check |
|---|---|---|
| A. Foundations | Existing repo check, approved sources, schemas, auth/demo isolation, company IDs, API client | UI and API start; user data scopes work |
| B. Trustworthy company data | One authentic company report + market snapshot + dated events | Page renders sourced values, periods and freshness |
| C. Financial outputs | Deterministic bear/base/bull valuation and holding exposure | Known-value tests pass; assumptions visible |
| D. Research answer | Company/portfolio-scoped retrieval, role routing, claim checks, evidence drawer | Prepared questions return sourced answers; unknowns fail safely |
| E. Feature coverage | Learning content and remaining P0 items, then P1 features from SPEC | Updated feature matrix records completed/partial/missing accurately |
| F. Integration/release | Source audit, regression tests, deployment, documented dated local fallback | Demo reproduces the same verifiable walkthrough |

Do not implement many ingestion services and agents in isolation before connecting one company end to end. Record blockers (access, parser, source mismatch, financial ambiguity) in a short issue/status note.

## 11. Focused testing recipes

**Unit tests:** valuation math and scenario ordering; conversion between PKR and PKR million; zero/negative inputs; price adjustment events; portfolio exposure; event deduplication; alias-to-company mapping; formatting and input validation.

**Integration tests:** official report → source/pages/structured metrics; new article → stored event/chunks; calculation inputs → persisted receipt; stored evidence → cited response; holdings → overview; user A cannot read user B's records.

**RAG and safety tests:** quote matches excerpt, company filter, stale/date flags, contradictory sources, missing filing period, forged instructions in PDFs, unsupported claims refused/flagged, and actual calculated numbers equal tool output.

**Manual end-to-end demonstration:** sign in/open isolated demo → add/edit PSX holdings → examine timestamped stock data → inspect period financials → modify a valuation assumption → read relevant event → ask a question → open supporting evidence → visit an educational lesson. Where P1 features are implemented, verify saved chats, alerts and thesis updates too.

Run only applicable tests during a focused task; before final submission run the broader suite and test on the deployed URL. Report only checks that actually executed.

## 12. Operational workflow

**Environment:** use `.env.example` listing required keys (`DATABASE_URL`, parser key, LLM key, optional provider keys and object-storage settings). Never place secrets in frontend bundles. Implement bounded retries, timeouts, rate limits and source-adapter error statuses.

**Job telemetry:** record job name, source, company, started/completed timestamps, items found/stored/skipped, last success, and error; use idempotency keys. For research, store run/model/tool/evidence IDs, latency, status and `knowledge_as_of` without logging confidential queries unnecessarily.

**Deployment:** migrate database → provision vector capability/storage → configure backend secrets → seed or ingest *authentic* dated evidence → deploy backend → deploy frontend → verify origins/auth → optionally enable approved ingestion schedules → run public-URL smoke test. Check live provider limits and data licensing before claiming full automation.

**Offline demo fallback:** package permitted, authentic, cited, **dated** source snapshots and already verified calculation receipts, load via the same schemas, and visibly indicate snapshot age. A fallback is not permission to invent PSX prices/news or claim live ingestion succeeded.

**Final status:** use `SPEC.md`'s feature matrix to label every feature complete, partial or not started. This skill guides implementation; it cannot change the success criteria on its own.
