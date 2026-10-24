"""
STEP 10: Backend API — serve our data live, instead of baking it into a file.

WHY THIS STEP EXISTS:
Step 9's dashboard works great, but the data is FROZEN at the moment we
generated it — if new FIRs/CDRs came in, we'd have to re-run all 9 steps
and rebuild the HTML file by hand. A real system needs a backend that can
be queried on demand and updated independently of whoever's looking at it.

This is also what lets OTHER tools use our system — not just our one
dashboard. Any app that can make a web request (a mobile app, another
team's internal tool, etc.) could now plug into this.

WHAT THIS GIVES US THAT A STATIC FILE CAN'T:
- Always reflects the latest data on disk (just re-run steps 1-8, no need
  to rebuild the dashboard file)
- Multiple different tools/screens could all query the same live backend
- This is the shape a real production system would actually take

ENDPOINTS:
  GET  /people                 -> list every known person + their scores
  GET  /person/{name}          -> full detail on one person
  GET  /search?q=...           -> fuzzy name search
  GET  /graph                  -> full graph (nodes + edges) for drawing
  GET  /anomalies              -> all flagged patterns

HOW TO RUN THIS FOR REAL (on your own machine):
  uvicorn step10_api:app --reload
  Then open http://127.0.0.1:8000/docs in your browser — FastAPI
  auto-generates an interactive page where you can try every endpoint.
"""

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rapidfuzz import process, fuzz

app = FastAPI(title="Criminal Network Analysis API")

# Allow a browser-based frontend (like our dashboard, if we pointed it at
# this API instead of embedded data) to call this API from a different
# origin. In a real deployment you'd restrict this to known frontend URLs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load all our pipeline's output ONCE when the server starts, and keep it
# in memory. For a bigger real system this would be a database instead —
# but for our scale (a handful of people), an in-memory dict is genuinely
# fine and much simpler.
# ---------------------------------------------------------------------------
with open("data/centrality_scores.json") as f:
    CENTRALITY = {p["name"]: p for p in json.load(f)}

with open("data/relationships.json") as f:
    RELATIONSHIPS = json.load(f)

with open("data/anomalies.json") as f:
    ANOMALIES = json.load(f)

with open("dashboard/dashboard_data.json") as f:
    GRAPH_DATA = json.load(f)

ALL_NAMES = list(CENTRALITY.keys())


def get_connections(name: str):
    """Every relationship edge touching this person, in a readable form."""
    results = []
    for r in RELATIONSHIPS:
        if r["source"] == name:
            results.append({"with": r["target"], "relation": r["relation"], "evidence_type": r["evidence_type"]})
        elif r["target"] == name:
            results.append({"with": r["source"], "relation": r["relation"], "evidence_type": r["evidence_type"]})
    return results


def get_flags(name: str):
    return [a for a in ANOMALIES if name in a["people_involved"]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Criminal Network Analysis API is running.",
        "endpoints": ["/people", "/person/{name}", "/search?q=...", "/graph", "/anomalies"],
    }


@app.get("/people")
def list_people():
    """Every known person, with their centrality scores, sorted by bridge score."""
    people = sorted(CENTRALITY.values(), key=lambda p: -p["betweenness_centrality"])
    return {"count": len(people), "people": people}


@app.get("/person/{name}")
def get_person(name: str):
    """Full detail on one person: scores, connections, and any flags."""
    if name not in CENTRALITY:
        raise HTTPException(status_code=404, detail=f"No person found with name '{name}'")
    return {
        "scorecard": CENTRALITY[name],
        "connections": get_connections(name),
        "flags": get_flags(name),
    }


@app.get("/search")
def search_people(q: str):
    """Fuzzy search — lets you find someone even with a typo or partial name."""
    if not q:
        return {"results": []}
    matches = process.extract(q, ALL_NAMES, scorer=fuzz.WRatio, limit=5)
    return {"results": [{"name": name, "match_score": round(score, 1)} for name, score, _ in matches]}


@app.get("/graph")
def get_graph():
    """Full graph data (nodes with positions + edges) for drawing a visualization."""
    return GRAPH_DATA


@app.get("/anomalies")
def list_anomalies():
    """Every flagged pattern found by Step 7's anomaly detection."""
    return {"count": len(ANOMALIES), "anomalies": ANOMALIES}


# ---------------------------------------------------------------------------
# Plain-text, human-readable endpoints.
# Everything above returns JSON, which is meant for other programs to read
# (like our dashboard, or any future tool). These two endpoints instead
# return plain formatted TEXT, meant to be read directly by a person --
# useful when you just want to glance at results in a browser without
# clicking through Swagger's "Try it out" JSON viewer.
# ---------------------------------------------------------------------------
from fastapi.responses import PlainTextResponse


@app.get("/report", response_class=PlainTextResponse)
def full_report():
    """A plain-English summary of the whole network -- open this URL directly
    in your browser (no 'Try it out' needed) to just read the results."""
    lines = []
    lines.append("=" * 60)
    lines.append("CRIMINAL NETWORK ANALYSIS -- SUMMARY REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"People tracked: {len(CENTRALITY)}")
    lines.append(f"Flagged patterns: {len(ANOMALIES)}")
    lines.append("")
    lines.append("-- PEOPLE, RANKED BY BRIDGE SCORE (most structurally important first) --")
    people = sorted(CENTRALITY.values(), key=lambda p: -p["betweenness_centrality"])
    for p in people:
        lines.append(
            f"  {p['name']:<16} activity={p['weighted_degree']:<5} "
            f"bridge_score={p['betweenness_centrality']:<7} pagerank={p['pagerank']}"
        )
    lines.append("")
    lines.append("-- FLAGGED PATTERNS (for human review, not accusations) --")
    if not ANOMALIES:
        lines.append("  None found.")
    for a in ANOMALIES:
        lines.append(f"  [{a['type']}] {', '.join(a['people_involved'])}")
        lines.append(f"      {a['description']}")
    lines.append("")
    lines.append("For details on one person, visit /person/{name}/report")
    return "\n".join(lines)


@app.get("/person/{name}/report", response_class=PlainTextResponse)
def person_report(name: str):
    """Plain-text version of the person detail endpoint -- readable directly
    in a browser, e.g. /person/Sanjay Gupta/report"""
    if name not in CENTRALITY:
        return f"No person found with name '{name}'.\nTry /people to see all valid names."

    p = CENTRALITY[name]
    lines = []
    lines.append("=" * 60)
    lines.append(f"PERSON REPORT: {name}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total activity (weighted degree): {p['weighted_degree']}")
    lines.append(f"Bridge score (betweenness):        {p['betweenness_centrality']}")
    lines.append(f"Influence (PageRank):               {p['pagerank']}")
    lines.append(f"Community group:                    #{p['community_id']}")
    lines.append("")

    flags = get_flags(name)
    lines.append(f"-- FLAGGED FOR REVIEW ({len(flags)}) --")
    if not flags:
        lines.append("  None.")
    for f in flags:
        lines.append(f"  [{f['type']}] {f['description']}")
        lines.append(f"      Note: {f['note']}")
    lines.append("")

    connections = get_connections(name)
    # Group by "who", not by individual event -- nobody wants to read
    # "Rahul Sharma via CALLED" fourteen separate times.
    grouped = {}
    for c in connections:
        key = c["with"]
        grouped.setdefault(key, {"relations": set(), "count": 0})
        grouped[key]["relations"].add(c["relation"])
        grouped[key]["count"] += 1

    lines.append(f"-- CONNECTIONS ({len(grouped)} people/places) --")
    for who, info in sorted(grouped.items(), key=lambda x: -x[1]["count"]):
        relation_list = ", ".join(sorted(info["relations"]))
        lines.append(f"  {who:<20} {relation_list}  (x{info['count']})")

    return "\n".join(lines)
