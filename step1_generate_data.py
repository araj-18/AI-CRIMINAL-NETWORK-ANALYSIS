"""
STEP 1: Generate synthetic (fake) crime data.

WHY THIS STEP EXISTS:
We don't have real FIRs, phone records, or bank data (and shouldn't use real
data even if we had it). Everything downstream — NER, graph building,
analytics — needs *some* data to work on. This script creates realistic-
looking fake data so we have a safe sandbox to build and test the whole
pipeline on.

WHAT IT PRODUCES:
  data/firs.txt              -> fake police report narratives (unstructured text)
  data/cdr.csv               -> fake call detail records (structured)
  data/financial_txns.csv    -> fake bank transactions (structured)

The data is deliberately built with a few "hidden" connections woven in,
so that later steps (graph + analytics) have something interesting to find.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)  # fixed seed = same fake data every time we run this, for reproducibility

# ---------------------------------------------------------------------------
# A small cast of fake people. In a real system these would come from real
# records; here we hand-write them so we can control the "story" the data
# tells (e.g., who is secretly connected to whom).
# ---------------------------------------------------------------------------
PEOPLE = [
    {"name": "Rahul Sharma",  "alias": "R. Sharma",   "phone": "9876500001"},
    {"name": "Amit Verma",    "alias": "Amit V.",     "phone": "9876500002"},
    {"name": "Sanjay Gupta",  "alias": "S. Gupta",    "phone": "9876500003"},  # the "hidden" connector
    {"name": "Priya Nair",    "alias": "Priya N.",    "phone": "9876500004"},
    {"name": "Vikram Singh",  "alias": "Vikram S.",   "phone": "9876500005"},
]

LOCATIONS = ["Andheri Market", "MG Road", "Sector 12 Warehouse", "Central Bus Depot", "Lakeview Apartments"]
VEHICLES = ["MH-12-AB-1234", "DL-04-CD-5678", "KA-05-EF-9012"]

# ---------------------------------------------------------------------------
# 1. FAKE FIRs (unstructured text) — this is what our NER step will read.
#    Notice: Sanjay Gupta is NEVER named directly next to Rahul in these FIRs.
#    He only shows up via phone/financial records — that's the "hidden link"
#    the later graph analytics step should be able to surface.
# ---------------------------------------------------------------------------
fir_templates = [
    "On {date}, a complaint was filed regarding a theft near {loc}. "
    "Witnesses reported seeing {p1} and {p2} near the scene shortly before the incident. "
    "A vehicle matching {vehicle} was seen parked nearby.",

    "FIR registered on {date}: {p1} was seen arguing with {p2} at {loc}. "
    "Local shopkeepers stated this was not the first such altercation.",

    "On {date}, surveillance near {loc} recorded {p1} meeting an unidentified group. "
    "No further identification was possible from the footage.",

    "Complaint dated {date}: household goods reported missing from {loc}. "
    "{p1} is listed as a person of interest based on prior history in the area.",
]

def random_date(start_days_ago=60, end_days_ago=1):
    d = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=d)).strftime("%d %B %Y")

firs = []
named_people = [p["name"] for p in PEOPLE if p["name"] != "Sanjay Gupta"]  # keep Sanjay out of FIR text on purpose
for i in range(8):
    template = random.choice(fir_templates)
    p1, p2 = random.sample(named_people, 2)
    fir_text = template.format(
        date=random_date(),
        loc=random.choice(LOCATIONS),
        p1=p1,
        p2=p2,
        vehicle=random.choice(VEHICLES),
    )
    firs.append(f"FIR-{1000+i}: {fir_text}")

with open("data/firs.txt", "w") as f:
    f.write("\n\n".join(firs))

# ---------------------------------------------------------------------------
# 2. FAKE CALL DETAIL RECORDS (CDR) — structured data.
#    This is where Sanjay Gupta's hidden connection actually shows up:
#    Rahul Sharma calls Sanjay Gupta's number many times in a short window,
#    even though no FIR ever mentions them together.
# ---------------------------------------------------------------------------
cdr_rows = []
base_time = datetime.now() - timedelta(days=5)

# the "hidden link" pattern: Rahul <-> Sanjay, 14 calls in 2 days
rahul = next(p for p in PEOPLE if p["name"] == "Rahul Sharma")
sanjay = next(p for p in PEOPLE if p["name"] == "Sanjay Gupta")
for i in range(14):
    call_time = base_time + timedelta(hours=random.uniform(0, 48))
    cdr_rows.append({
        "caller": rahul["phone"],
        "callee": sanjay["phone"],
        "timestamp": call_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": random.randint(15, 300),
    })

# some normal, everyday-looking calls between other people (background noise)
for _ in range(20):
    p1, p2 = random.sample(PEOPLE, 2)
    call_time = base_time + timedelta(hours=random.uniform(-100, 100))
    cdr_rows.append({
        "caller": p1["phone"],
        "callee": p2["phone"],
        "timestamp": call_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_sec": random.randint(10, 600),
    })

with open("data/cdr.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["caller", "callee", "timestamp", "duration_sec"])
    writer.writeheader()
    writer.writerows(cdr_rows)

# ---------------------------------------------------------------------------
# 3. FAKE FINANCIAL TRANSACTIONS — structured data.
#    This is how we'll later "resolve" Sanjay's phone number to his name:
#    a bank transfer record links his phone number-linked account to his name.
# ---------------------------------------------------------------------------
txn_rows = []
for _ in range(15):
    p1, p2 = random.sample(PEOPLE, 2)
    txn_time = datetime.now() - timedelta(days=random.randint(1, 90))
    txn_rows.append({
        "sender_name": p1["name"],
        "receiver_name": p2["name"],
        "amount_inr": random.choice([500, 1500, 2000, 5000, 10000, 25000]),
        "timestamp": txn_time.strftime("%Y-%m-%d %H:%M:%S"),
    })

# a record that ties Sanjay Gupta's name to identifying info, for entity resolution later
txn_rows.append({
    "sender_name": "Sanjay Gupta",
    "receiver_name": "Amit Verma",
    "amount_inr": 8000,
    "timestamp": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
})

with open("data/financial_txns.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["sender_name", "receiver_name", "amount_inr", "timestamp"])
    writer.writeheader()
    writer.writerows(txn_rows)

# ---------------------------------------------------------------------------
# Also save the "ground truth" people list — later steps will need to know
# each person's name + phone number to link CDR data (which only has phone
# numbers) back to named people.
# ---------------------------------------------------------------------------
with open("data/people_directory.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "alias", "phone"])
    writer.writeheader()
    writer.writerows(PEOPLE)

print("Done. Files created in data/:")
print("  - firs.txt              (", len(firs), "fake police reports )")
print("  - cdr.csv               (", len(cdr_rows), "call records, includes a hidden Rahul<->Sanjay pattern )")
print("  - financial_txns.csv    (", len(txn_rows), "transactions )")
print("  - people_directory.csv  (", len(PEOPLE), "known people, name<->phone lookup )")
