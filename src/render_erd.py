#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the re-normalised schema to ERD.png (matplotlib). A Mermaid version
(rendered natively by GitHub) lives in docs/erd.md."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "ERD.png")

# table -> (x, y, [columns]); PK marked *, FK marked +
E = {
    "Users":      (0.5, 7.0, ["*user_id", "user_name", "+role_id"]),
    "Account":    (0.5, 5.2, ["*account_id", "+user_id", "+billing_address_id", "+industry_id"]),
    "Customer":   (0.5, 3.2, ["*customer_id", "+account_id", "+job_title_id"]),
    "Lead":       (0.5, 1.2, ["*lead_id", "+customer_id", "+lead_source_id", "+lead_status_id"]),
    "Opportunity":(3.4, 1.2, ["*opportunity_id", "+lead_id", "+customer_id", "+stage_id", "+product_id", "+lost_reason_id"]),
    "Quote":      (3.4, 3.4, ["*quote_id", "+opportunity_id", "+quote_status_id", "discount", "total_amount"]),
    "Orders":     (3.4, 5.4, ["*order_id", "+quote_id", "+shipping_address_id", "+order_status_id"]),
    "Invoice":    (3.4, 7.2, ["*invoice_id", "+order_id", "+payment_status_id", "+payment_method_id", "total_amount"]),
    "QuoteLineItem":(6.4, 3.0, ["*line_item_id", "+quote_id", "+product_id", "+warranty_id", "quantity", "total_price"]),
    "Product":    (6.4, 1.0, ["*product_id", "+vehicle_type_id", "+fuel_type_id", "base_price"]),
    "BillingAddress": (6.4, 5.4, ["*billing_address_id", "+city_id"]),
    "ShippingAddress":(6.4, 6.6, ["*shipping_address_id", "+city_id"]),
}
# dimensions (compact): name -> (x, y)
D = {
    "Role": (2.0, 7.6), "Industry": (2.0, 6.4), "JobTitle": (2.0, 4.2),
    "LeadSource": (2.0, 0.4), "LeadStatus": (2.0, 1.4),
    "Stage": (5.0, 0.2), "LostReason": (5.0, 1.0),
    "QuoteStatus": (5.0, 2.6), "OrderStatus": (5.0, 5.0),
    "PaymentStatus": (5.0, 7.6), "PaymentMethod": (5.0, 6.9),
    "Warranty": (8.3, 3.4), "VehicleType": (8.3, 1.4), "FuelType": (8.3, 0.6),
    "City": (8.3, 6.0),
}
# FK edges: (child, parent)
EDGES = [
    ("Account","Users"),("Customer","Account"),("Lead","Customer"),
    ("Opportunity","Lead"),("Quote","Opportunity"),("Orders","Quote"),
    ("Invoice","Orders"),("QuoteLineItem","Quote"),("QuoteLineItem","Product"),
    ("Orders","ShippingAddress"),("Account","BillingAddress"),
    ("Users","Role"),("Account","Industry"),("Customer","JobTitle"),
    ("Lead","LeadSource"),("Lead","LeadStatus"),("Opportunity","Stage"),
    ("Opportunity","LostReason"),("Opportunity","Product"),("Quote","QuoteStatus"),
    ("Orders","OrderStatus"),("Invoice","PaymentStatus"),("Invoice","PaymentMethod"),
    ("QuoteLineItem","Warranty"),("Product","VehicleType"),("Product","FuelType"),
    ("BillingAddress","City"),("ShippingAddress","City"),
]

fig, ax = plt.subplots(figsize=(17, 11))
boxes = {}  # name -> (cx, cy, w, h)
CW = 2.05

def draw_entity(name, x, y, cols):
    h = 0.26 * (len(cols) + 1) + 0.12
    ax.add_patch(FancyBboxPatch((x, y), CW, h, boxstyle="round,pad=0.02",
                 linewidth=1.4, edgecolor="#1f3b57", facecolor="#eaf2fb"))
    ax.text(x + CW/2, y + h - 0.16, name, ha="center", va="center",
            fontsize=11, fontweight="bold", color="#11304b")
    ax.plot([x, x+CW], [y+h-0.32, y+h-0.32], color="#1f3b57", lw=0.8)
    for i, c in enumerate(cols):
        ax.text(x + 0.1, y + h - 0.52 - i*0.26, c, ha="left", va="center",
                fontsize=8.3, family="monospace")
    boxes[name] = (x + CW/2, y + h/2, CW, h)

def draw_dim(name, x, y):
    w, h = 1.7, 0.42
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                 linewidth=1.1, edgecolor="#5a7d2a", facecolor="#f0f6e6"))
    ax.text(x + w/2, y + h/2, name, ha="center", va="center",
            fontsize=8.6, color="#3c5418")
    boxes[name] = (x + w/2, y + h/2, w, h)

for n,(x,y,cols) in E.items(): draw_entity(n,x,y,cols)
for n,(x,y) in D.items(): draw_dim(n,x,y)

for child, parent in EDGES:
    if child not in boxes or parent not in boxes: continue
    c = boxes[child]; p = boxes[parent]
    ax.add_patch(FancyArrowPatch((c[0], c[1]), (p[0], p[1]),
                 arrowstyle="-|>", mutation_scale=11, color="#8a8a8a",
                 lw=0.8, alpha=0.55, shrinkA=14, shrinkB=14,
                 connectionstyle="arc3,rad=0.06"))

ax.text(0.3, 9.0, "GCV CRM — Entity Relationship Diagram (re-normalised 3NF)",
        fontsize=15, fontweight="bold", color="#11304b")
ax.text(0.3, 8.7, "* primary key    + foreign key    blue = entities    green = dimensions",
        fontsize=9.5, color="#555")
ax.set_xlim(0, 10.3); ax.set_ylim(0, 9.3); ax.axis("off")
plt.tight_layout()
plt.savefig(OUT, dpi=130, bbox_inches="tight"); plt.close()
print("ERD written:", os.path.abspath(OUT))
