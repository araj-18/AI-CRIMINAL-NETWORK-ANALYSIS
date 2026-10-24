"""
STEP 8: Export Dashboard Data — package everything into one file the
dashboard can read.

WHY THIS STEP EXISTS:
Steps 1-7 produced several separate files (resolved_entities.json,
relationships.json, centrality_scores.json, communities.json,
anomalies.json...). A dashboard shouldn't have to know about 6 different
files and how they relate — it should just load ONE ready-to-use file.
This step is purely "gluing together" work: it combines everything into
a single dashboard_data.json, and also calculates where each node should
be DRAWN on screen (its x/y position), so the dashboard doesn't need to
run any layout algorithm itself — it just draws dots where we tell it to.

OUTPUT:
  dashboard/dashboard_data.json
"""

import json
import pickle
import networkx as nx

with open("data/graph_simple.pkl", "rb") as f:
    graph = pickle.load(f)

with open("data/centrality_scores.json") as f:
    centrality_scores = json.load(f)

with open("data/communities.json") as f:
    communities = json.load(f)

with open("data/anomalies.json") as f:
    anomalies = json.load(f)

with open("data/relationships.json") as f:
    relationships = json.load(f)

# ---------------------------------------------------------------------------
# Calculate on-screen positions for every node using the same layout
# algorithm we used for the preview image in Step 5, scaled to fit a
# 1000x700 canvas for the dashboard.
# ---------------------------------------------------------------------------
pos = nx.spring_layout(graph, seed=42, k=0.9)
xs = [p[0] for p in pos.values()]
ys = [p[1] for p in pos.values()]
x_min, x_max = min(xs), max(xs)
y_min, y_max = min(ys), max(ys)

def scale(value, vmin, vmax, out_min, out_max):
    if vmax == vmin:
        return (out_min + out_max) / 2
    return out_min + (value - vmin) / (vmax - vmin) * (out_max - out_min)

CANVAS_W, CANVAS_H, MARGIN = 1000, 650, 60

score_lookup = {s["name"]: s for s in centrality_scores}

nodes = []
for node in graph.nodes:
    x, y = pos[node]
    node_type = graph.nodes[node]["node_type"]
    entry = {
        "id": node,
        "type": node_type,
        "x": scale(x, x_min, x_max, MARGIN, CANVAS_W - MARGIN),
        "y": scale(y, y_min, y_max, MARGIN, CANVAS_H - MARGIN),
        "degree": graph.degree(node, weight="weight"),
    }
    if node in score_lookup:
        entry.update({
            "weighted_degree": score_lookup[node]["weighted_degree"],
            "betweenness_centrality": score_lookup[node]["betweenness_centrality"],
            "pagerank": score_lookup[node]["pagerank"],
            "community_id": score_lookup[node]["community_id"],
        })
    nodes.append(entry)

edges = []
for u, v, data in graph.edges(data=True):
    edges.append({"source": u, "target": v, "weight": data["weight"]})

# Attach the underlying evidence (every individual FIR/CDR/txn edge) so the
# dashboard can show "why" two nodes are connected when clicked.
evidence_by_pair = {}
for r in relationships:
    key = tuple(sorted([r["source"], r["target"]]))
    evidence_by_pair.setdefault(key, []).append(r)

for e in edges:
    key = tuple(sorted([e["source"], e["target"]]))
    e["evidence"] = evidence_by_pair.get(key, [])

# Attach which node(s) each anomaly involves, matched by name
for a in anomalies:
    a["people_involved"] = a["people_involved"]

dashboard_data = {
    "nodes": nodes,
    "edges": edges,
    "anomalies": anomalies,
    "canvas": {"width": CANVAS_W, "height": CANVAS_H},
}

import os
os.makedirs("dashboard", exist_ok=True)
with open("dashboard/dashboard_data.json", "w") as f:
    json.dump(dashboard_data, f, indent=2)

print(f"Exported {len(nodes)} nodes and {len(edges)} edges to dashboard/dashboard_data.json")
