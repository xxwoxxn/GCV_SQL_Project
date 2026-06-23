#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Advanced analytical queries (window fns, CTEs, correlated subqueries,
date math). Prints results and saves charts to reports/figures/."""
import os, sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "CRM.db")
FIG = os.path.join(HERE, "..", "reports", "figures")
os.makedirs(FIG, exist_ok=True)
conn = sqlite3.connect(DB)
def q(sql): return pd.read_sql_query(sql, conn)
def show(t, df): print("\n" + "=" * 66 + "\n" + t + "\n" + "-" * 66); print(df.to_string(index=False))
def save(name): plt.tight_layout(); plt.savefig(os.path.join(FIG, name), dpi=120); plt.close()

# A1. Rep leaderboard ---------------------------------------------------
a1 = q("""
WITH rep AS (
 SELECT u.user_name, CAST(u.commission_rate AS REAL) comm,
   COUNT(DISTINCT o.order_id) deals, SUM(i.total_amount) revenue
 FROM Users u JOIN Opportunity opp ON opp.user_id=u.user_id
 JOIN Quote q ON q.opportunity_id=opp.opportunity_id
 JOIN Orders o ON o.quote_id=q.quote_id JOIN Invoice i ON i.order_id=o.order_id
 GROUP BY u.user_id)
SELECT user_name, deals, revenue,
  RANK() OVER (ORDER BY revenue DESC) revenue_rank,
  ROUND(100.0*revenue/SUM(revenue) OVER(),1) pct_of_total,
  ROUND(revenue*comm/100.0,0) est_commission,
  RANK() OVER (ORDER BY revenue*comm DESC) commission_rank
FROM rep ORDER BY revenue_rank;""")
show("A1. Sales-rep leaderboard (RANK / SUM OVER)", a1.head(10))
top = a1.head(10)
ax = top.plot(kind="barh", x="user_name", y="revenue", legend=False, figsize=(10, 5.5), color="#2a7ab9")
ax.invert_yaxis(); ax.set_title("Top 10 Sales Reps by Invoiced Revenue"); ax.set_xlabel("Revenue (GBP)"); ax.set_ylabel("")
save("a1_rep_leaderboard.png")

# A2. Pareto ------------------------------------------------------------
a2 = q("""
WITH acct_rev AS (
 SELECT a.account_id, SUM(i.total_amount) rev
 FROM Invoice i JOIN Orders o ON i.order_id=o.order_id
 JOIN Quote q ON o.quote_id=q.quote_id JOIN Opportunity opp ON q.opportunity_id=opp.opportunity_id
 JOIN Customer c ON opp.customer_id=c.customer_id JOIN Account a ON c.account_id=a.account_id
 GROUP BY a.account_id)
SELECT ROW_NUMBER() OVER (ORDER BY rev DESC) rank,
  ROUND(100.0*ROW_NUMBER() OVER (ORDER BY rev DESC)/COUNT(*) OVER(),1) pct_accounts,
  ROUND(100.0*SUM(rev) OVER (ORDER BY rev DESC)/SUM(rev) OVER(),1) pct_revenue_cum
FROM acct_rev ORDER BY rank;""")
cross = a2[a2.pct_revenue_cum >= 80].iloc[0]
show("A2. Pareto (cumulative SUM OVER) - 80pct revenue point", pd.DataFrame([cross]))
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot(a2.pct_accounts, a2.pct_revenue_cum, color="#2a7ab9", lw=2)
ax.axhline(80, color="#cc4444", ls="--", lw=1); ax.axvline(cross.pct_accounts, color="#cc4444", ls="--", lw=1)
ax.set_title("Revenue Concentration (Pareto)"); ax.set_xlabel("Cumulative % of accounts"); ax.set_ylabel("Cumulative % of revenue")
ax.grid(alpha=0.3); save("a2_pareto_accounts.png")

# A3. Funnel ------------------------------------------------------------
a3 = q("""
WITH funnel(step,stage_name,cnt) AS (VALUES
  (1,'Leads',(SELECT COUNT(DISTINCT lead_id) FROM Lead)),
  (2,'Opportunities',(SELECT COUNT(DISTINCT opportunity_id) FROM Opportunity)),
  (3,'Quoted',(SELECT COUNT(DISTINCT opportunity_id) FROM Quote)),
  (4,'Ordered',(SELECT COUNT(DISTINCT q.opportunity_id) FROM Quote q JOIN Orders o ON o.quote_id=q.quote_id)),
  (5,'Invoiced',(SELECT COUNT(DISTINCT q.opportunity_id) FROM Quote q JOIN Orders o ON o.quote_id=q.quote_id JOIN Invoice i ON i.order_id=o.order_id)))
SELECT stage_name, cnt,
  ROUND(100.0*cnt/FIRST_VALUE(cnt) OVER(ORDER BY step),1) pct_of_leads,
  ROUND(100.0*cnt/LAG(cnt) OVER(ORDER BY step),1) step_conversion
FROM funnel ORDER BY step;""")
show("A3. Sales funnel (CTE VALUES + FIRST_VALUE/LAG)", a3)
ax = a3.plot(kind="barh", x="stage_name", y="cnt", legend=False, figsize=(9, 4.5), color="#4c7fb0")
ax.invert_yaxis(); ax.set_title("Sales Funnel (opportunity grain)"); ax.set_xlabel("Count"); ax.set_ylabel("")
for i, v in enumerate(a3.cnt): ax.text(v + 3, i, "%d (%.0f%%)" % (v, a3.pct_of_leads[i]), va="center", fontsize=9)
save("a3_funnel.png")

# A4. Discount band -----------------------------------------------------
a4 = q("""
WITH od AS (SELECT opp.opportunity_id, MAX(q.discount) d,
   MAX(CASE WHEN s.stage='Won' THEN 1 ELSE 0 END) won
 FROM Opportunity opp JOIN Stage s ON opp.stage_id=s.stage_id
 JOIN Quote q ON q.opportunity_id=opp.opportunity_id GROUP BY opp.opportunity_id)
SELECT CASE WHEN d<=5 THEN '0-5%' WHEN d<=10 THEN '6-10%' WHEN d<=15 THEN '11-15%' ELSE '16-25%' END band,
  COUNT(*) opportunities, SUM(won) won, ROUND(100.0*SUM(won)/COUNT(*),1) win_rate_pct
FROM od GROUP BY band;""")
order = ["0-5%", "6-10%", "11-15%", "16-25%"]
a4 = a4.set_index("band").loc[order].reset_index()
show("A4. Win rate by discount band (CASE + CTE)", a4)
ax = a4.plot(kind="bar", x="band", y="win_rate_pct", legend=False, figsize=(8, 5), color="#e07b39")
ax.set_title("Win Rate by Discount Band"); ax.set_ylabel("Win rate (%)"); ax.set_xlabel("Discount band")
plt.xticks(rotation=0); save("a4_discount_winrate.png")

# A5. Sales cycle -------------------------------------------------------
a5 = q("""
SELECT ls.lead_source, COUNT(*) deals,
  ROUND(AVG(julianday(o.order_date)-julianday(l.created_date)),0) avg_cycle_days
FROM Lead l JOIN LeadSource ls ON l.lead_source_id=ls.lead_source_id
JOIN Opportunity opp ON opp.lead_id=l.lead_id JOIN Quote q ON q.opportunity_id=opp.opportunity_id
JOIN Orders o ON o.quote_id=q.quote_id GROUP BY ls.lead_source ORDER BY avg_cycle_days;""")
show("A5. Sales-cycle length by lead source (date math)", a5)
ax = a5.plot(kind="bar", x="lead_source", y="avg_cycle_days", legend=False, figsize=(9, 5), color="#7a5ea8")
ax.set_title("Avg Sales-Cycle Days by Lead Source"); ax.set_ylabel("Days"); ax.set_xlabel("")
plt.xticks(rotation=30, ha="right"); save("a5_sales_cycle.png")

# A6. Correlated subquery (table only) ----------------------------------
a6 = q("""
SELECT ct.city_name, c.customer_name, l.lead_score,
 (SELECT ROUND(AVG(l2.lead_score),1) FROM Lead l2
   JOIN Customer c2 ON l2.customer_id=c2.customer_id JOIN Account a2 ON c2.account_id=a2.account_id
   JOIN BillingAddress b2 ON a2.billing_address_id=b2.billing_address_id WHERE b2.city_id=ba.city_id) city_avg_score
FROM Lead l JOIN Customer c ON l.customer_id=c.customer_id JOIN Account a ON c.account_id=a.account_id
JOIN BillingAddress ba ON a.billing_address_id=ba.billing_address_id JOIN City ct ON ba.city_id=ct.city_id
WHERE l.lead_score > (SELECT AVG(l2.lead_score) FROM Lead l2
   JOIN Customer c2 ON l2.customer_id=c2.customer_id JOIN Account a2 ON c2.account_id=a2.account_id
   JOIN BillingAddress b2 ON a2.billing_address_id=b2.billing_address_id WHERE b2.city_id=ba.city_id)
ORDER BY (l.lead_score-city_avg_score) DESC LIMIT 10;""")
show("A6. Leads above their city average (correlated subquery)", a6)

# A7. DSO ---------------------------------------------------------------
a7 = q("""
SELECT pm.payment_method, COUNT(*) paid_invoices,
  ROUND(100.0*SUM(CASE WHEN julianday(i.payment_date)>julianday(i.due_date) THEN 1 ELSE 0 END)/COUNT(*),1) overdue_pct,
  ROUND(AVG(julianday(i.payment_date)-julianday(i.invoice_date)),0) avg_days_to_pay,
  ROUND(SUM(i.late_fees),0) total_late_fees
FROM Invoice i JOIN PaymentMethod pm ON i.payment_method_id=pm.payment_method_id
WHERE i.payment_date IS NOT NULL AND i.payment_date<>'' GROUP BY pm.payment_method ORDER BY overdue_pct DESC;""")
show("A7. Payment behaviour / DSO by method (date math)", a7)
ax = a7.plot(kind="bar", x="payment_method", y="overdue_pct", legend=False, figsize=(9, 5), color="#c0563b")
ax.set_title("Overdue Rate by Payment Method"); ax.set_ylabel("Overdue (%)"); ax.set_xlabel("")
plt.xticks(rotation=20, ha="right"); save("a7_dso_by_method.png")

# A8. Pipeline aging ----------------------------------------------------
a8 = q("""
WITH asof AS (SELECT MAX(order_date) d FROM Orders),
oo AS (SELECT s.stage, opp.opportunity_amount,
   julianday((SELECT d FROM asof))-julianday(opp.expected_close_date) days_over
 FROM Opportunity opp JOIN Stage s ON opp.stage_id=s.stage_id
 WHERE s.stage IN ('Prospecting','Negotiation') AND opp.expected_close_date<>'')
SELECT stage, COUNT(*) stuck_deals, ROUND(SUM(opportunity_amount),0) pipeline_value,
  ROUND(AVG(days_over),0) avg_days_overdue FROM oo WHERE days_over>0 GROUP BY stage ORDER BY pipeline_value DESC;""")
show("A8. Pipeline aging (CTE + date math)", a8)
ax = a8.plot(kind="bar", x="stage", y="pipeline_value", legend=False, figsize=(7, 5), color="#5a7d2a")
ax.set_title("Stuck Pipeline Value by Stage"); ax.set_ylabel("Opportunity value (GBP)"); ax.set_xlabel("")
plt.xticks(rotation=0); save("a8_pipeline_aging.png")

print("\nAdvanced charts saved to reports/figures/  (7 charts)")
conn.close()
