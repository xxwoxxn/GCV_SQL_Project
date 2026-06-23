#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-normalize the raw GCV CRM export into a clean 3NF dataset.

The raw synthetic data (data/raw) has two systemic defects:
  1. Every "lookup" table stores one row PER OCCURRENCE instead of one row per
     distinct value (e.g. Warranty has 1000 rows for 3 values). This is the
     opposite of normalisation, despite the report claiming 3NF.
  2. Broken foreign keys:
       - ShippingAddress.shipping_city_id uses a 'CIT' prefix while ShippingCity
         ids are 'SCT' (same numeric suffix) -> 700/700 dangling.
       - Customer.job_title_id ranges JOB00002..JOB00500 but JobTitle has only
         ~50 rows -> 451/500 dangling.

This script rebuilds proper dimension tables (one row per distinct value),
unifies Billing/Shipping city into a single City dimension, repoints every
foreign key, and writes the result to data/clean.
"""
import os, hashlib
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
CLEAN = os.path.join(HERE, "..", "data", "clean")
os.makedirs(CLEAN, exist_ok=True)

log_lines = []
def log(msg=""):
    print(msg)
    log_lines.append(str(msg))

def read(name):
    df = pd.read_csv(os.path.join(RAW, name + ".csv"), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    return df

def write(name, df):
    df.to_csv(os.path.join(CLEAN, name + ".csv"), index=False)
    return len(df)

raw = {}
for f in os.listdir(RAW):
    if f.endswith(".csv"):
        raw[f[:-4]] = read(f[:-4])

log("=" * 64)
log("RE-NORMALISATION LOG")
log("=" * 64)

# ----------------------------------------------------------------------
# 1. Generic lookup dimensions: dedupe to distinct values, repoint FKs.
#    Each entry: lookup_table -> (new_prefix, [(fact_table, fk_col), ...])
#    Lookups are all 2-column [id, value]; we address columns positionally.
# ----------------------------------------------------------------------
LOOKUPS = {
    "Industry":      ("IND", [("Account", "industry_id")]),
    "LeadSource":    ("LSR", [("Lead", "lead_source_id")]),
    "LeadStatus":    ("LST", [("Lead", "lead_status_id")]),
    "LostReason":    ("LRS", [("Opportunity", "lost_reason_id")]),
    "QuoteStatus":   ("QST", [("Quote", "quote_status_id")]),
    "PaymentMethod": ("PMT", [("Invoice", "payment_method_id")]),
    "PaymentStatus": ("PST", [("Invoice", "payment_status_id")]),
    "OrderStatus":   ("OST", [("Orders", "order_status_id")]),
    "Warranty":      ("WAR", [("QuoteLineItem", "warranty_id")]),
    "VehicleType":   ("VHT", [("Product", "vehicle_type_id")]),
    "FuelType":      ("FUL", [("Product", "fuel_type_id")]),
    "Role":          ("ROL", [("Users", "role_id")]),
    "Stage":         ("STG", [("Opportunity", "stage_id")]),
}

clean = {}  # name -> df (written at the end)

SENTINELS = {"", "Na", "NA", "N/A", "nan", "None"}

def dedupe_lookup(name, prefix, refs):
    df = raw[name]
    id_col, val_col = df.columns[0], df.columns[1]
    old_to_val = dict(zip(df[id_col], df[val_col]))
    # Sentinels (e.g. 'Na' for "no lost reason") are not real members; fact rows
    # that referenced them resolve to NULL via the map below.
    distinct = sorted(v for v in df[val_col].unique() if v not in SENTINELS)
    val_to_new = {v: "%s%05d" % (prefix, i + 1) for i, v in enumerate(distinct)}
    dim = pd.DataFrame({id_col: [val_to_new[v] for v in distinct], val_col: distinct})
    clean[name] = dim
    log("  %-14s %4d -> %2d rows" % (name, len(df), len(dim)))
    for fact, fk in refs:
        f = raw[fact]
        f[fk] = f[fk].map(old_to_val).map(val_to_new)
        raw[fact] = f

log("\n[1] Lookup dimensions deduplicated:")
for name, (prefix, refs) in LOOKUPS.items():
    dedupe_lookup(name, prefix, refs)

# ----------------------------------------------------------------------
# 2. City: merge BillingCity + ShippingCity into one City dimension.
#    BillingAddress.billing_city_id -> valid BCT (recover name).
#    ShippingAddress.shipping_city_id -> 'CIT'+n is wrong, real is 'SCT'+n.
# ----------------------------------------------------------------------
log("\n[2] City dimension (merge Billing/Shipping):")
bc = raw["BillingCity"];   bc.columns = ["billing_city_id", "city_name"]
sc = raw["ShippingCity"];  sc.columns = ["shipping_city_id", "city_name"]
cities = sorted(set(bc["city_name"]) | set(sc["city_name"]))
city_to_id = {c: "CTY%05d" % (i + 1) for i, c in enumerate(cities)}
clean["City"] = pd.DataFrame({"city_id": [city_to_id[c] for c in cities],
                              "city_name": cities})
log("  City dimension: %d distinct cities" % len(cities))

bc_to_name = dict(zip(bc["billing_city_id"], bc["city_name"]))
ba = raw["BillingAddress"]                       # billing_address_id, billing_address, billing_city_id
ba["city_id"] = ba["billing_city_id"].map(bc_to_name).map(city_to_id)
ba = ba.drop(columns=["billing_city_id"])
clean["BillingAddress"] = ba
log("  BillingAddress: %d rows linked to City (recovered from BillingCity)" % len(ba))

sc_to_name = dict(zip(sc["shipping_city_id"], sc["city_name"]))
sa = raw["ShippingAddress"]                      # shipping_address_id, shipping_address, shipping_city_id
fixed = sa["shipping_city_id"].str.replace(r"^CIT", "SCT", regex=True)
sa["city_id"] = fixed.map(sc_to_name).map(city_to_id)
n_recovered = sa["city_id"].notna().sum()
sa = sa.drop(columns=["shipping_city_id"])
clean["ShippingAddress"] = sa
log("  ShippingAddress: %d/%d rows recovered via CIT->SCT prefix fix" % (n_recovered, len(sa)))

# ----------------------------------------------------------------------
# 3. JobTitle: dedupe to 9 titles. Customer.job_title_id is 90% dangling;
#    recover where valid, else assign deterministically (seeded by id).
# ----------------------------------------------------------------------
log("\n[3] JobTitle dimension + Customer reassignment:")
jt = raw["JobTitle"]; jt_id, jt_val = jt.columns[0], jt.columns[1]
old_jt_to_val = dict(zip(jt[jt_id], jt[jt_val]))
titles = sorted(v for v in jt[jt_val].unique() if v != "")
title_to_id = {t: "JOB%05d" % (i + 1) for i, t in enumerate(titles)}
clean["JobTitle"] = pd.DataFrame({jt_id: [title_to_id[t] for t in titles],
                                  jt_val: titles})
log("  JobTitle %d -> %d rows" % (len(jt), len(titles)))

def assign_title(cid, old_id):
    v = old_jt_to_val.get(old_id)
    if v in title_to_id:
        return title_to_id[v]                    # genuine reference preserved
    h = int(hashlib.md5(cid.encode()).hexdigest(), 16)
    return title_to_id[titles[h % len(titles)]]  # deterministic fill

cust = raw["Customer"]
recovered = cust["job_title_id"].isin(old_jt_to_val) & \
            cust["job_title_id"].map(old_jt_to_val).isin(title_to_id)
cust["job_title_id"] = [assign_title(c, o)
                        for c, o in zip(cust["customer_id"], cust["job_title_id"])]
clean["Customer"] = cust
log("  Customer: %d genuine titles kept, %d reassigned deterministically"
    % (int(recovered.sum()), int((~recovered).sum())))

# ----------------------------------------------------------------------
# 4. Pass-through entity tables (FKs already remapped in place above).
# ----------------------------------------------------------------------
for t in ["Users", "Account", "Lead", "Opportunity", "Quote",
          "QuoteLineItem", "Orders", "Invoice", "Product"]:
    clean[t] = raw[t]

# ----------------------------------------------------------------------
# 4b. Deduplicate primary keys (the raw export has a few dup PKs that the
#     original INSERT OR REPLACE load silently collapsed; keep last, as REPLACE
#     did). Addresses/Product/Users are already unique.
# ----------------------------------------------------------------------
log("\n[4] Deduplicating primary keys (keep last, matching INSERT OR REPLACE):")
PK = {"Account": "account_id", "Customer": "customer_id", "Lead": "lead_id",
      "Opportunity": "opportunity_id", "Quote": "quote_id", "Orders": "order_id",
      "Invoice": "invoice_id", "QuoteLineItem": "line_item_id"}
for t, k in PK.items():
    before = len(clean[t])
    clean[t] = clean[t].drop_duplicates(subset=k, keep="last")
    if before != len(clean[t]):
        log("  %-13s -%d dup PK" % (t, before - len(clean[t])))

# ----------------------------------------------------------------------
# 4c. Normalise null sentinels and drop blank rows.
#     Open opportunities/undelivered orders store the string 'Na' for dates;
#     convert to real NULL. One Opportunity and stray rows are fully blank.
# ----------------------------------------------------------------------
log("\n[5] Null-sentinel cleanup (date columns only):")
for t, df in clean.items():
    date_cols = [c for c in df.columns if "date" in c.lower()]
    for c in date_cols:
        df[c] = df[c].replace(list(SENTINELS - {""}), "")
    clean[t] = df
before = len(clean["Opportunity"])
clean["Opportunity"] = clean["Opportunity"][clean["Opportunity"]["opportunity_amount"] != ""]
log("  Opportunity: dropped %d blank-amount row(s)" % (before - len(clean["Opportunity"])))
before = len(clean["Invoice"])
clean["Invoice"] = clean["Invoice"][clean["Invoice"]["invoice_date"] != ""]
log("  Invoice: dropped %d blank-date row(s)" % (before - len(clean["Invoice"])))

# ----------------------------------------------------------------------
# 6. Drop the handful of genuinely orphaned rows (broken entity FKs) so the
#    clean dataset passes FK enforcement. Resolve in dependency order.
# ----------------------------------------------------------------------
log("\n[6] Dropping orphan rows (broken entity references):")
def drop_orphans(child, fk, parent, pk):
    valid = set(clean[parent][pk])
    before = len(clean[child])
    clean[child] = clean[child][clean[child][fk].isin(valid) | (clean[child][fk] == "")]
    dropped = before - len(clean[child])
    if dropped:
        log("  %-13s -%d (dangling %s -> %s)" % (child, dropped, fk, parent))

# parents first
drop_orphans("Customer", "account_id", "Account", "account_id")
drop_orphans("Lead", "customer_id", "Customer", "customer_id")
drop_orphans("Opportunity", "lead_id", "Lead", "lead_id")
drop_orphans("Opportunity", "customer_id", "Customer", "customer_id")
drop_orphans("Quote", "opportunity_id", "Opportunity", "opportunity_id")
drop_orphans("QuoteLineItem", "quote_id", "Quote", "quote_id")
drop_orphans("Orders", "quote_id", "Quote", "quote_id")
drop_orphans("Invoice", "order_id", "Orders", "order_id")

# ----------------------------------------------------------------------
# 6. Write clean CSVs.
# ----------------------------------------------------------------------
log("\n[7] Writing clean CSVs to data/clean:")
total = 0
for name, df in sorted(clean.items()):
    n = write(name, df)
    total += n
log("  %d tables, %d total rows written" % (len(clean), total))

with open(os.path.join(HERE, "..", "docs", "normalize_log.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(log_lines))
log("\nDone.")
