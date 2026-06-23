# GCV CRM — Business Insights Report (corrected)

**Global Commercial Vehicles Inc. (GCV)** is a B2B manufacturer of commercial
vehicles (heavy-load, mining and specialty-storage trucks). This CRM data product
tracks the sales lifecycle: **Lead → Opportunity → Quote → Order → Invoice**.

This report supersedes the original course submission. The numbers below are
recomputed on the cleaned, re-normalised dataset; see
[`../docs/VERIFICATION.md`](../docs/VERIFICATION.md) for what changed and why.
Period: synthetic data, **2020–2022**, 10 UK cities.

> **Note on the original figures.** The original report overstated revenue by
> **1.60×** (£115.7M vs the true £72.4M) because line-item joins multiplied
> invoice totals, and its regional report could not resolve cities due to a broken
> foreign key. Both are fixed here.

---

## 1. Quarterly sales by vehicle type
Revenue attributed at line-item grain (`QuoteLineItem.total_price`).

![Quarterly revenue by vehicle type](figures/q1_quarterly_revenue_by_vehicle.png)

- **Mining Truck** leads revenue in most quarters; Heavy Load and Specialty
  Storage trade second place.
- Clear seasonality: Q2/Q4 peaks, softer Q1.

## 2. Territory sales leaderboard
Total invoiced revenue by shipping city (one invoice per order).

![Revenue by city](figures/q2_revenue_by_city.png)

| Rank | City | Orders | Revenue (£) | Avg order value (£) |
|---|---|---|---|---|
| 1 | Newcastle | 82 | 9,004,647 | 108,490 |
| 2 | Nottingham | 80 | 8,533,627 | 106,670 |
| 3 | Leicester | 80 | 8,143,554 | 100,538 |
| 4 | Leeds | 73 | 7,662,896 | 104,971 |
| 5 | London | 70 | 7,529,098 | 106,044 |

Total across all cities: **£72,358,475** (matches total invoiced revenue exactly).

## 3. Lead source effectiveness (win rate)

![Win rate by lead source](figures/q3_win_rate_by_source.png)

| Lead source | Leads | Won | Win rate | Avg score |
|---|---|---|---|---|
| Email | 77 | 24 | **31.2%** | 57.6 |
| Cold Call | 84 | 24 | 28.6% | 55.1 |
| Referral | 84 | 21 | 25.0% | 54.1 |
| Website | 77 | 18 | 23.4% | 53.7 |
| Social Media | 89 | 18 | 20.2% | 51.3 |
| Inquiry | 85 | 15 | 17.6% | 57.3 |

**Email** and **Cold Call** convert best; **Inquiry** has high volume but the
lowest win rate — a candidate for budget reallocation.

## 4. Average lead score by city

![Average lead score by city](figures/q4_avg_lead_score_by_city.png)

Birmingham, Manchester and Sheffield carry the highest-quality leads (avg score
60+); Newcastle is lowest (46.8) despite strong revenue — a quality-vs-volume gap.

## 5. Warranty mix
Gold (3,691 units) and Platinum (3,612) dominate over Silver (2,684) — customers
skew toward premium warranty tiers.

---

# Advanced analyses

These go beyond the core report and exercise window functions, CTEs, correlated
subqueries and date arithmetic. SQL in [`../sql/queries_advanced.sql`](../sql/queries_advanced.sql);
run with `python src/analysis_advanced.py`.

## A1. Sales-rep leaderboard — *revenue rank ≠ reward rank*
`RANK() OVER` + `SUM() OVER ()` for revenue share, plus estimated commission.

![Rep leaderboard](figures/a1_rep_leaderboard.png)

Riannon Gwioneth tops revenue (£5.64M, 7.8% of total) but **Becca Baugham ranks
#5 on revenue yet #1 on commission** — her commission rate more than offsets the
revenue gap. A pure-revenue leaderboard would misrepresent cost-to-serve.

## A2. Revenue concentration (Pareto)
Cumulative `SUM() OVER (ORDER BY revenue DESC)`.

![Pareto](figures/a2_pareto_accounts.png)

**~51% of accounts generate 80% of revenue** — less extreme than the classic
80/20, i.e. revenue is relatively broad-based rather than whale-dependent.

## A3. Sales funnel
CTE `VALUES` + `FIRST_VALUE`/`LAG`, measured at opportunity grain.

![Funnel](figures/a3_funnel.png)

| Stage | Count | % of leads |
|---|---|---|
| Leads | 497 | 100% |
| Opportunities | 496 | 99.8% |
| Quoted | 372 | 74.8% |
| Ordered | 371 | 74.6% |
| Invoiced | 371 | 74.6% |

The single drop-off is **Opportunity → Quote (~25% lost)**. Once a quote is
issued, conversion to order and invoice is essentially 100% — the bottleneck is
getting to a quote, not closing.

## A4. Does discounting buy wins? *(No.)*
CASE-bucketed discount bands vs win rate.

![Discount vs win rate](figures/a4_discount_winrate.png)

Win rate peaks at the **11–15% band (28.8%)** and *falls* for the deepest
**16–25% band (23.5%)** — over-discounting does not improve (and may erode) win
rates while sacrificing margin.

## A5. Sales-cycle length by lead source
`julianday()` date arithmetic, lead creation → order.

![Sales cycle](figures/a5_sales_cycle.png)

**Email closes fastest (~70 days); Inquiry slowest (~108)** — and Inquiry also
has the lowest win rate (§3). It is doubly inefficient.

## A6. Leads above their city average — correlated subquery
Each lead's score compared to the average of its own city. Surfaces standout
prospects in otherwise low-scoring territories (e.g. Newcastle's avg is 46.8, but
Renato Adami scores 100).

## A7. Payment behaviour / DSO by method
Overdue rate, average days-to-pay and late-fee burden.

![DSO by method](figures/a7_dso_by_method.png)

**Bearer checks** are slowest/most overdue (26.2% overdue, ~£242k late fees);
**Order checks** are cleanest (21.6%). A lever for tightening cash collection.

## A8. Pipeline aging — stuck deals
Opportunities still open whose expected close date has passed (as of latest data).

![Pipeline aging](figures/a8_pipeline_aging.png)

**£121M of pipeline is stale** (124 Prospecting + 114 Negotiation deals, ~1.5
years past expected close) — either dead deals inflating the forecast or a
follow-up gap.

---

*Reproduce: `python src/normalize.py && python src/build_db.py && python src/analysis.py && python src/analysis_advanced.py`*
