# Verification & Data-Quality Findings

This document records what was wrong with the original submission and how it was
fixed. The original raw export is preserved under `data/raw/`; the cleaned,
re-normalised dataset is in `data/clean/` and is rebuilt by the scripts in `src/`.

## How it was verified

The repository CSVs were loaded into SQLite and every report query was re-run.
The decisive step was enabling **`PRAGMA foreign_keys = ON`** — which the original
pipeline never did during data import (it opened a fresh connection and SQLite
defaults the pragma to OFF). With enforcement on, the hidden defects surfaced.

## Defects found

### 1. Foreign-key enforcement was never active
The loader created the schema in one connection, closed it, then re-opened a new
connection to import CSVs without re-enabling `foreign_keys`. All referential
integrity checks were silently skipped, so broken references loaded without error.
With enforcement on, **1,160 orphan references** were exposed.

### 2. Lookup tables were not normalised (despite the report claiming 3NF)
Every "lookup" table stored **one row per occurrence** instead of one row per
distinct value:

| Table | Raw rows | Distinct values |
|---|---|---|
| Warranty | 1,000 | 3 |
| QuoteStatus / PaymentMethod / OrderStatus | 700 each | 3–4 |
| LeadSource / LeadStatus / LostReason / Stage | 500 each | 3–6 |
| ShippingCity | 700 | 10 |
| BillingCity | 200 | 10 |
| Industry | 200 | 5 |
| JobTitle | 500 | 9 |

**Fix:** each lookup was deduplicated to its distinct values and every foreign key
re-pointed. Billing/Shipping city were merged into a single `City` dimension.

### 3. Broken foreign keys
- **ShippingAddress → ShippingCity (700/700 broken):** `shipping_city_id` used a
  `CIT` prefix while `ShippingCity` ids are `SCT` (same numeric suffix). This
  collapsed the **Territory Sales Leaderboard** to a single `NULL` city.
  **Fix:** `CIT→SCT` prefix correction recovered all 700.
- **Customer → JobTitle (451/500 broken):** `job_title_id` ran JOB00002–JOB00500
  (≈ one per customer) but only 50 lookup rows / 9 titles existed.
  **Fix:** 49 genuine references kept; the rest assigned deterministically.

### 4. Duplicate primary keys
Entity tables carried duplicate PKs that the original `INSERT OR REPLACE` silently
collapsed: Account ×1, Customer ×1, Lead ×3, Opportunity ×4, Quote ×3, Orders ×2,
Invoice ×3, QuoteLineItem ×7. **Fix:** deduplicated (keep last).

### 5. Schema / null-handling issues
- `Product.product_name VARCHA(50)` typo → `VARCHAR(50)`.
- `Quote.expiration_date` was `NOT NULL`, but the spec says only revised quotes
  have an expiry (366/697 are empty) → relaxed to nullable.
- Open opportunities / undelivered orders stored the string `'Na'` for dates →
  converted to real `NULL`.
- A few fully-blank rows (1 Opportunity, 1 Invoice) were dropped.

### 6. Analytical bug — revenue double-counted (most important)
Q1 and Q2 joined `QuoteLineItem` and then summed `Invoice.total_amount`. Because
296 of 695 quotes have ≥2 line items, the invoice total was multiplied by the
number of lines.

| Metric | Reported (buggy) | Correct |
|---|---|---|
| Total revenue | £115,702,403 | **£72,358,475** |
| Inflation | **1.60× (+£43.3M)** | — |

**Fix:** revenue-by-vehicle now uses `QuoteLineItem.total_price` (correct grain);
revenue-by-city uses one invoice per order. The corrected per-city revenue sums
**exactly** to the true invoice total — a referential-integrity cross-check.

### 7. Missing query
The report described a "Lead Source Effectiveness" query with no corresponding
code. It is implemented in `sql/queries.sql` as **win rate by lead source**
(every lead becomes an opportunity here, so conversion-to-opportunity is trivially
100%; win rate is the meaningful metric).

## Result
The cleaned dataset loads with **full FK enforcement and zero violations** across
27 tables, and all five business queries run correctly.
