"""
STEP 7: Anomaly Detection — flag suspicious PATTERNS, not suspicious PEOPLE.

WHY THIS STEP EXISTS:
Steps 5-6 found who's structurally important in the network. But some red
flags aren't about a person's overall position — they're about a specific
BEHAVIOR PATTERN that's suspicious regardless of who's involved. This step
looks for two classic, well-known patterns:

1. CIRCULAR MONEY TRANSFERS
   Money going A -> B -> C -> back to A (a "cycle") is a classic
   money-laundering red flag — it moves funds through multiple accounts
   to obscure where they originally came from. We detect this using
   basic GRAPH CYCLE DETECTION: build a directed graph of "who paid whom"
   and ask the graph library to find any loops.

2. UNUSUAL CALLING PATTERNS
   A sudden burst of calls between two people in a short time window can
   indicate urgent coordination (e.g., planning something) rather than
   routine contact. We detect this with simple counting: if two people
   called each other more than N times within a short window, flag it.

IMPORTANT: like Step 6, these are FLAGS FOR HUMAN REVIEW, not proof of
wrongdoing. Legitimate reasons can also produce these patterns (repaying
a shared expense in a loop, a family emergency causing many calls, etc).
A human investigator always makes the final call.

OUTPUT:
  data/anomalies.json -> every flagged pattern, with the evidence behind it
"""

import csv
import json
from datetime import datetime
import networkx as nx

CALL_SPIKE_THRESHOLD = 10       # more than this many calls between 2 people...
CALL_SPIKE_WINDOW_HOURS = 72    # ...within this time window = flagged

anomalies = []

# ---------------------------------------------------------------------------
# 1. Circular money transfers — cycle detection on the transaction graph
# ---------------------------------------------------------------------------
txn_graph = nx.DiGraph()

with open("data/financial_txns.csv") as f:
    for row in csv.DictReader(f):
        txn_graph.add_edge(row["sender_name"], row["receiver_name"],
                            amount_inr=row["amount_inr"], timestamp=row["timestamp"])

# simple_cycles finds every loop in the directed graph, e.g. A -> B -> C -> A.
# NOTE: on a small, densely-connected graph, this can return a LOT of cycles
# that are mathematically real but practically meaningless (e.g. a 5-person
# loop that only exists because everyone happened to pay everyone once).
# Real money-laundering detection tightens this in two ways, which we do too:
#   1. Only look at SHORT cycles (2-3 hops) — that's what real layering looks
#      like: money bouncing through a couple of accounts quickly, not a long
#      coincidental chain through everyone in the dataset.
#   2. Only flag cycles where the transactions happened close together in
#      TIME — money laundered through a loop moves fast, not over months.
MAX_CYCLE_LENGTH = 3
MAX_CYCLE_TIMESPAN_DAYS = 14

all_cycles = list(nx.simple_cycles(txn_graph, length_bound=MAX_CYCLE_LENGTH))

for cycle in all_cycles:
    if len(cycle) < 2:
        continue

    # Check how close together in time this cycle's transactions happened
    cycle_edges = list(zip(cycle, cycle[1:] + cycle[:1]))
    timestamps = []
    for u, v in cycle_edges:
        ts = datetime.strptime(txn_graph[u][v]["timestamp"], "%Y-%m-%d %H:%M:%S")
        timestamps.append(ts)
    timespan_days = (max(timestamps) - min(timestamps)).days

    if timespan_days > MAX_CYCLE_TIMESPAN_DAYS:
        continue  # spread out over too long a period to look like real layering

    anomalies.append({
        "type": "CIRCULAR_MONEY_TRANSFER",
        "people_involved": cycle,
        "description": f"Money appears to flow in a loop through: {' -> '.join(cycle + [cycle[0]])} "
                        f"(all within {timespan_days} day(s))",
        "severity": "medium",
        "note": "Could indicate layering, or could be coincidental repayments — needs human review.",
    })

# ---------------------------------------------------------------------------
# 2. Unusual calling patterns — count calls per pair within a time window
# ---------------------------------------------------------------------------
# CDR data only has phone numbers, not names — we translate using the
# lookup Step 3 already built, so our report is human-readable.
with open("data/resolved_entities.json") as f:
    resolved = json.load(f)
phone_to_name = {p["phone"]: p["canonical_name"] for p in resolved["resolved_people"]}

calls_by_pair = {}  # (personA, personB) -> list of call timestamps

with open("data/cdr.csv") as f:
    for row in csv.DictReader(f):
        name_a = phone_to_name.get(row["caller"], row["caller"])
        name_b = phone_to_name.get(row["callee"], row["callee"])
        pair = tuple(sorted([name_a, name_b]))  # order doesn't matter for "how often do they talk"
        timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        calls_by_pair.setdefault(pair, []).append(timestamp)

for pair, timestamps in calls_by_pair.items():
    timestamps.sort()
    # slide a window across the sorted timestamps looking for a burst
    for i in range(len(timestamps)):
        window_calls = [t for t in timestamps if 0 <= (t - timestamps[i]).total_seconds() / 3600 <= CALL_SPIKE_WINDOW_HOURS]
        if len(window_calls) >= CALL_SPIKE_THRESHOLD:
            anomalies.append({
                "type": "UNUSUAL_CALL_FREQUENCY",
                "people_involved": list(pair),
                "description": f"{len(window_calls)} calls between {pair[0]} and {pair[1]} "
                                f"within a {CALL_SPIKE_WINDOW_HOURS}-hour window "
                                f"(starting {window_calls[0].strftime('%Y-%m-%d %H:%M')})",
                "severity": "medium",
                "note": "Could indicate urgent coordination, or could be routine for close contacts — needs human review.",
            })
            break  # found one spike for this pair, no need to report every overlapping window

# ---------------------------------------------------------------------------
# Save + report
# ---------------------------------------------------------------------------
with open("data/anomalies.json", "w") as f:
    json.dump(anomalies, f, indent=2)

print(f"Found {len(anomalies)} flagged pattern(s):\n")
if not anomalies:
    print("  (None found in this dataset — that's a valid result, not an error.")
    print("   Not every dataset will contain these specific patterns.)")
for a in anomalies:
    print(f"[{a['type']}] severity: {a['severity']}")
    print(f"  People: {', '.join(a['people_involved'])}")
    print(f"  {a['description']}")
    print(f"  Note: {a['note']}\n")
