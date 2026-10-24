"""
STEP 6: Graph Analytics — find who actually matters in the network.

WHY THIS STEP EXISTS:
Step 5 gave us a graph we can look at, but "looking at it" doesn't scale
past a handful of people, and raw connection-count (degree) can be
misleading — it doesn't account for HOW MUCH two people interacted, or
whether someone is a structurally important "bridge" even with few
connections. This step runs proper, well-established graph algorithms
(the same category of math Google used for PageRank) to score every
person's importance in specific, meaningful ways.

IMPORTANT FRAMING:
These scores are NOT accusations. A high score means "this person's
position in the network is mathematically unusual/central" — it is a
signal for a human investigator to look closer, nothing more. We use the
words "flagged for review" rather than anything implying guilt.

THREE MEASURES WE CALCULATE (all built into NetworkX — we don't
implement the algorithms ourselves, just call the library):

1. WEIGHTED DEGREE
   - Sum of edge weights touching a node (calls + transactions + mentions).
   - Answers: "How much total activity does this person have?"

2. BETWEENNESS CENTRALITY
   - How often a node sits on the shortest path between two OTHER nodes.
   - Answers: "Does this person bridge two groups that otherwise
     wouldn't be connected?" This is the measure most likely to catch a
     hidden, structurally-important person — like Sanjay Gupta in our data.

3. PAGERANK
   - A node's importance depends on the importance of the nodes it's
     connected to (not just the raw count).
   - Answers: "Is this person connected to other well-connected people?"

We also run COMMUNITY DETECTION (the Louvain algorithm) to automatically
group people into likely clusters/cells based on how densely connected
they are to each other versus everyone else.

OUTPUT:
  data/centrality_scores.json  -> every person's score on all 3 measures
  data/communities.json        -> which cluster/group each node belongs to
"""

import json
import pickle
import networkx as nx

with open("data/graph_simple.pkl", "rb") as f:
    graph = pickle.load(f)

# ---------------------------------------------------------------------------
# 1. Weighted degree — total activity per node
# ---------------------------------------------------------------------------
weighted_degree = dict(graph.degree(weight="weight"))

# ---------------------------------------------------------------------------
# 2. Betweenness centrality — bridge/broker score
#    We tell it to use "weight" so that stronger connections (e.g. 14 calls)
#    count as "closer" than a single one-off mention.
# ---------------------------------------------------------------------------
betweenness = nx.betweenness_centrality(graph, weight="weight", normalized=True)

# ---------------------------------------------------------------------------
# 3. PageRank — importance based on your neighbors' importance
# ---------------------------------------------------------------------------
pagerank = nx.pagerank(graph, weight="weight")

# ---------------------------------------------------------------------------
# Community detection (Louvain algorithm) — auto-group into likely clusters
# ---------------------------------------------------------------------------
communities = nx.community.louvain_communities(graph, weight="weight", seed=42)
community_map = {}
for i, group in enumerate(communities):
    for node in group:
        community_map[node] = i

# ---------------------------------------------------------------------------
# Combine everything into one scorecard per node, but only report on
# PEOPLE (not vehicles/locations) — those are important as connections,
# but scoring "how important is this vehicle" doesn't make sense here.
# ---------------------------------------------------------------------------
scorecards = []
for node in graph.nodes:
    if graph.nodes[node]["node_type"] != "Person":
        continue
    scorecards.append({
        "name": node,
        "weighted_degree": weighted_degree[node],
        "betweenness_centrality": round(betweenness[node], 4),
        "pagerank": round(pagerank[node], 4),
        "community_id": community_map[node],
    })

# Sort by betweenness first — that's the measure most likely to catch a
# hidden connector, which is the core "hidden relationship" goal of this project.
scorecards.sort(key=lambda x: -x["betweenness_centrality"])

with open("data/centrality_scores.json", "w") as f:
    json.dump(scorecards, f, indent=2)

with open("data/communities.json", "w") as f:
    json.dump({str(k): v for k, v in community_map.items()}, f, indent=2)

# ---------------------------------------------------------------------------
# Print a readable report
# ---------------------------------------------------------------------------
print("=" * 78)
print("PERSON SCORECARD  (sorted by betweenness = 'hidden bridge' score)")
print("=" * 78)
print(f"{'Name':<16}{'Weighted Degree':<18}{'Betweenness':<14}{'PageRank':<12}{'Community'}")
print("-" * 78)
for s in scorecards:
    print(f"{s['name']:<16}{s['weighted_degree']:<18}{s['betweenness_centrality']:<14}"
          f"{s['pagerank']:<12}{s['community_id']}")

top_by_betweenness = scorecards[0]
top_by_degree = max(scorecards, key=lambda x: x["weighted_degree"])

print("\n" + "=" * 78)
print("SUMMARY (for a human investigator to review — not an accusation):")
print("=" * 78)
print(f"- Highest RAW ACTIVITY:      {top_by_degree['name']} "
      f"(weighted degree {top_by_degree['weighted_degree']})")
print(f"- Highest BRIDGE/BROKER score: {top_by_betweenness['name']} "
      f"(betweenness {top_by_betweenness['betweenness_centrality']})")
print(f"\nNumber of communities detected: {len(communities)}")
for i, group in enumerate(communities):
    people_in_group = [n for n in group if graph.nodes[n]["node_type"] == "Person"]
    if people_in_group:
        print(f"  Community {i}: {', '.join(sorted(people_in_group))}")
