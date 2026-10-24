"""
STEP 2: Extract entities from the FIR text (Named Entity Recognition).

WHY THIS STEP EXISTS:
Step 1 gave us FIRs as plain paragraphs. A computer can't "see" that
"Rahul Sharma" is a person and "MG Road" is a place just by reading text —
we have to explicitly extract those pieces. This step turns unstructured
text into structured data: a list of (entity_type, entity_text) pairs per FIR.

HOW IT WORKS:
- spaCy's built-in model already recognizes general categories like
  PERSON, GPE (places), ORG (organizations) — it was pre-trained on lots
  of general English text, so it's decent at these out of the box.
- Vehicle numbers and phone numbers are NOT something spaCy knows about by
  default (they're domain-specific), so we detect those ourselves with
  regular expressions (regex) — simple pattern matching on the text.

OUTPUT:
  data/extracted_entities.json
  -> one entry per FIR, listing every entity found and its type.
"""

import json
import re
import spacy

nlp = spacy.load("en_core_web_sm")

# Regex pattern for Indian-style vehicle plates, e.g. "MH-12-AB-1234"
VEHICLE_PATTERN = re.compile(r"\b[A-Z]{2}-\d{2}-[A-Z]{2}-\d{4}\b")

# Regex pattern for a 10-digit phone number
PHONE_PATTERN = re.compile(r"\b\d{10}\b")

with open("data/firs.txt") as f:
    raw_text = f.read()

# Each FIR is separated by a blank line in our file
fir_entries = [entry.strip() for entry in raw_text.split("\n\n") if entry.strip()]

all_results = []

for entry in fir_entries:
    # split "FIR-1000: <text>" into an ID and the body text
    fir_id, _, body = entry.partition(": ")

    doc = nlp(body)

    people = sorted({ent.text for ent in doc.ents if ent.label_ == "PERSON"})
    locations = sorted({ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "FAC")})
    orgs = sorted({ent.text for ent in doc.ents if ent.label_ == "ORG"})
    dates = sorted({ent.text for ent in doc.ents if ent.label_ == "DATE"})

    vehicles = sorted(set(VEHICLE_PATTERN.findall(body)))
    phones = sorted(set(PHONE_PATTERN.findall(body)))

    all_results.append({
        "fir_id": fir_id,
        "text": body,
        "people": people,
        "locations": locations,
        "organizations": orgs,
        "dates": dates,
        "vehicles": vehicles,
        "phones": phones,
    })

with open("data/extracted_entities.json", "w") as f:
    json.dump(all_results, f, indent=2)

# ---- Print a readable summary so we can sanity-check the results ----
print(f"Processed {len(all_results)} FIRs.\n")
for r in all_results:
    print(f"{r['fir_id']}:")
    print(f"  People:    {r['people']}")
    print(f"  Locations: {r['locations']}")
    print(f"  Vehicles:  {r['vehicles']}")
    print()
