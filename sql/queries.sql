-- ====================================================================
-- GCV CRM — business insight queries (corrected)
-- Run against CRM.db built by src/build_db.py
-- ====================================================================

-- --------------------------------------------------------------------
-- Q1. Quarterly sales by vehicle type
-- FIX: revenue is taken from QuoteLineItem.total_price (the per-line value),
-- NOT Invoice.total_amount. Joining line items and then summing the invoice
-- total multiplies revenue by the number of line items per order.
-- --------------------------------------------------------------------
SELECT
    strftime('%Y', o.order_date) || '-Q' ||
        ((CAST(strftime('%m', o.order_date) AS INTEGER) + 2) / 3) AS quarter,
    vt.vehicle_type,
    COUNT(DISTINCT o.order_id)      AS orders,
    SUM(qli.quantity)               AS units_sold,
    SUM(qli.total_price)            AS revenue
FROM Orders o
JOIN Quote q          ON o.quote_id   = q.quote_id
JOIN QuoteLineItem qli ON q.quote_id  = qli.quote_id
JOIN Product p        ON qli.product_id = p.product_id
JOIN VehicleType vt   ON p.vehicle_type_id = vt.vehicle_type_id
GROUP BY quarter, vt.vehicle_type
ORDER BY quarter, revenue DESC;

-- --------------------------------------------------------------------
-- Q2. Territory sales leaderboard
-- FIX: no QuoteLineItem join (it fanned out invoice rows); City is now a
-- valid dimension so cities actually resolve (previously all NULL).
-- --------------------------------------------------------------------
SELECT
    ct.city_name,
    COUNT(DISTINCT o.order_id)      AS total_orders,
    SUM(i.total_amount)             AS total_revenue,
    ROUND(AVG(i.total_amount), 0)   AS avg_order_value
FROM Orders o
JOIN ShippingAddress sa ON o.shipping_address_id = sa.shipping_address_id
JOIN City ct            ON sa.city_id = ct.city_id
JOIN Invoice i          ON o.order_id = i.order_id
GROUP BY ct.city_name
ORDER BY total_revenue DESC;

-- --------------------------------------------------------------------
-- Q3. Lead source effectiveness (win rate)
-- Every lead becomes an opportunity here, so the meaningful metric is the
-- share of opportunities that reach the 'Won' stage, by source.
-- --------------------------------------------------------------------
SELECT
    ls.lead_source,
    COUNT(*)                                              AS total_leads,
    SUM(CASE WHEN s.stage = 'Won' THEN 1 ELSE 0 END)      AS won,
    ROUND(100.0 * SUM(CASE WHEN s.stage = 'Won' THEN 1 ELSE 0 END)
          / COUNT(*), 1)                                  AS win_rate_pct,
    ROUND(AVG(l.lead_score), 1)                           AS avg_lead_score
FROM Lead l
JOIN LeadSource ls   ON l.lead_source_id = ls.lead_source_id
JOIN Opportunity opp ON opp.lead_id = l.lead_id
JOIN Stage s         ON opp.stage_id = s.stage_id
GROUP BY ls.lead_source
ORDER BY win_rate_pct DESC;

-- --------------------------------------------------------------------
-- Q4. Top lead sources and average lead score by (billing) city
-- --------------------------------------------------------------------
SELECT
    ct.city_name,
    ls.lead_source,
    COUNT(l.lead_id)            AS total_leads,
    ROUND(AVG(l.lead_score), 1) AS avg_lead_score
FROM Lead l
JOIN LeadSource ls     ON l.lead_source_id = ls.lead_source_id
JOIN Customer c        ON l.customer_id = c.customer_id
JOIN Account a         ON c.account_id = a.account_id
JOIN BillingAddress ba ON a.billing_address_id = ba.billing_address_id
JOIN City ct           ON ba.city_id = ct.city_id
GROUP BY ct.city_name, ls.lead_source
ORDER BY ct.city_name, total_leads DESC;

-- --------------------------------------------------------------------
-- Q5. Warranty mix (units sold by warranty tier)
-- --------------------------------------------------------------------
SELECT
    w.warranty AS warranty_type,
    COUNT(qli.line_item_id) AS line_items,
    SUM(qli.quantity)       AS units_sold
FROM QuoteLineItem qli
JOIN Warranty w ON qli.warranty_id = w.warranty_id
GROUP BY w.warranty
ORDER BY units_sold DESC;
