#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the corrected business queries against CRM.db, print results, and save
charts to reports/figures/. Also prints a double-counting sanity check."""
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

def q(sql):
    return pd.read_sql_query(sql, conn)

def show(title, df):
    print("\n" + "=" * 64 + "\n" + title + "\n" + "-" * 64)
    print(df.to_string(index=False))

# ---- sanity check: the original double-counting bug ----
true_rev = q("SELECT SUM(total_amount) AS r FROM Invoice")["r"][0]
buggy_rev = q("""SELECT SUM(i.total_amount) AS r FROM Orders o
    JOIN Quote q ON o.quote_id=q.quote_id
    JOIN QuoteLineItem ql ON q.quote_id=ql.quote_id
    JOIN Invoice i ON o.order_id=i.order_id""")["r"][0]
print("Revenue sanity check:")
print("  TRUE invoice revenue (1 row/invoice): %15s" % format(int(true_rev), ","))
print("  Original buggy figure (line fan-out): %15s" % format(int(buggy_rev), ","))
print("  Inflation factor: %.2fx (+%s)" % (buggy_rev / true_rev,
                                           format(int(buggy_rev - true_rev), ",")))

# ---- Q1 Quarterly sales by vehicle type ----
q1 = q("""
SELECT strftime('%Y', o.order_date) || '-Q' ||
       ((CAST(strftime('%m', o.order_date) AS INTEGER)+2)/3) AS quarter,
       vt.vehicle_type, COUNT(DISTINCT o.order_id) AS orders,
       SUM(qli.quantity) AS units_sold, SUM(qli.total_price) AS revenue
FROM Orders o JOIN Quote q ON o.quote_id=q.quote_id
JOIN QuoteLineItem qli ON q.quote_id=qli.quote_id
JOIN Product p ON qli.product_id=p.product_id
JOIN VehicleType vt ON p.vehicle_type_id=vt.vehicle_type_id
GROUP BY quarter, vt.vehicle_type ORDER BY quarter, revenue DESC;""")
show("Q1. Quarterly sales by vehicle type (revenue from line items)", q1.head(12))

pivot = q1.pivot_table(index="quarter", columns="vehicle_type",
                       values="revenue", aggfunc="sum").fillna(0)
ax = pivot.plot(kind="line", marker="o", figsize=(11, 5))
ax.set_title("Quarterly Revenue by Vehicle Type")
ax.set_ylabel("Revenue (GBP)"); ax.set_xlabel("Quarter")
ax.grid(True, alpha=0.3); plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(os.path.join(FIG, "q1_quarterly_revenue_by_vehicle.png"), dpi=120); plt.close()

# ---- Q2 Territory leaderboard ----
q2 = q("""
SELECT ct.city_name, COUNT(DISTINCT o.order_id) AS total_orders,
       SUM(i.total_amount) AS total_revenue,
       ROUND(AVG(i.total_amount),0) AS avg_order_value
FROM Orders o JOIN ShippingAddress sa ON o.shipping_address_id=sa.shipping_address_id
JOIN City ct ON sa.city_id=ct.city_id
JOIN Invoice i ON o.order_id=i.order_id
GROUP BY ct.city_name ORDER BY total_revenue DESC;""")
show("Q2. Territory sales leaderboard (revenue now resolves by city)", q2)
print("  -> Q2 revenue sums to %s (matches true invoice revenue: %s)"
      % (format(int(q2.total_revenue.sum()), ","), int(q2.total_revenue.sum()) == int(true_rev)))

ax = q2.plot(kind="bar", x="city_name", y="total_revenue", legend=False, figsize=(11, 5), color="#2a7ab9")
ax.set_title("Total Sales Revenue by City"); ax.set_ylabel("Revenue (GBP)"); ax.set_xlabel("")
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(os.path.join(FIG, "q2_revenue_by_city.png"), dpi=120); plt.close()

# ---- Q3 Lead source effectiveness ----
q3 = q("""
SELECT ls.lead_source, COUNT(*) AS total_leads,
       SUM(CASE WHEN s.stage='Won' THEN 1 ELSE 0 END) AS won,
       ROUND(100.0*SUM(CASE WHEN s.stage='Won' THEN 1 ELSE 0 END)/COUNT(*),1) AS win_rate_pct,
       ROUND(AVG(l.lead_score),1) AS avg_lead_score
FROM Lead l JOIN LeadSource ls ON l.lead_source_id=ls.lead_source_id
JOIN Opportunity opp ON opp.lead_id=l.lead_id
JOIN Stage s ON opp.stage_id=s.stage_id
GROUP BY ls.lead_source ORDER BY win_rate_pct DESC;""")
show("Q3. Lead source effectiveness (win rate)", q3)

ax = q3.plot(kind="bar", x="lead_source", y="win_rate_pct", legend=False, figsize=(10, 5), color="#e07b39")
ax.set_title("Win Rate by Lead Source"); ax.set_ylabel("Win rate (%)"); ax.set_xlabel("")
plt.xticks(rotation=30, ha="right"); plt.tight_layout()
plt.savefig(os.path.join(FIG, "q3_win_rate_by_source.png"), dpi=120); plt.close()

# ---- Q4 Avg lead score by city ----
q4 = q("""
SELECT ct.city_name, ROUND(AVG(l.lead_score),1) AS avg_lead_score, COUNT(*) AS leads
FROM Lead l JOIN Customer c ON l.customer_id=c.customer_id
JOIN Account a ON c.account_id=a.account_id
JOIN BillingAddress ba ON a.billing_address_id=ba.billing_address_id
JOIN City ct ON ba.city_id=ct.city_id
GROUP BY ct.city_name ORDER BY avg_lead_score DESC;""")
show("Q4. Average lead score by city", q4)

ax = q4.plot(kind="bar", x="city_name", y="avg_lead_score", legend=False, figsize=(11, 5), color="#4c9a5d")
ax.set_title("Average Lead Score by City"); ax.set_ylabel("Avg lead score"); ax.set_xlabel("")
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(os.path.join(FIG, "q4_avg_lead_score_by_city.png"), dpi=120); plt.close()

# ---- Q5 Warranty mix ----
q5 = q("""SELECT w.warranty AS warranty_type, COUNT(qli.line_item_id) AS line_items,
       SUM(qli.quantity) AS units_sold
FROM QuoteLineItem qli JOIN Warranty w ON qli.warranty_id=w.warranty_id
GROUP BY w.warranty ORDER BY units_sold DESC;""")
show("Q5. Warranty mix", q5)

print("\nFigures saved to reports/figures/  (4 charts)")
conn.close()
