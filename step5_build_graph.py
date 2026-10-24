"""
STEP 5: Build the Graph — turn our list of edges into a real network.

WHY THIS STEP EXISTS:
Step 4 gave us a flat LIST of edges: (source, relation, target, metadata).
A list is not a graph yet — it's just rows in a table. This step loads
those rows into an actual graph STRUCTURE (using the NetworkX library),
where nodes and edges are connected objects you can traverse, query, and
run algorithms on. This is the data structure everything from here on
(centrality, community detection, visualization) depends on.

WE BUILD TWO VERSIONS OF THE GRAPH:

1. graph_full   (a MultiDiGraph)
   - Keeps EVERY individual edge separately, with its full metadata
     (which FIR, what timestamp, call duration, amount, etc).
   - "Multi" = allows more than one edge between the same two nodes
     (e.g., 14 separate CALLED edges between Rahul and Sanjay).
   - "Di" = directed (A called B is different from B called A).
   - This is our "evidence" version — good for looking up WHY two nodes
     are connected, but harder to run standard graph algorithms on
     directly (most centrality algorithms expect a simpler graph).

2. graph_simple (a plain, undirected, WEIGHTED Graph)
   - Collapses all edges between the same two nodes into ONE edge with
     a "weight" = how many times they were connected across all sources.
   - This is what Step 6 (centrality, community detection) will actually
     run on — those algorithms need this simpler structure to work well.

OUTPUT:
  data/graph_full.pkl     -> the detailed graph (for evidence lookups)
  data/graph_simple.pkl   -> the simplified weighted graph (for analytics)
  data/network_preview.png -> a picture of the graph, so we can SEE it
"""

import json
import re
import pickle
import networkx as nx
import matplotlib.pyplot as plt

VEHICLE_PATTERN = re.compile(r"\b[A-Z]{2}-\d{2}-[A-Z]{2}-\d{4}\b")

with open("data/relationships.json") as f:
    edges = json.load(f)

with open("data/resolved_entities.json") as f:
    resolved = json.load(f)
canonical_names = {p["canonical_name"] for p in resolved["resolved_people"]}


def node_type(name: str) -> str:
    """Classify a node as Person, Vehicle, or Location based on what it looks like."""
    if name in canonical_names:
        return "Person"
    if VEHICLE_PATTERN.match(name):
        return "Vehicle"
    return "Location"


# ---------------------------------------------------------------------------
# Build graph_full: every edge kept separately, with metadata
# ---------------------------------------------------------------------------
graph_full = nx.MultiDiGraph()

for e in edges:
    src, tgt = e["source"], e["target"]
    if src not in graph_full:
        graph_full.add_node(src, node_type=node_type(src))
    if tgt not in graph_full:
        graph_full.add_node(tgt, node_type=node_type(tgt))

    metadata = {k: v for k, v in e.items() if k not in ("source", "target", "relation")}
    graph_full.add_edge(src, tgt, relation=e["relation"], **metadata)

# ---------------------------------------------------------------------------
# Build graph_simple: collapsed to one weighted edge per connected pair
# ---------------------------------------------------------------------------
graph_simple = nx.Graph()

for e in edges:
    src, tgt = e["source"], e["target"]
    if src not in graph_simple:
        graph_simple.add_node(src, node_type=node_type(src))
    if tgt not in graph_simple:
        graph_simple.add_node(tgt, node_type=node_type(tgt))

    if graph_simple.has_edge(src, tgt):
        graph_simple[src][tgt]["weight"] += 1
    else:
        graph_simple.add_edge(src, tgt, weight=1)

# ---------------------------------------------------------------------------
# Save both graphs so later steps can load them without rebuilding
# ---------------------------------------------------------------------------
with open("data/graph_full.pkl", "wb") as f:
    pickle.dump(graph_full, f)

with open("data/graph_simple.pkl", "wb") as f:
    pickle.dump(graph_simple, f)

# ---------------------------------------------------------------------------
# Draw a picture of the graph so we can actually SEE what we built
# ---------------------------------------------------------------------------
plt.figure(figsize=(11, 8))
pos = nx.spring_layout(graph_simple, seed=42, k=0.8)  # spring_layout spaces nodes out naturally

color_map = {"Person": "#C1272D", "Vehicle": "#3E4C59", "Location": "#8A93A6"}
node_colors = [color_map[graph_simple.nodes[n]["node_type"]] for n in graph_simple.nodes]
node_sizes = [300 + 60 * graph_simple.degree(n) for n in graph_simple.nodes]  # busier nodes drawn bigger

nx.draw_networkx_edges(graph_simple, pos, alpha=0.4, width=1)
nx.draw_networkx_nodes(graph_simple, pos, node_color=node_colors, node_size=node_sizes)
nx.draw_networkx_labels(graph_simple, pos, font_size=8, font_weight="bold")

plt.title("Our Crime Network Graph (bigger dot = more connections)")
plt.axis("off")
plt.tight_layout()
plt.savefig("data/network_preview.png", dpi=150)

# ---------------------------------------------------------------------------
# Print a summary
# ---------------------------------------------------------------------------
print(f"graph_full:   {graph_full.number_of_nodes()} nodes, {graph_full.number_of_edges()} edges (every call/txn kept separate)")
print(f"graph_simple: {graph_simple.number_of_nodes()} nodes, {graph_simple.number_of_edges()} edges (collapsed, weighted)")

print("\nNode types:")
type_counts = {}
for n in graph_simple.nodes:
    t = graph_simple.nodes[n]["node_type"]
    type_counts[t] = type_counts.get(t, 0) + 1
for t, c in type_counts.items():
    print(f"  {t}: {c}")

print("\nMost connected nodes (by raw degree, i.e. number of distinct connections):")
degrees = sorted(graph_simple.degree, key=lambda x: -x[1])
for name, degree in degrees[:5]:
    print(f"  {name}: {degree} connections")

print("\nSaved: data/graph_full.pkl, data/graph_simple.pkl, data/network_preview.png")
