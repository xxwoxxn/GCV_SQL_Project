-- ====================================================================
-- GCV CRM — advanced analytical queries
-- Demonstrates: window functions, CTEs, correlated subqueries, CASE
-- bucketing, anti-/date arithmetic. Run against CRM.db.
-- ====================================================================

-- --------------------------------------------------------------------
-- A1. Sales-rep leaderboard            [window: RANK, SUM OVER + CTE]
-- Ranks reps by invoiced revenue, their share of total, and estimated
-- commission. Shows that revenue rank != commission rank.
-- --------------------------------------------------------------------
WITH rep AS (
    SELECT u.user_name,
           CAST(u.commission_rate AS REAL) AS comm,
           COUNT(DISTINCT o.order_id)       AS deals,
           SUM(i.total_amount)              AS revenue
    FROM Users u
    JOIN Opportunity opp ON opp.user_id = u.user_id
    JOIN Quote q         ON q.opportunity_id = opp.opportunity_id
    JOIN Orders o        ON o.quote_id = q.quote_id
    JOIN Invoice i       ON i.order_id = o.order_id
    GROUP BY u.user_id
)
SELECT user_name, deals, revenue,
       RANK() OVER (ORDER BY revenue DESC)                       AS revenue_rank,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 1)          AS pct_of_total,
       ROUND(revenue * comm / 100.0, 0)                          AS est_commission,
       RANK() OVER (ORDER BY revenue * comm DESC)                AS commission_rank
FROM rep
ORDER BY revenue_rank;

-- --------------------------------------------------------------------
-- A2. Pareto / 80-20 of accounts       [window: cumulative SUM OVER]
-- Lorenz-style curve: cumulative % of revenue against cumulative % of
-- accounts (ranked high to low). ~51% of accounts drive 80% of revenue.
-- --------------------------------------------------------------------
WITH acct_rev AS (
    SELECT a.account_id, SUM(i.total_amount) AS rev
    FROM Invoice i
    JOIN Orders o       ON i.order_id = o.order_id
    JOIN Quote q        ON o.quote_id = q.quote_id
    JOIN Opportunity opp ON q.opportunity_id = opp.opportunity_id
    JOIN Customer c     ON opp.customer_id = c.customer_id
    JOIN Account a      ON c.account_id = a.account_id
    GROUP BY a.account_id
)
SELECT ROW_NUMBER() OVER (ORDER BY rev DESC)                          AS rank,
       ROUND(100.0 * ROW_NUMBER() OVER (ORDER BY rev DESC)
             / COUNT(*) OVER (), 1)                                   AS pct_accounts,
       ROUND(100.0 * SUM(rev) OVER (ORDER BY rev DESC)
             / SUM(rev) OVER (), 1)                                   AS pct_revenue_cum
FROM acct_rev
ORDER BY rank;

-- --------------------------------------------------------------------
-- A3. Sales funnel                     [CTE VALUES + FIRST_VALUE / LAG]
-- Drop-off at each lifecycle stage, at opportunity grain so it is
-- monotonic. ~25% of opportunities never get quoted; once quoted, almost
-- all convert to order + invoice.
-- --------------------------------------------------------------------
WITH funnel(step, stage_name, cnt) AS (
    VALUES
      (1, 'Leads',         (SELECT COUNT(DISTINCT lead_id) FROM Lead)),
      (2, 'Opportunities', (SELECT COUNT(DISTINCT opportunity_id) FROM Opportunity)),
      (3, 'Quoted',        (SELECT COUNT(DISTINCT opportunity_id) FROM Quote)),
      (4, 'Ordered',       (SELECT COUNT(DISTINCT q.opportunity_id)
                            FROM Quote q JOIN Orders o ON o.quote_id = q.quote_id)),
      (5, 'Invoiced',      (SELECT COUNT(DISTINCT q.opportunity_id)
                            FROM Quote q JOIN Orders o ON o.quote_id = q.quote_id
                            JOIN Invoice i ON i.order_id = o.order_id))
)
SELECT stage_name, cnt,
       ROUND(100.0 * cnt / FIRST_VALUE(cnt) OVER (ORDER BY step), 1) AS pct_of_leads,
       ROUND(100.0 * cnt / LAG(cnt) OVER (ORDER BY step), 1)         AS step_conversion
FROM funnel
ORDER BY step;

-- --------------------------------------------------------------------
-- A4. Win rate by discount band        [CTE + CASE bucketing]
-- Tests whether deeper discounts buy wins. They do not: the 11-15% band
-- wins most (28.8%); 16-25% over-discounting wins less (23.5%).
-- --------------------------------------------------------------------
WITH opp_disc AS (
    SELECT opp.opportunity_id,
           MAX(q.discount)                                       AS max_discount,
           MAX(CASE WHEN s.stage = 'Won' THEN 1 ELSE 0 END)      AS won
    FROM Opportunity opp
    JOIN Stage s  ON opp.stage_id = s.stage_id
    JOIN Quote q  ON q.opportunity_id = opp.opportunity_id
    GROUP BY opp.opportunity_id
)
SELECT CASE WHEN max_discount <= 5  THEN '0-5%'
            WHEN max_discount <= 10 THEN '6-10%'
            WHEN max_discount <= 15 THEN '11-15%'
            ELSE '16-25%' END                            AS discount_band,
       COUNT(*)                                          AS opportunities,
       SUM(won)                                          AS won,
       ROUND(100.0 * SUM(won) / COUNT(*), 1)             AS win_rate_pct
FROM opp_disc
GROUP BY discount_band
ORDER BY win_rate_pct DESC;

-- --------------------------------------------------------------------
-- A5. Sales-cycle length by lead source    [date arithmetic + joins]
-- Days from lead creation to order. Email closes fastest (~70d); Inquiry
-- slowest (~108d) — and (see Q3) also lowest win rate.
-- --------------------------------------------------------------------
SELECT ls.lead_source,
       COUNT(*)                                                       AS deals,
       ROUND(AVG(julianday(o.order_date) - julianday(l.created_date)), 0) AS avg_cycle_days,
       MIN(CAST(julianday(o.order_date) - julianday(l.created_date) AS INT)) AS fastest_days
FROM Lead l
JOIN LeadSource ls   ON l.lead_source_id = ls.lead_source_id
JOIN Opportunity opp ON opp.lead_id = l.lead_id
JOIN Quote q         ON q.opportunity_id = opp.opportunity_id
JOIN Orders o        ON o.quote_id = q.quote_id
GROUP BY ls.lead_source
ORDER BY avg_cycle_days;

-- --------------------------------------------------------------------
-- A6. Leads scoring above their city average   [correlated subquery]
-- Each lead compared to the average lead score of its own (billing) city.
-- --------------------------------------------------------------------
SELECT ct.city_name, c.customer_name, l.lead_score,
       (SELECT ROUND(AVG(l2.lead_score), 1)
        FROM Lead l2
        JOIN Customer c2       ON l2.customer_id = c2.customer_id
        JOIN Account a2        ON c2.account_id = a2.account_id
        JOIN BillingAddress b2 ON a2.billing_address_id = b2.billing_address_id
        WHERE b2.city_id = ba.city_id)                       AS city_avg_score
FROM Lead l
JOIN Customer c        ON l.customer_id = c.customer_id
JOIN Account a         ON c.account_id = a.account_id
JOIN BillingAddress ba ON a.billing_address_id = ba.billing_address_id
JOIN City ct           ON ba.city_id = ct.city_id
WHERE l.lead_score >
      (SELECT AVG(l2.lead_score)
       FROM Lead l2
       JOIN Customer c2       ON l2.customer_id = c2.customer_id
       JOIN Account a2        ON c2.account_id = a2.account_id
       JOIN BillingAddress b2 ON a2.billing_address_id = b2.billing_address_id
       WHERE b2.city_id = ba.city_id)
ORDER BY (l.lead_score - city_avg_score) DESC
LIMIT 20;

-- --------------------------------------------------------------------
-- A7. Payment behaviour / DSO by method     [date math + aggregation]
-- Overdue rate, average days-to-pay, and late-fee burden per method.
-- --------------------------------------------------------------------
SELECT pm.payment_method,
       COUNT(*)                                                            AS paid_invoices,
       SUM(CASE WHEN julianday(i.payment_date) > julianday(i.due_date)
                THEN 1 ELSE 0 END)                                         AS overdue,
       ROUND(100.0 * SUM(CASE WHEN julianday(i.payment_date) > julianday(i.due_date)
                THEN 1 ELSE 0 END) / COUNT(*), 1)                          AS overdue_pct,
       ROUND(AVG(julianday(i.payment_date) - julianday(i.invoice_date)), 0) AS avg_days_to_pay,
       ROUND(SUM(i.late_fees), 0)                                          AS total_late_fees
FROM Invoice i
JOIN PaymentMethod pm ON i.payment_method_id = pm.payment_method_id
WHERE i.payment_date IS NOT NULL AND i.payment_date <> ''
GROUP BY pm.payment_method
ORDER BY overdue_pct DESC;

-- --------------------------------------------------------------------
-- A8. Pipeline aging                        [CTE + date arithmetic]
-- Opportunities still open (Prospecting/Negotiation) whose expected close
-- date has passed (as of the latest order date) — stuck pipeline value.
-- --------------------------------------------------------------------
WITH asof AS (SELECT MAX(order_date) AS d FROM Orders),
open_opps AS (
    SELECT s.stage, opp.opportunity_amount,
           julianday((SELECT d FROM asof)) - julianday(opp.expected_close_date) AS days_over
    FROM Opportunity opp
    JOIN Stage s ON opp.stage_id = s.stage_id
    WHERE s.stage IN ('Prospecting', 'Negotiation')
      AND opp.expected_close_date <> ''
)
SELECT stage,
       COUNT(*)                          AS stuck_deals,
       ROUND(SUM(opportunity_amount), 0) AS pipeline_value,
       ROUND(AVG(days_over), 0)          AS avg_days_overdue
FROM open_opps
WHERE days_over > 0
GROUP BY stage
ORDER BY pipeline_value DESC;
