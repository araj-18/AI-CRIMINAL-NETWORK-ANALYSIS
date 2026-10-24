"""
STEP 1b: Generate synthetic Social Media Intelligence (SOCMINT) data.

WHY THIS STEP EXISTS:
Your original project scope listed SOCMINT (social media posts, connections,
geotags) as one of the data sources investigators use. We hadn't built that
yet. Like Step 1, we generate FAKE data here — real social media scraping
raises serious legal and platform Terms-of-Service issues even for
legitimate law-enforcement tools, so a real system would need proper legal
authority and official data-sharing agreements with platforms, not a
scraping script. For our demo, synthetic data teaches the same pipeline
concepts safely.

WHAT IT PRODUCES:
  data/social_posts.csv        -> fake posts, some with location tags
  data/social_connections.csv  -> fake "friend/follower" links between people

WHAT'S WOVEN IN FOR OUR DEMO STORY:
Sanjay Gupta (our "hidden connector") is friends with Rahul Sharma on
social media, AND once posts from the same location as a Rahul Sharma FIR
mention — giving our pipeline a THIRD independent source (after CDR and
financial records) that ties them together.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(7)

PEOPLE = ["Rahul Sharma", "Amit Verma", "Sanjay Gupta", "Priya Nair", "Vikram Singh"]
LOCATIONS = ["Andheri Market", "MG Road", "Sector 12 Warehouse", "Central Bus Depot", "Lakeview Apartments"]

POST_TEMPLATES = [
    "Great evening out with friends.",
    "Traffic is terrible today, stuck for an hour.",
    "Anyone know a good place to eat nearby?",
    "Missing the monsoon already.",
    "New phone, who dis.",
    "Long day at work, finally home.",
]

# ---------------------------------------------------------------------------
# 1. Social media posts — mostly harmless noise, with a couple of
#    geotagged posts placed deliberately to overlap with FIR locations.
# ---------------------------------------------------------------------------
posts = []
for i in range(25):
    person = random.choice(PEOPLE)
    has_location = random.random() < 0.4
    post = {
        "person_name": person,
        "post_text": random.choice(POST_TEMPLATES),
        "location_tag": random.choice(LOCATIONS) if has_location else "",
        "timestamp": (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d %H:%M:%S"),
        "platform": random.choice(["Instagram", "X", "Facebook"]),
    }
    posts.append(post)

# Deliberately add: Sanjay Gupta geotagged at the same location as a
# Rahul Sharma FIR mention (MG Road), a few days before the calls started.
posts.append({
    "person_name": "Sanjay Gupta",
    "post_text": "Meeting someone here, back soon.",
    "location_tag": "MG Road",
    "timestamp": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    "platform": "Instagram",
})

with open("data/social_posts.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["person_name", "post_text", "location_tag", "timestamp", "platform"])
    writer.writeheader()
    writer.writerows(posts)

# ---------------------------------------------------------------------------
# 2. Social connections ("friends"/"follows") — structured, like a CDR but
#    for social platforms instead of phone calls.
# ---------------------------------------------------------------------------
connections = []

# background noise: some random connections
pairs_seen = set()
while len(connections) < 6:
    a, b = random.sample(PEOPLE, 2)
    key = tuple(sorted([a, b]))
    if key in pairs_seen:
        continue
    pairs_seen.add(key)
    connections.append({
        "person_a": a,
        "person_b": b,
        "platform": random.choice(["Instagram", "Facebook"]),
        "connection_type": random.choice(["friends", "follows"]),
    })

# deliberate: Sanjay Gupta <-> Rahul Sharma are social media "friends" too.
# Remove any random connection between them first, so we control this
# specific pair's relation_type exactly (avoids claiming "friends" when
# the random generator happened to produce "follows" instead).
connections = [
    c for c in connections
    if tuple(sorted([c["person_a"], c["person_b"]])) != ("Rahul Sharma", "Sanjay Gupta")
]
connections.append({
    "person_a": "Rahul Sharma",
    "person_b": "Sanjay Gupta",
    "platform": "Facebook",
    "connection_type": "friends",
})

with open("data/social_connections.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["person_a", "person_b", "platform", "connection_type"])
    writer.writeheader()
    writer.writerows(connections)

print(f"Generated {len(posts)} social media posts -> data/social_posts.csv")
print(f"Generated {len(connections)} social connections -> data/social_connections.csv")
print("\nNote: Sanjay Gupta <-> Rahul Sharma now appear connected via a THIRD")
print("independent source (social media), in addition to calls and a financial transaction.")
