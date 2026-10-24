"""
STEP 4: Relationship Extraction — turn "who's connected to whom" into edges.

WHY THIS STEP EXISTS:
Step 3 gave us a clean list of WHO exists (canonical people). But a list of
people alone tells us nothing about the network. This step is where we
figure out HOW they're connected, and produce the actual (A, RELATION, B)
triples that will become edges in our graph in Step 5.

We pull relationships from three different sources, each handled
differently because the data looks different:

  1. FIRs (text)        -> people mentioned in the same report are likely
                            connected somehow. We use simple keyword rules
                            to guess a relation type (rule-based relation
                            extraction — no fancy ML needed for a demo).
  2. CDR (call records)  -> each row IS a relationship already: a phone
                            call between two numbers. We just look up which
                            canonical person each phone number belongs to.
  3. Financial txns      -> same idea: each row is a "sent money to" edge.

OUTPUT:
  data/relationships.json
  -> a flat list of edges, each with a source, target, relation type,
     and supporting metadata (which FIR, what timestamp, etc.) so we can
     always trace an edge back to the evidence that produced it.
"""

import json
import csv
from rapidfuzz import process, fuzz

FUZZY_MATCH_THRESHOLD = 85

# ---------------------------------------------------------------------------
# Load what Step 3 already resolved: canonical people + phone lookup.
# ---------------------------------------------------------------------------
with open("data/resolved_entities.json") as f:
    resolved = json.load(f)

canonical_names = [p["canonical_name"] for p in resolved["resolved_people"]]
phone_to_name = {p["phone"]: p["canonical_name"] for p in resolved["resolved_people"]}


def resolve_name(raw_name: str):
    match = process.extractOne(raw_name, canonical_names, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= FUZZY_MATCH_THRESHOLD:
        return match[0]
    return None


edges = []  # every edge we find goes here as a dict


def add_edge(source, relation, target, **metadata):
    edges.append({
        "source": source,
        "relation": relation,
        "target": target,
        **metadata,
    })


# ---------------------------------------------------------------------------
# 1. Relationships from FIR text
#    Rule: if two people are named in the same FIR, they're connected.
#    The exact relation TYPE is guessed from keywords in the sentence —
#    this is simple rule-based relation extraction.
# ---------------------------------------------------------------------------
with open("data/extracted_entities.json") as f:
    fir_entities = json.load(f)

for fir in fir_entities:
    text_lower = fir["text"].lower()

    if "arguing" in text_lower:
        relation = "HAD_ALTERCATION_WITH"
    elif "seen" in text_lower:
        relation = "SEEN_WITH"
    else:
        relation = "MENTIONED_TOGETHER"

    # Resolve every raw name found in this FIR to a canonical person
    resolved_people_in_fir = []
    for raw_name in fir["people"]:
        canonical = resolve_name(raw_name)
        if canonical:
            resolved_people_in_fir.append(canonical)
    resolved_people_in_fir = sorted(set(resolved_people_in_fir))

    # Connect every pair of people mentioned in the same FIR
    for i in range(len(resolved_people_in_fir)):
        for j in range(i + 1, len(resolved_people_in_fir)):
            add_edge(
                resolved_people_in_fir[i], relation, resolved_people_in_fir[j],
                source_document=fir["fir_id"], evidence_type="FIR"
            )

    # Connect each person to any vehicle mentioned in the same FIR
    for person in resolved_people_in_fir:
        for vehicle in fir["vehicles"]:
            add_edge(person, "LINKED_TO_VEHICLE", vehicle,
                      source_document=fir["fir_id"], evidence_type="FIR")

    # Connect each person to any location mentioned in the same FIR
    for person in resolved_people_in_fir:
        for location in fir["locations"]:
            add_edge(person, "PRESENT_AT", location,
                      source_document=fir["fir_id"], evidence_type="FIR")

# ---------------------------------------------------------------------------
# 2. Relationships from CDR (call records) — exact, no fuzzy matching needed
# ---------------------------------------------------------------------------
with open("data/cdr.csv") as f:
    for row in csv.DictReader(f):
        caller_name = phone_to_name.get(row["caller"])
        callee_name = phone_to_name.get(row["callee"])
        if caller_name and callee_name:
            add_edge(
                caller_name, "CALLED", callee_name,
                timestamp=row["timestamp"], duration_sec=row["duration_sec"],
                evidence_type="CDR"
            )

# ---------------------------------------------------------------------------
# 3. Relationships from financial transactions
# ---------------------------------------------------------------------------
with open("data/financial_txns.csv") as f:
    for row in csv.DictReader(f):
        sender = resolve_name(row["sender_name"]) or row["sender_name"]
        receiver = resolve_name(row["receiver_name"]) or row["receiver_name"]
        add_edge(
            sender, "TRANSACTED_WITH", receiver,
            amount_inr=row["amount_inr"], timestamp=row["timestamp"],
            evidence_type="FINANCIAL"
        )

# ---------------------------------------------------------------------------
# 4. Relationships from SOCMINT (social media) — two kinds:
#    a) direct friend/follow connections between people
#    b) a person "present at" a location via a geotagged post — this uses
#       the SAME relation type (PRESENT_AT) as our FIR location edges,
#       because to the graph, "present at a place" means the same thing
#       regardless of which data source reported it.
# ---------------------------------------------------------------------------
import os

if os.path.exists("data/social_connections.csv"):
    with open("data/social_connections.csv") as f:
        for row in csv.DictReader(f):
            person_a = resolve_name(row["person_a"]) or row["person_a"]
            person_b = resolve_name(row["person_b"]) or row["person_b"]
            relation = "SOCIAL_FRIENDS_WITH" if row["connection_type"] == "friends" else "SOCIAL_FOLLOWS"
            add_edge(person_a, relation, person_b,
                     platform=row["platform"], evidence_type="SOCMINT")

if os.path.exists("data/social_posts.csv"):
    with open("data/social_posts.csv") as f:
        for row in csv.DictReader(f):
            if not row["location_tag"]:
                continue
            person = resolve_name(row["person_name"]) or row["person_name"]
            add_edge(person, "PRESENT_AT", row["location_tag"],
                     timestamp=row["timestamp"], platform=row["platform"], evidence_type="SOCMINT")

# ---------------------------------------------------------------------------
# Save + summarize
# ---------------------------------------------------------------------------
with open("data/relationships.json", "w") as f:
    json.dump(edges, f, indent=2)

print(f"Extracted {len(edges)} relationships (edges) total.\n")

by_type = {}
for e in edges:
    by_type[e["relation"]] = by_type.get(e["relation"], 0) + 1

print("Breakdown by relationship type:")
for relation, count in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {relation:<22} {count}")

print("\nSample edges:")
for e in edges[:5]:
    print(f"  ({e['source']}) --[{e['relation']}]--> ({e['target']})   [from {e['evidence_type']}]")
