#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build CRM.db from sql/schema.sql + data/clean CSVs, with FK enforcement ON.
Loads in dependency order and runs PRAGMA foreign_key_check at the end."""
import os, csv, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLEAN = os.path.join(HERE, "..", "data", "clean")
SCHEMA = os.path.join(HERE, "..", "sql", "schema.sql")
DB = os.path.join(HERE, "..", "CRM.db")

# dependency order: dimensions -> addresses -> entities
LOAD_ORDER = [
    "City", "JobTitle", "Industry", "LeadSource", "LeadStatus", "LostReason",
    "QuoteStatus", "PaymentMethod", "PaymentStatus", "OrderStatus", "Warranty",
    "VehicleType", "FuelType", "Role",
    "BillingAddress", "ShippingAddress",
    "Users", "Account", "Customer", "Lead", "Product", "Stage",
    "Opportunity", "Quote", "Orders", "Invoice", "QuoteLineItem",
]

def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    with open(SCHEMA, encoding="utf-8") as fh:
        cur.executescript(fh.read())
    cur.execute("PRAGMA foreign_keys = ON;")

    print("Loading clean CSVs (FK enforcement ON):")
    for t in LOAD_ORDER:
        path = os.path.join(CLEAN, t + ".csv")
        with open(path, encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            cols = [c.strip() for c in next(r)]
            ph = ", ".join("?" for _ in cols)
            sql = "INSERT INTO %s (%s) VALUES (%s)" % (t, ", ".join(cols), ph)
            rows = [[(v if v != "" else None) for v in row] for row in r]
            cur.executemany(sql, rows)
        print("  %-16s %d rows" % (t, len(rows)))
    conn.commit()

    violations = cur.execute("PRAGMA foreign_key_check;").fetchall()
    print("\nForeign-key check:",
          "PASS (0 violations)" if not violations else "FAIL: %d" % len(violations))
    if violations:
        from collections import Counter
        for (tbl, _, parent, _), n in Counter((v[0], v[2]) for v in violations).items():
            print("  %s -> %s : %d" % (tbl, parent, n))
        conn.close(); sys.exit(1)

    n_tables = cur.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table';").fetchone()[0]
    print("Tables: %d   DB: %s" % (n_tables, os.path.abspath(DB)))
    conn.close()

if __name__ == "__main__":
    main()
