# GCV CRM — SQL Data Product

A relational CRM data product for a fictional commercial-vehicle manufacturer,
**Global Commercial Vehicles Inc. (GCV)**. It models the full B2B sales lifecycle
— **Lead → Opportunity → Quote → Order → Invoice** — over synthetic 2020–2022 data
across 10 UK cities, and generates business-insight reports in SQL.

> Originally a master's Data Management group project. This version has been
> **audited, re-normalised, and corrected** — see
> [`docs/VERIFICATION.md`](docs/VERIFICATION.md) for the full data-quality review.

## What was fixed
- **Referential integrity:** the original never enforced foreign keys, hiding
  1,160 orphan references (incl. a 100%-broken shipping-city link). The clean
  dataset loads with **FK enforcement on and zero violations**.
- **Normalisation:** 16 "lookup" tables stored one row per occurrence instead of
  per distinct value. They are now proper dimensions (e.g. Warranty 1,000 → 3).
- **Analytics:** revenue was double-counted **1.60×** by line-item joins
  (£115.7M → true **£72.4M**); queries corrected.

## Repository layout
```
GCV_SQL_Project/
├── data/
│   ├── raw/      # original export (preserved, as-submitted)
│   └── clean/    # re-normalised, FK-valid dataset (generated)
├── sql/
│   ├── schema.sql    # clean 3NF DDL (FK enforced)
│   └── queries.sql   # corrected business queries
├── src/
│   ├── normalize.py  # raw  -> clean  (dedupe lookups, fix FKs, drop bad rows)
│   ├── build_db.py   # clean -> CRM.db (loads with FK enforcement, verifies)
│   └── analysis.py   # runs queries + saves charts
├── reports/
│   ├── REPORT.md     # corrected insights write-up
│   └── figures/      # generated charts
└── docs/
    └── VERIFICATION.md
```

## Quick start
```bash
pip install -r requirements.txt
python src/normalize.py    # data/raw -> data/clean
python src/build_db.py     # build CRM.db (prints "Foreign-key check: PASS")
python src/analysis.py     # print results + write reports/figures/*.png
```

## Data model
A star-style schema: 15 dimension tables + a unified `City` dimension feed the
core entities (Account, Customer, Lead, Opportunity, Quote, QuoteLineItem, Order,
Invoice, Product, Users). Keys are `CHAR(8)` (3-letter table code + 5-digit
sequence). Full DDL in [`sql/schema.sql`](sql/schema.sql); ER diagram in
[`docs/erd.md`](docs/erd.md) (and [`ERD.png`](ERD.png)).

![ERD](ERD.png)

## Business questions answered
1. Quarterly sales & revenue by vehicle type
2. Territory sales leaderboard (revenue by city)
3. Lead source effectiveness (win rate)
4. Average lead score by city
5. Warranty mix

*Stack: Python (pandas, matplotlib) + SQLite.*
