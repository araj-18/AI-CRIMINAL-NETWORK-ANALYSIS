"""
STEP 9: Build the Dashboard — package everything into one webpage.

WHY THIS STEP EXISTS:
Everything so far has lived in JSON files and terminal output. That's fine
for us as developers, but useless to an actual investigator (or a judge at
a hackathon). This step generates ONE self-contained HTML file with the
graph, search, scorecards, and flags all built in — double-click it and
it opens in any browser. No web server, no installation, no internet
connection needed, because we embed the data directly inside the page
instead of loading it separately (which avoids browser security
restrictions on opening local files).

WHAT YOU CAN DO IN THE DASHBOARD:
- See the whole network as a graph (same idea as our Step 5 preview image,
  but interactive)
- Search for a person by name
- Click any person to see their centrality scores, connections, and any
  flagged patterns involving them
- See the anomaly list (Step 7's output) front and center
"""

import json

with open("dashboard/dashboard_data.json") as f:
    data = json.load(f)

data_json = json.dumps(data)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Criminal Network Analysis — Investigator View</title>
<style>
  :root {
    --ink: #1b2430;
    --ink-soft: #262f3d;
    --mist: #f4f5f7;
    --mist-card: #e8eaee;
    --crimson: #c1272d;
    --slate: #3e4c59;
    --muted: #62707d;
    --white: #ffffff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--mist);
    color: #232a33;
  }
  header {
    background: var(--ink);
    color: var(--white);
    padding: 18px 28px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 3px solid var(--crimson);
  }
  header h1 {
    font-family: Georgia, "Cambria", serif;
    font-size: 22px;
    margin: 0;
    font-weight: 700;
  }
  header .meta { color: #aeb7c4; font-size: 13px; }
  .layout {
    display: grid;
    grid-template-columns: 260px 1fr 320px;
    height: calc(100vh - 62px);
  }
  .sidebar {
    background: var(--white);
    border-right: 1px solid var(--mist-card);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .sidebar-header { padding: 16px; border-bottom: 1px solid var(--mist-card); }
  .sidebar-header input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--mist-card);
    border-radius: 4px;
    font-size: 13px;
  }
  .person-list { overflow-y: auto; flex: 1; }
  .person-row {
    padding: 10px 16px;
    border-bottom: 1px solid var(--mist-card);
    cursor: pointer;
    font-size: 13px;
  }
  .person-row:hover { background: var(--mist); }
  .person-row.active { background: var(--ink); color: var(--white); }
  .person-row .name { font-weight: 600; }
  .person-row .sub { color: var(--muted); font-size: 11px; margin-top: 2px; }
  .person-row.active .sub { color: #aeb7c4; }
  .graph-panel { position: relative; background: var(--white); }
  #graph { width: 100%; height: 100%; display: block; }
  .node-label {
    font-size: 11px;
    font-weight: 600;
    fill: #232a33;
    pointer-events: none;
  }
  .edge-line { stroke: #c7cdd6; stroke-width: 1.5; }
  .edge-line.highlighted { stroke: var(--crimson); stroke-width: 2.5; }
  .node-circle { cursor: pointer; stroke: var(--white); stroke-width: 2; }
  .node-circle.dimmed { opacity: 0.25; }
  .detail-panel {
    background: var(--white);
    border-left: 1px solid var(--mist-card);
    padding: 20px;
    overflow-y: auto;
  }
  .detail-panel h2 {
    font-family: Georgia, "Cambria", serif;
    font-size: 19px;
    margin: 0 0 4px 0;
  }
  .empty-state { color: var(--muted); font-size: 13px; line-height: 1.6; margin-top: 40px; }
  .score-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 16px 0;
  }
  .score-box {
    background: var(--mist);
    padding: 10px 12px;
    border-radius: 4px;
  }
  .score-box .label { font-size: 11px; color: var(--muted); margin-bottom: 3px; }
  .score-box .value { font-size: 18px; font-weight: 700; color: var(--ink); }
  .section-title {
    font-size: 12px;
    font-weight: 700;
    color: var(--slate);
    margin: 20px 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--mist-card);
  }
  .connection-row {
    font-size: 13px;
    padding: 6px 0;
    border-bottom: 1px solid var(--mist-card);
    display: flex;
    justify-content: space-between;
  }
  .connection-row .rel { color: var(--muted); font-size: 11px; }
  .flag-banner {
    background: #fdecec;
    border: 1px solid var(--crimson);
    border-radius: 4px;
    padding: 10px 12px;
    margin-bottom: 10px;
    font-size: 12.5px;
  }
  .flag-banner .flag-title { font-weight: 700; color: var(--crimson); margin-bottom: 3px; }
  .anomaly-strip {
    background: var(--ink);
    color: var(--white);
    padding: 10px 28px;
    font-size: 13px;
    display: flex;
    gap: 24px;
    align-items: center;
    border-bottom: 1px solid #2e3947;
  }
  .anomaly-strip .tag {
    background: var(--crimson);
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
  }
</style>
</head>
<body>

<header>
  <h1>Criminal Network Analysis — Investigator View</h1>
  <div class="meta" id="header-meta"></div>
</header>

<div id="anomaly-strip-container"></div>

<div class="layout">
  <div class="sidebar">
    <div class="sidebar-header">
      <input type="text" id="search" placeholder="Search by name...">
    </div>
    <div class="person-list" id="person-list"></div>
  </div>

  <div class="graph-panel">
    <svg id="graph"></svg>
  </div>

  <div class="detail-panel" id="detail-panel">
    <div class="empty-state">Click a person on the left or in the graph to see their details, connections, and any flagged patterns.</div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;

const nodesById = {};
DATA.nodes.forEach(n => nodesById[n.id] = n);

let selectedId = null;

// ---- Header meta ----
const peopleCount = DATA.nodes.filter(n => n.type === "Person").length;
document.getElementById("header-meta").textContent =
  peopleCount + " people tracked · " + DATA.edges.length + " connections · " + DATA.anomalies.length + " flagged pattern(s)";

// ---- Anomaly strip ----
const stripContainer = document.getElementById("anomaly-strip-container");
DATA.anomalies.forEach(a => {
  const strip = document.createElement("div");
  strip.className = "anomaly-strip";
  strip.innerHTML = '<span class="tag">FLAGGED</span><span>' + a.description + '</span>';
  strip.onclick = () => selectNode(a.people_involved[0]);
  strip.style.cursor = "pointer";
  stripContainer.appendChild(strip);
});

// ---- Sidebar person list ----
const listEl = document.getElementById("person-list");
function renderPersonList(filter) {
  listEl.innerHTML = "";
  const people = DATA.nodes
    .filter(n => n.type === "Person")
    .filter(n => !filter || n.id.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => (b.betweenness_centrality || 0) - (a.betweenness_centrality || 0));

  people.forEach(p => {
    const row = document.createElement("div");
    row.className = "person-row" + (p.id === selectedId ? " active" : "");
    row.innerHTML = '<div class="name">' + p.id + '</div>' +
      '<div class="sub">activity: ' + (p.weighted_degree || 0) +
      ' &middot; bridge score: ' + (p.betweenness_centrality || 0).toFixed(2) + '</div>';
    row.onclick = () => selectNode(p.id);
    listEl.appendChild(row);
  });
}
renderPersonList("");

document.getElementById("search").addEventListener("input", (e) => renderPersonList(e.target.value));

// ---- Graph drawing (SVG) ----
const svg = document.getElementById("graph");
const NS = "http://www.w3.org/2000/svg";
const typeColor = { Person: "#c1272d", Vehicle: "#3e4c59", Location: "#9aa5b1" };

function drawGraph() {
  svg.innerHTML = "";
  svg.setAttribute("viewBox", "0 0 " + DATA.canvas.width + " " + DATA.canvas.height);

  // edges first (so nodes draw on top)
  DATA.edges.forEach(e => {
    const line = document.createElementNS(NS, "line");
    const a = nodesById[e.source], b = nodesById[e.target];
    line.setAttribute("x1", a.x); line.setAttribute("y1", a.y);
    line.setAttribute("x2", b.x); line.setAttribute("y2", b.y);
    const isHighlighted = selectedId && (e.source === selectedId || e.target === selectedId);
    line.setAttribute("class", "edge-line" + (isHighlighted ? " highlighted" : ""));
    svg.appendChild(line);
  });

  // nodes
  DATA.nodes.forEach(n => {
    const g = document.createElementNS(NS, "g");

    const circle = document.createElementNS(NS, "circle");
    circle.setAttribute("cx", n.x);
    circle.setAttribute("cy", n.y);
    const radius = n.type === "Person" ? 14 + Math.min(n.degree, 20) : 10;
    circle.setAttribute("r", radius);
    circle.setAttribute("fill", typeColor[n.type]);
    let cls = "node-circle";
    if (selectedId && n.id !== selectedId) {
      const connected = DATA.edges.some(e =>
        (e.source === selectedId && e.target === n.id) ||
        (e.target === selectedId && e.source === n.id));
      if (!connected) cls += " dimmed";
    }
    circle.setAttribute("class", cls);
    circle.onclick = () => selectNode(n.id);
    g.appendChild(circle);

    const label = document.createElementNS(NS, "text");
    label.setAttribute("x", n.x);
    label.setAttribute("y", n.y + radius + 14);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "node-label");
    label.textContent = n.id;
    g.appendChild(label);

    svg.appendChild(g);
  });
}

// ---- Detail panel ----
function selectNode(id) {
  selectedId = id;
  renderPersonList(document.getElementById("search").value);
  drawGraph();
  renderDetail(id);
}

function renderDetail(id) {
  const n = nodesById[id];
  const panel = document.getElementById("detail-panel");

  if (n.type !== "Person") {
    panel.innerHTML = "<h2>" + n.id + "</h2><div class='empty-state'>This is a " + n.type.toLowerCase() +
      ", linked to " + n.degree + " connection(s) in the network.</div>";
    return;
  }

  let html = "<h2>" + n.id + "</h2>";
  html += "<div class='score-grid'>" +
    "<div class='score-box'><div class='label'>Total Activity</div><div class='value'>" + (n.weighted_degree || 0) + "</div></div>" +
    "<div class='score-box'><div class='label'>Bridge Score</div><div class='value'>" + (n.betweenness_centrality || 0).toFixed(2) + "</div></div>" +
    "<div class='score-box'><div class='label'>Influence (PageRank)</div><div class='value'>" + (n.pagerank || 0).toFixed(3) + "</div></div>" +
    "<div class='score-box'><div class='label'>Group</div><div class='value'>#" + n.community_id + "</div></div>" +
  "</div>";

  // Flags involving this person
  const flags = DATA.anomalies.filter(a => a.people_involved.includes(id));
  if (flags.length) {
    html += "<div class='section-title'>Flagged for Review</div>";
    flags.forEach(f => {
      html += "<div class='flag-banner'><div class='flag-title'>" + f.type.replace(/_/g, " ") + "</div>" +
        f.description + "<br><em>" + f.note + "</em></div>";
    });
  }

  // Connections
  html += "<div class='section-title'>Connections</div>";
  const related = DATA.edges.filter(e => e.source === id || e.target === id);
  related.forEach(e => {
    const other = e.source === id ? e.target : e.source;
    const relTypes = [...new Set(e.evidence.map(ev => ev.relation))].join(", ");
    html += "<div class='connection-row'><span>" + other + "</span><span class='rel'>" + relTypes + " (" + e.weight + ")</span></div>";
  });

  panel.innerHTML = html;
}

drawGraph();
</script>

</body>
</html>
"""

html = html.replace("__DATA_JSON__", data_json)

with open("dashboard/index.html", "w") as f:
    f.write(html)

print("Dashboard built: dashboard/index.html")
print("Open this file directly in any web browser (double-click it) — no server needed.")
