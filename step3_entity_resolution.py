"""
STEP 3: Entity Resolution — figure out which mentions refer to the same person.

WHY THIS STEP EXISTS:
Step 2 gave us names as they literally appear in text: "Rahul Sharma",
"R. Sharma", etc. Our CDR file only has phone numbers, not names at all.
Our financial file has names, but no phone numbers.

If we don't resolve all of these to one canonical identity, our future
graph will have separate, disconnected nodes for what is actually ONE
real person — which defeats the whole point of finding hidden connections.

HOW IT WORKS:
1. We treat data/people_directory.csv as our "source of truth" — a known
   list of real people with their canonical name, alias, and phone number.
   (In a real system, this might come from a national ID database instead.)
2. For every name we found in FIRs (Step 2) or financial transactions, we
   use FUZZY STRING MATCHING (RapidFuzz) to score how similar it is to each
   known canonical name. If the best match scores above a threshold, we
   treat it as the same person.
3. For CDR data, we don't need fuzzy matching at all — phone numbers are
   exact identifiers, so we just look them up directly in the directory.

OUTPUT:
  data/resolved_entities.json
  -> a canonical ID for every person mentioned anywhere in our data,
     with all their known aliases and source phone numbers attached.
"""

import json
import csv
from rapidfuzz import process, fuzz

# ---------------------------------------------------------------------------
# Load our "source of truth" — the known people directory from Step 1.
# ---------------------------------------------------------------------------
directory = []
with open("data/people_directory.csv") as f:
    for row in csv.DictReader(f):
        directory.append(row)

canonical_names = [p["name"] for p in directory]
phone_to_name = {p["phone"]: p["name"] for p in directory}

FUZZY_MATCH_THRESHOLD = 85  # 0-100 scale; below this, we don't trust the match


def resolve_name(raw_name: str):
    """
    Given a name as it appeared in raw text (e.g. "R. Sharma"), find the
    closest matching canonical name from our directory using fuzzy matching.
    Returns (canonical_name, confidence_score) or (None, 0) if nothing is
    close enough to trust.
    """
    match = process.extractOne(raw_name, canonical_names, scorer=fuzz.token_sort_ratio)
    if match is None:
        return None, 0
    matched_name, score, _ = match
    if score >= FUZZY_MATCH_THRESHOLD:
        return matched_name, score
    return None, score


# ---------------------------------------------------------------------------
# Build a canonical record for every real person, and track every raw
# mention we can tie back to them (from FIRs and financial transactions).
# ---------------------------------------------------------------------------
canonical_people = {
    p["name"]: {
        "canonical_name": p["name"],
        "known_alias": p["alias"],
        "phone": p["phone"],
        "mentions_in_firs": [],
        "mentions_in_transactions": [],
    }
    for p in directory
}

unresolved_mentions = []  # names we saw but couldn't confidently match

# ---- Resolve names mentioned in FIRs (from Step 2's output) ----
with open("data/extracted_entities.json") as f:
    fir_entities = json.load(f)

for fir in fir_entities:
    for raw_name in fir["people"]:
        matched_name, score = resolve_name(raw_name)
        if matched_name:
            canonical_people[matched_name]["mentions_in_firs"].append({
                "fir_id": fir["fir_id"],
                "raw_text": raw_name,
                "match_confidence": score,
            })
        else:
            unresolved_mentions.append({"source": "FIR", "raw_text": raw_name, "best_score": score})

# ---- Resolve names mentioned in financial transactions ----
with open("data/financial_txns.csv") as f:
    for row in csv.DictReader(f):
        for raw_name in (row["sender_name"], row["receiver_name"]):
            matched_name, score = resolve_name(raw_name)
            if matched_name:
                canonical_people[matched_name]["mentions_in_transactions"].append({
                    "raw_text": raw_name,
                    "amount_inr": row["amount_inr"],
                    "timestamp": row["timestamp"],
                    "match_confidence": score,
                })
            else:
                unresolved_mentions.append({"source": "financial_txn", "raw_text": raw_name, "best_score": score})

# ---- Attach CDR call counts using exact phone number lookup (no fuzzy matching needed) ----
call_counts = {}
with open("data/cdr.csv") as f:
    for row in csv.DictReader(f):
        for phone in (row["caller"], row["callee"]):
            call_counts[phone] = call_counts.get(phone, 0) + 1

for name, record in canonical_people.items():
    record["total_calls_in_cdr"] = call_counts.get(record["phone"], 0)

# ---------------------------------------------------------------------------
# Save the result
# ---------------------------------------------------------------------------
output = {
    "resolved_people": list(canonical_people.values()),
    "unresolved_mentions": unresolved_mentions,
}
with open("data/resolved_entities.json", "w") as f:
    json.dump(output, f, indent=2)

# ---- Print a readable summary ----
print(f"Resolved {len(canonical_people)} canonical people:\n")
for name, record in canonical_people.items():
    print(f"  {name}")
    print(f"    Phone: {record['phone']}  |  Calls in CDR: {record['total_calls_in_cdr']}")
    print(f"    Mentioned in {len(record['mentions_in_firs'])} FIR(s), "
          f"{len(record['mentions_in_transactions'])} transaction(s)")
print(f"\n{len(unresolved_mentions)} mention(s) could not be confidently resolved.")
if unresolved_mentions:
    for u in unresolved_mentions:
        print(f"    [{u['source']}] '{u['raw_text']}' (best score: {u['best_score']:.0f})")
