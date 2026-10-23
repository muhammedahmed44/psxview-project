# PSXviewAI

---

## Problem

Investors on the Pakistan Stock Exchange (PSX) have to follow filings, news, economic data, and sector developments across many separate sources. Generic AI tools rarely show where their answers come from, and beginners have no safe place to learn before risking real money.

| Problem | What goes wrong today |
|---|---|
| **Information overload** | Disclosures, news, and macro releases sit in different places, so important changes are easy to miss. |
| **Difficulty estimating fair value** | Value depends on growth, margins, discount rates, and multiples, and investors cannot see how each assumption moves the result. |
| **Complex financial reports** | Dense tables and jargon make period-to-period comparison slow and error-prone. |
| **Fragmented research workflow** | News, reports, valuation, and portfolio tracking live in separate tools, so events are not linked to the holdings they affect. |
| **Weak evidence in generic AI answers** | Answers lack source dates, excerpts, calculation details, and any split between fact and opinion. |
| **No safe way to learn** | Beginners go straight from reading about investing to using real money, with no guided practice and no feedback on how they decide. |

---

## Project

### Overview

PSXviewAI is an AI research assistant that turns scattered PSX information into a concise, evidence-backed view of three things:

1. **What happened?** The relevant company, sector, regulatory, and macroeconomic events.
2. **Why does it matter to my portfolio?** The transmission mechanism, the exposure of each holding, and the likely effect.
3. **What evidence supports that conclusion?** Sources, dates, excerpts, calculations, and limitations.

It is a research tool, not investment advice. It states what the evidence suggests and what would change the view.

### What sets it apart

- **Every material claim is traceable.** Each statement is tagged as a Fact, a Calculation, or an Interpretation, and linked to its source, publication date, retrieval time, and excerpt.
- **The language model never does the financial arithmetic.** Valuations, scenarios, and metrics come from tested, repeatable calculations with visible inputs and formulas.
- **Built for Pakistan.** It follows PSX disclosures, SBP and PBS releases, PKR and policy-rate effects, corporate actions, Shariah screening.
- **Learn first, then invest.** New users can access learner section to learn important terms about stocks and how stock market works.

### Target users

| User | Main need | What PSXviewAI provides |
|---|---|---|
| **Beginner investors** | Learn how investing works, and understand a company's position and valuation assumptions. | Important terms, how stock market works, company's actual fair valuation, financial performance |
| **Time-constrained investors** | Know quickly what matters for stocks they already hold. | A prioritized feed of news and report updates ranked by impact on their holdings. |
| **Long-term investors** | Track performance and notice when an investment thesis changes. | Period-over-period comparison, a thesis tracker, and alerts when new filings strengthen or weaken the thesis. |

### How it works (high level)

- Information from official filings, exchange announcements, reputable news, and economic releases is collected on a schedule and stored in a single evidence store.
- Answers are produced **only from stored evidence**, never from live outside lookups. Each answer carries a "knowledge as of" timestamp, so it can be reproduced and audited.
- A team of specialised AI roles handles news, financial analysis, valuation, macro context, verification, and writing the final answer. Each has one narrow job.
- A verification layer checks every material claim before the user sees it.

### The user journey

1. **Sign up** and receive a private, secure account space.
2. **Go live.** add real holdings and a watchlist, or start from a sample portfolio.
3. **Review the overview.** See holdings, relevant events, research coverage, and data freshness.
4. **Research a company.** Inspect metrics, valuation scenarios, and source evidence, or ask the assistant to summarise.
5. **Ask a question** about a company, event, valuation, or portfolio exposure.
6. **Get a verified answer** where every claim is checked against its source.
7. **Save and revisit.** Answers, sources, assumptions, and conversations are stored for later review.
8. **Get follow-up alerts** when a new filing or changed input affects a saved view.

### Scope

The final submission should deliver, fully functional end-to-end experience for a select  group of companies prioritizing depth and reliability over  broad but superficial coverage.

---

## Features

### 1. Learning Academy

- **Guided tutorial:** Section conting short blogs on stocks, risk, time horizons, diversification, fees, and how to read a PSXviewAI research view. Explanations are in simple English.

### 2. Portfolio and Watchlist Management

- Create portfolios and watchlists; record holdings, quantities, cost basis.
- Exposure by sector and by stock, with price timestamps.
- Strict separation of each user's data.

### 3. News and Event Monitoring

- Collects official filings, exchange disclosures, announcements, reputable news, and economic releases.
- Groups duplicate coverage into one event with multiple sources.
- Maps each event to the companies, sectors, and holdings it affects.
- Event cards show the impact mechanism, time horizon, evidence quality, and competing interpretations.
- Flags stale, conflicting, or low-confidence items.

### 4. Financial Report Analysis

- Reads reports into statements, tables, and key passages, and compares reporting periods.
- Summaries of revenue, margins, earnings, debt, and cash flow, each with page references.
- Extracted, derived, and interpreted values are kept clearly separate.
- Automatic checks, such as assets equalling liabilities plus equity and subtotals adding up.
- Users can correct an extracted number, and dependent calculations update.

### 5. Company Performance, Fair-Value and Scenario Analysis

- Compare current results with previous to track investment thesis. 
- A sector-appropriate valuation method is chosen and explained:
  - Stable cash generators (e.g. fertilizer, cement): discounted cash flow.
  - Banks: price-to-book against return on equity, or residual income.
  - Cyclicals (e.g. oil and gas, steel): multiples on normalised earnings.
- Bear, base, and bull scenarios with visible assumptions.
- Sensitivity table, a chart showing which assumption matters most, and a reverse valuation answering "what growth does the current price imply?"
- Every input is labelled "from filing", "user override", or "analyst assumption", with its source date.

### 6. Conversational Research Assistant

- Answers questions such as "Why did my portfolio risk change?" or "What could weaken this company's thesis?"
- Concise answers with claims, sources, timestamps, assumptions, and uncertainty.
- Saved conversations for later review.
- Declines to answer when evidence is missing, for example: "I do not have a filing from this period."

### 7. Evidence and Verification Layer

- Every material claim is stored with its source, publication date, retrieval time, excerpt, and status.
- **Claim types:** Fact (from a source), Calculation (from tested code), Interpretation (the model's reasoning).
- **Verification status:** supported, partially supported, unsupported, stale, or conflicting. When sources disagree, both are shown side by side.
- **Source ranking:** official filings, then exchange notices, then reputable news, then aggregators.
- **Confidence labels:** low, medium, or high evidence quality. These are guides and not guarantees.
- A "How this answer was produced" panel shows the sources and steps behind each answer.

### 8. Alerts and Research Briefs

- Events ranked by portfolio relevance and materiality, how they can impact the portfolio.
- In-app alerts for filings, earnings changes, valuation updates, and thesis-relevant developments.
- Periodic briefs that flag stale or incomplete inputs.

### 9. Thesis Tracking

- Save an investment thesis with measurable indicators.
- Get alerted when new filings strengthen or weaken it.

### 10. Pakistan Market Focus

- **Local sources:** PSX announcements, SECP, State Bank of Pakistan (policy rate and monetary policy statements), Pakistan Bureau of Statistics (CPI), and budget and IMF-program news.
- **Macro transmission:** Effects explained in terms local investors recognise, such as policy rate on banks, PKR/USD on importers and exporters, oil and gas prices on marketing, power, and fertilizer companies, and circular debt in the energy chain.
- **Corporate-action adjustment:** Bonus shares, rights issues, dividends, and book closures are applied before returns, EPS, or valuation are computed.

### 11. Responsible AI, Security, and Trust

- **Research, not advice:** The assistant states what the evidence suggests and what would change the view.
- **Explicit uncertainty:** Evidence quality is labelled with a plain explanation.
- **Account security:** Secure sign-in with two-factor authentication, and each user can only see their own data.
- **Injection resistance:** Scraped news and document text is treated as untrusted data and never as instructions.
- **Auditability:** Every AI run logs the tools used, sources retrieved, and outputs produced.
- **Cost control:** Per-user usage limits, and repeated requests reuse saved results.
- **Data provenance:** Duplicate evidence is prevented, and company names (tickers, subsidiaries) map to one company record.

---

## Expected Impact

Investors spend less time collecting information and more time judging it. They can see the assumptions behind a valuation. They dont need to track every news. The claim is not that AI can predict the market. It is that an investor can see what happened, why it may matter, and exactly how well the evidence supports each statement.
