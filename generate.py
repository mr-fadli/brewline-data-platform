"""
Brewline Coffee Co. — Synthetic Data Generator
================================================
Generates realistic bronze-layer exports for 5 source systems:
  - Shopify (orders, one-off + recharge-originated)
  - Square POS (line-item grain transactions, 3 stores)
  - Recharge (subscription lifecycle)
  - Zendesk (support tickets)
  - ShipStation (shipment tracking)

Deliberately injects the real-world messiness identified during requirements
gathering, so the pipeline has something honest to prove itself against:
  - CAD currency mixed with USD orders
  - Recharge-originated orders tagged via source_name (subset of Shopify, not additive)
  - Subscription cancelled-for-payment-failure-then-resubscribed-within-48h ("Erin case")
  - A mislabeled-batch incident causing a refund spike + matching Zendesk tickets
  - Square transactions with sparse/missing customer_phone (walk-ins)
  - Zendesk tickets with missing requester_email and inconsistent order linkage
  - Partial refunds that don't cleanly map to a single line item price
  - Cancelled Shopify orders where financial_status doesn't auto-flip

Output partitioning:
  - Shopify orders, Square transactions, Zendesk tickets, ShipStation shipments
    are written as ONE FILE PER DAY -- these are append-style sources where
    each day's file is a new batch of daily facts.
  - Recharge subscriptions are written as a FULL SNAPSHOT PER DAY -- each
    day's file contains the complete current state of every subscription as
    of that day (not just what changed), matching how a real subscription
    platform export behaves. This is why bronze's loading strategy for
    Recharge should be "overwrite with latest known state" while the other
    four sources are genuinely append-only.
"""

import json
import csv
import random
from datetime import datetime, timedelta, timezone
from itertools import groupby
from pathlib import Path
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

OUT_DIR = Path(__file__).parent / "pipelines" / "bronze" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- Config -----------------------------------------------------------
NUM_DAYS = 30
START_DATE = datetime(2026, 6, 8, tzinfo=timezone.utc)
SHOPIFY_ORDERS_PER_DAY = (35, 50)      # scaled down from real 450-600/day for a portfolio-sized demo
SQUARE_TXNS_PER_DAY = (15, 25)         # scaled down from real 200-300/day
STORES = ["STORE-01", "STORE-02", "STORE-03"]
STORE_TZ_OFFSET = {"STORE-01": -4, "STORE-02": -5, "STORE-03": -7}  # ET, CT-ish, PT

PRODUCTS = [
    {"sku": "DR-12OZ", "name": "Dark Roast 12oz", "price": 16.00},
    {"sku": "DR-8OZ",  "name": "Dark Roast 8oz",  "price": 11.00},
    {"sku": "LR-12OZ", "name": "Light Roast 12oz", "price": 15.00},
    {"sku": "MR-12OZ", "name": "Medium Roast 12oz", "price": 15.50},
    {"sku": "GM-8OZ",  "name": "Ground Medium 8oz", "price": 6.50},
    {"sku": "MUG-CER", "name": "Ceramic Mug", "price": 12.00},
    {"sku": "GRINDER-01", "name": "Burr Grinder", "price": 42.00},
    {"sku": "DRIPPER-01", "name": "Pour-Over Dripper", "price": 22.00},
]
SUB_PRODUCTS = [
    {"sku": "SUB-CURATED", "name": "Subscription Box - Curated", "price": 28.00},
    {"sku": "SUB-CUSTOM",  "name": "Subscription Box - Customize", "price": 22.50},
]
MISLABELED_SKU = "DR-12OZ"  # the batch that got mislabeled as ground instead of whole bean
MISLABEL_INCIDENT_START = START_DATE + timedelta(days=10)
MISLABEL_INCIDENT_END = START_DATE + timedelta(days=13)

# ---- Customer pools -----------------------------------------------------
def make_online_customers(n):
    return [{"email": fake.unique.email(), "name": fake.name()} for _ in range(n)]

def make_loyalty_customers(n):
    return [{"phone": fake.unique.numerify("555-####"), "name": fake.name()} for _ in range(n)]

ONLINE_CUSTOMERS = make_online_customers(120)
LOYALTY_CUSTOMERS = make_loyalty_customers(40)
SUBSCRIBERS = random.sample(ONLINE_CUSTOMERS, 35)

# ---- Helper: bucket an already-built list of rows into daily files --------
def write_daily_files(rows, date_key_fn, name_prefix, fieldnames=None):
    """Group finished rows by a date key extracted from each row, and write
    one CSV per day. Used for sources (Zendesk, ShipStation) that are
    generated in a pass referencing already-built orders, rather than
    generated inside their own per-day loop."""
    if not rows:
        return
    rows_sorted = sorted(rows, key=date_key_fn)
    for day_str, group in groupby(rows_sorted, key=date_key_fn):
        group_list = list(group)
        path = OUT_DIR / f"{name_prefix}_{day_str}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames or list(group_list[0].keys()))
            writer.writeheader()
            writer.writerows(group_list)

# ---- Shopify --------------------------------------------------------------
shopify_orders = []          # full-run accumulation, still used by downstream Zendesk/ShipStation passes
order_counter = 5000
refund_counter = 9000

def next_order_id():
    global order_counter
    order_counter += 1
    return f"#{order_counter}"

def next_refund_id():
    global refund_counter
    refund_counter += 1
    return f"RF-{refund_counter}"

recharge_subs = {}   # customer_email -> current subscription dict (live state)
recharge_sub_history = []  # superseded subscription rows (append-only, mimics a real export)

# seed one active subscription per subscriber
for cust in SUBSCRIBERS:
    sub_id = f"RC-{100 + len(recharge_subs)}"
    freq = random.choice([14, 30])
    created = START_DATE - timedelta(days=random.randint(30, 120))
    recharge_subs[cust["email"]] = {
        "subscription_id": sub_id,
        "customer_email": cust["email"],
        "status": "active",
        "frequency_days": freq,
        "created_at": created.isoformat(),
        "next_charge_date": (START_DATE + timedelta(days=random.randint(1, freq))).date().isoformat(),
        "cancelled_at": None,
        "cancellation_reason": None,
        "linked_shopify_order_id": None,
    }

# pick a few subscribers to go through the "payment failed -> cancel -> resubscribe within 48h" pattern
REACTIVATION_CUSTOMERS = random.sample(SUBSCRIBERS, 3)
# pick a few to go through genuine voluntary churn
VOLUNTARY_CHURN_CUSTOMERS = random.sample([c for c in SUBSCRIBERS if c not in REACTIVATION_CUSTOMERS], 4)
# pick a few to pause
PAUSED_CUSTOMERS = random.sample(
    [c for c in SUBSCRIBERS if c not in REACTIVATION_CUSTOMERS and c not in VOLUNTARY_CHURN_CUSTOMERS], 3
)

shopify_daily_file_count = 0
recharge_daily_file_count = 0

for day in range(NUM_DAYS):
    day_date = START_DATE + timedelta(days=day)
    n_orders = random.randint(*SHOPIFY_ORDERS_PER_DAY)
    day_orders = []  # reset at the top of each day's iteration

    for _ in range(n_orders):
        is_subscription_renewal = random.random() < 0.35
        currency = "CAD" if random.random() < 0.08 else "USD"
        tz_off = random.choice([-4, -5, -7])
        order_time = day_date + timedelta(
            hours=random.randint(6, 22), minutes=random.randint(0, 59)
        )
        order_time = order_time.replace(tzinfo=timezone(timedelta(hours=tz_off)))

        if is_subscription_renewal and SUBSCRIBERS:
            cust = random.choice(SUBSCRIBERS)
            product = random.choice(SUB_PRODUCTS)
            line_items = [{"sku": product["sku"], "name": product["name"], "qty": 1, "price": product["price"]}]
            total = product["price"]
            source_name = "recharge"
        else:
            cust = random.choice(ONLINE_CUSTOMERS)
            n_items = random.randint(1, 3)
            chosen = random.sample(PRODUCTS, n_items)
            line_items = [{"sku": p["sku"], "name": p["name"], "qty": random.randint(1, 2), "price": p["price"]} for p in chosen]
            total = round(sum(li["price"] * li["qty"] for li in line_items), 2)
            source_name = "web"

        order_id = next_order_id()
        cancelled_at = None
        financial_status = "paid"
        refunds = []

        # small % of web orders get cancelled before shipping
        if source_name == "web" and random.random() < 0.03:
            cancelled_at = (order_time + timedelta(minutes=30)).isoformat()
            # cancellation does NOT automatically flip financial_status — matches real Shopify behavior

        # mislabeled batch incident: DR-12OZ orders in the incident window have elevated refund rate
        in_incident_window = MISLABEL_INCIDENT_START <= day_date <= MISLABEL_INCIDENT_END
        contains_mislabeled_sku = any(li["sku"] == MISLABELED_SKU for li in line_items)
        refund_chance = 0.35 if (in_incident_window and contains_mislabeled_sku) else 0.02

        if random.random() < refund_chance and not cancelled_at:
            refund_delay_days = random.randint(1, 6)
            refund_amount = total if random.random() < 0.6 else round(total * random.uniform(0.2, 0.6), 2)
            financial_status = "refunded" if refund_amount >= total else "partially_refunded"
            reason = "product_mislabeled" if (in_incident_window and contains_mislabeled_sku) else random.choice(
                ["damaged_item", "changed_mind", "wrong_item"]
            )
            refunds.append({
                "refund_id": next_refund_id(),
                "amount": refund_amount,
                "created_at": (order_time + timedelta(days=refund_delay_days)).isoformat(),
                "reason": reason,
            })

        order = {
            "order_id": order_id,
            "customer_email": cust["email"],
            "created_at": order_time.isoformat(),
            "currency": currency,
            "total_price": round(total, 2),
            "source_name": source_name,
            "financial_status": financial_status,
            "cancelled_at": cancelled_at,
            "refunds": refunds,
            "line_items": line_items,
        }
        day_orders.append(order)
        shopify_orders.append(order)

        if is_subscription_renewal and cust["email"] in recharge_subs:
            recharge_subs[cust["email"]]["linked_shopify_order_id"] = order_id

    # once per day, snapshot subscription state changes for scripted scenarios
    if day == 8:
        for cust in REACTIVATION_CUSTOMERS:
            sub = recharge_subs[cust["email"]]
            old_sub_id = sub["subscription_id"]
            cancel_time = day_date + timedelta(hours=10)
            recharge_sub_history.append({**sub, "status": "cancelled", "cancelled_at": cancel_time.isoformat(),
                                          "cancellation_reason": "payment_failed_max_retries",
                                          "next_charge_date": None})
            # resubscribe within 48h under a NEW subscription id (mirrors real Recharge behavior)
            new_created = cancel_time + timedelta(hours=random.randint(6, 40))
            new_sub_id = f"RC-{100 + len(recharge_subs) + len(recharge_sub_history)}"
            recharge_subs[cust["email"]] = {
                "subscription_id": new_sub_id,
                "customer_email": cust["email"],
                "status": "active",
                "frequency_days": sub["frequency_days"],
                "created_at": new_created.isoformat(),
                "next_charge_date": (new_created + timedelta(days=sub["frequency_days"])).date().isoformat(),
                "cancelled_at": None,
                "cancellation_reason": None,
                "linked_shopify_order_id": None,
            }

    if day == 12:
        for cust in VOLUNTARY_CHURN_CUSTOMERS:
            sub = recharge_subs[cust["email"]]
            cancel_time = day_date + timedelta(hours=14)
            sub.update({"status": "cancelled", "cancelled_at": cancel_time.isoformat(),
                        "cancellation_reason": "customer_cancelled", "next_charge_date": None})
            SUBSCRIBERS.remove(cust)  # stop generating renewal orders for them

    if day == 15:
        for cust in PAUSED_CUSTOMERS:
            sub = recharge_subs[cust["email"]]
            sub.update({"status": "paused", "next_charge_date": None})
            SUBSCRIBERS.remove(cust)  # paused = no renewals, but NOT churned

    # ---- write this day's Shopify orders file (append-style: today's new facts only) ----
    day_str = day_date.date().isoformat()
    with open(OUT_DIR / f"shopify_orders_{day_str}.json", "w") as f:
        json.dump(day_orders, f, indent=2)
    shopify_daily_file_count += 1

    # ---- write this day's Recharge snapshot (full current state, not a delta) ----
    # Include every live subscription, plus any history rows that had already
    # been superseded/cancelled as of this day, so the file reflects reality
    # "as of end of day_date" -- not just what changed today.
    current_snapshot = list(recharge_subs.values()) + [
        h for h in recharge_sub_history
        if datetime.fromisoformat(h["cancelled_at"]).date() <= day_date.date()
    ]
    with open(OUT_DIR / f"recharge_subscriptions_{day_str}.json", "w") as f:
        json.dump(current_snapshot, f, indent=2)
    recharge_daily_file_count += 1

print(f"Shopify orders: {len(shopify_orders)} rows across {shopify_daily_file_count} daily files")
print(f"Recharge subscriptions: {recharge_daily_file_count} daily snapshot files "
      f"(final day has {len(current_snapshot)} subscription rows)")

# ---- Square POS ------------------------------------------------------------
square_rows = []   # full-run accumulation, kept only for the summary print
txn_counter = 9000
square_daily_file_count = 0

for day in range(NUM_DAYS):
    day_date = START_DATE + timedelta(days=day)
    n_txns = random.randint(*SQUARE_TXNS_PER_DAY)
    day_txns = []  # reset at the top of each day's iteration

    for _ in range(n_txns):
        txn_counter += 1
        txn_id = f"SQ-{txn_counter}"
        store = random.choice(STORES)
        txn_time = day_date + timedelta(hours=random.randint(7, 18), minutes=random.randint(0, 59))
        # Square exports local time with NO offset info in the field itself -- a real quirk
        local_time_str = txn_time.replace(tzinfo=None).isoformat()

        # ~30% of transactions are from a loyalty-registered customer (phone captured)
        phone = random.choice(LOYALTY_CUSTOMERS)["phone"] if random.random() < 0.30 else ""

        employee = f"EMP-{random.randint(1, 12):02d}"
        n_items = random.randint(1, 3)
        chosen = random.sample(PRODUCTS, n_items)
        for p in chosen:
            qty = random.randint(1, 2)
            discount = round(p["price"] * 0.1, 2) if random.random() < 0.1 else 0.00
            row = {
                "transaction_id": txn_id,
                "location_id": store,
                "item_sku": p["sku"],
                "item_name": p["name"],
                "qty": qty,
                "unit_price": p["price"],
                "discount": discount,
                "payment_type": random.choice(["card", "card", "card", "cash"]),
                "employee_id": employee,
                "created_at_local": local_time_str,
                "customer_phone": phone,
            }
            day_txns.append(row)
            square_rows.append(row)

    # ---- write this day's Square transactions file ----
    day_str = day_date.date().isoformat()
    if day_txns:
        with open(OUT_DIR / f"square_transactions_{day_str}.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(day_txns[0].keys()))
            writer.writeheader()
            writer.writerows(day_txns)
        square_daily_file_count += 1

print(f"Square line-item rows: {len(square_rows)} across {square_daily_file_count} daily files")

# ---- ShipStation -------------------------------------------------------------
shipstation_rows = []
ship_counter = 7000
carriers = ["UPS", "USPS", "FedEx"]

shippable_orders = [o for o in shopify_orders if o["cancelled_at"] is None]
sampled_for_shipping = random.sample(shippable_orders, int(len(shippable_orders) * 0.85))

for order in sampled_for_shipping:
    ship_counter += 1
    ship_id = f"SS-{ship_counter}"
    order_time = datetime.fromisoformat(order["created_at"])
    ship_date = order_time + timedelta(days=random.randint(0, 2))
    days_in_transit = random.randint(1, 5)

    refund_reasons = [r["reason"] for r in order["refunds"]]
    if "damaged_item" in refund_reasons or "product_mislabeled" in refund_reasons:
        status = random.choice(["delivered", "delivery_exception"])
    else:
        status = random.choices(
            ["delivered", "in_transit", "shipped", "delivery_exception"],
            weights=[70, 15, 10, 5],
        )[0]

    last_scan = ship_date + timedelta(days=days_in_transit)
    shipstation_rows.append({
        "shipment_id": ship_id,
        "shopify_order_id": order["order_id"],
        "tracking_number": fake.numerify("#" * random.choice([16, 20, 22])),
        "carrier": random.choice(carriers),
        "ship_date": ship_date.date().isoformat(),
        "status": status,
        "last_scan_at": last_scan.isoformat(),
    })

# ---- bucket ShipStation rows into daily files by ship_date ----
write_daily_files(shipstation_rows, lambda r: r["ship_date"], "shipstation_shipments")

print(f"ShipStation rows: {len(shipstation_rows)}")

# ---- Zendesk -----------------------------------------------------------------
zendesk_rows = []
ticket_counter = 3000

quality_subjects = [
    "My coffee tastes off, tastes stale",
    "Wrong grind size sent, whole bean expected",
    "Coffee doesn't taste like what I ordered",
]
shipping_subjects = ["Where is my box??", "Tracking hasn't updated in days", "Package says delivered but I don't have it"]
damaged_subjects = ["Bag arrived crushed", "Box was soaked/damaged in transit"]
cancel_subjects = ["Please cancel my subscription", "How do I pause my subscription?"]

mislabel_orders = [o for o in shopify_orders if any(r["reason"] == "product_mislabeled" for r in o["refunds"])]
for order in mislabel_orders:
    ticket_counter += 1
    order_time = datetime.fromisoformat(order["created_at"])
    ticket_time = order_time + timedelta(days=random.randint(1, 3))
    has_email = random.random() < 0.7
    zendesk_rows.append({
        "ticket_id": f"ZD-{ticket_counter}",
        "requester_email": order["customer_email"] if has_email else "",
        "subject": random.choice(quality_subjects),
        "created_at": ticket_time.isoformat(),
        "tags": "quality,refund_request",
        "related_order_id": order["order_id"],
    })

for _ in range(60):
    ticket_counter += 1
    day_date = START_DATE + timedelta(days=random.randint(0, NUM_DAYS - 1), hours=random.randint(7, 21))
    kind = random.choice(["shipping", "damaged", "cancel"])
    has_email = random.random() < 0.6
    has_order_link = random.random() < 0.4
    cust = random.choice(ONLINE_CUSTOMERS)
    subject = {"shipping": random.choice(shipping_subjects),
               "damaged": random.choice(damaged_subjects),
               "cancel": random.choice(cancel_subjects)}[kind]
    tag = {"shipping": "shipping,frustrated", "damaged": "damaged,refund_request", "cancel": "cancellation"}[kind]
    zendesk_rows.append({
        "ticket_id": f"ZD-{ticket_counter}",
        "requester_email": cust["email"] if has_email else "",
        "subject": subject,
        "created_at": day_date.isoformat(),
        "tags": tag,
        "related_order_id": random.choice(shopify_orders)["order_id"] if has_order_link else "",
    })

# ---- bucket Zendesk rows into daily files by created_at date ----
ZENDESK_FIELDNAMES = ["ticket_id", "requester_email", "subject", "created_at", "tags", "related_order_id"]
write_daily_files(zendesk_rows, lambda r: r["created_at"][:10], "zendesk_tickets", fieldnames=ZENDESK_FIELDNAMES)

print(f"Zendesk tickets: {len(zendesk_rows)}")
print("\nAll bronze files written to:", OUT_DIR)