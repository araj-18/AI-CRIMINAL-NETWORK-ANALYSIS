# AI-Powered Criminal Network Analysis System

An end-to-end pipeline that turns fragmented, fake (synthetic) crime data — police reports, phone records, financial transactions, and social media — into a connected network graph, automatically identifies key influencers, flags suspicious patterns, and presents it all through an interactive investigator dashboard.

**Built as a working proof of concept — every script below has been run and its output verified, not just written.**

---

## The Core Result

Using generated synthetic data, one person ("Sanjay Gupta") was deliberately never named in any written police report — but the system still surfaced him as the **#2 most structurally important person in the network** by fusing phone records, financial records, and social media data. No single data source alone would have found him. This is the central proof-of-concept result: **cross-source fusion finds hidden connections that isolated analysis misses.**

---

## Quick Start

```bash
# 1. Install dependencies
pip install spacy rapidfuzz fastapi uvicorn networkx matplotlib
python -m spacy download en_core_web_sm

# 2. Run the full pipeline, in order
python3 step1_generate_data.py
python3 step1b_generate_socmint_data.py
python3 step2_extract_entities.py
python3 step3_entity_resolution.py
python3 step4_extract_relationships.py
python3 step5_build_graph.py
python3 step6_graph_analytics.py
python3 step7_anomaly_detection.py
python3 step8_export_dashboard_data.py
python3 step9_build_dashboard.py

# 3. View the results
open dashboard/index.html          # (or just double-click it)

# 4. (Optional) Run the live API
python -m uvicorn step10_api:app --reload
# then visit http://127.0.0.1:8000/docs
```

---

## Folder Structure

```
crime_network/
├── step1_generate_data.py            # Fake FIRs, CDRs, financial transactions
├── step1b_generate_socmint_data.py   # Fake social media posts & connections
├── step2_extract_entities.py         # NER: pull names/places/vehicles from text
├── step3_entity_resolution.py        # Fuzzy-match name variants to one identity
├── step4_extract_relationships.py    # Turn co-mentions/calls/txns into graph edges
├── step5_build_graph.py              # Build the NetworkX graph + preview image
├── step6_graph_analytics.py          # Centrality + community detection
├── step7_anomaly_detection.py        # Circular transactions + call spikes
├── step8_export_dashboard_data.py    # Package everything for the dashboard
├── step9_build_dashboard.py          # Generate the self-contained HTML dashboard
├── step10_api.py                     # FastAPI backend (live queries)
├── data/                             # All generated data + intermediate outputs
│   ├── firs.txt, cdr.csv, financial_txns.csv, people_directory.csv
│   ├── social_posts.csv, social_connections.csv
│   ├── extracted_entities.json, resolved_entities.json, relationships.json
│   ├── graph_full.pkl, graph_simple.pkl, network_preview.png
│   ├── centrality_scores.json, communities.json, anomalies.json
└── dashboard/
    ├── dashboard_data.json           # Consolidated data for the UI
    └── index.html                    # The dashboard itself — open this in a browser
```

**Rule of thumb:** `.py` files live in the root folder, all generated data lives in `data/`, and the dashboard lives in `dashboard/`.

---

## Pipeline Stages Explained

| # | Stage | What It Does | Key Technique |
|---|---|---|---|
| 1 | Data Generation | Creates realistic fake FIRs, call records, financial transactions | Templated random generation |
| 1b | SOCMINT Generation | Creates fake social media posts & friend/follow connections | Templated random generation |
| 2 | Entity Extraction | Pulls names, locations, vehicles out of police report text | spaCy NER + regex |
| 3 | Entity Resolution | Matches name variants/aliases to one canonical identity | RapidFuzz fuzzy string matching |
| 4 | Relationship Extraction | Turns co-mentions, calls, and transactions into graph edges | Rule-based extraction |
| 5 | Graph Construction | Builds the actual network structure | NetworkX (MultiDiGraph + weighted Graph) |
| 6 | Graph Analytics | Scores who's important and finds sub-groups | Betweenness centrality, PageRank, Louvain community detection |
| 7 | Anomaly Detection | Flags circular money flows and call-frequency spikes | Graph cycle detection, time-windowed counting |
| 8 | Data Export | Consolidates everything + computes visual layout | NetworkX spring_layout |
| 9 | Dashboard | Interactive search/graph/scorecard UI | Vanilla HTML/CSS/JS, no server needed |
| 10 | Backend API | Live queryable endpoints | FastAPI |

---

## Known Limitations (Be Upfront About These)

- **Synthetic data only.** All names, records, and patterns are fabricated for this demo. No real individuals, cases, or data are involved.
- **NER isn't perfect.** Off-the-shelf spaCy occasionally misclassifies names as locations (seen during testing) — a real system would need domain fine-tuning or human review of low-confidence extractions.
- **Anomaly detection needed tuning.** An early version of circular-transaction detection produced 16 false positives on a 5-person graph before adding time-window and cycle-length constraints. This is a genuine, documented lesson: naive pattern detection on small graphs generates noise.
- **Centrality results are illustrative, not universal.** Betweenness centrality did NOT initially surface the "hidden" person until a third data source (social media) was added — a good demonstration that no single metric or data source tells the whole story.
- **Scores are signals for human review, not conclusions.** Nothing in this system labels anyone as guilty of anything. High centrality or a flagged pattern means "an investigator should look at this," not "this person did something wrong."

---

## Tech Stack

- **NLP:** spaCy (`en_core_web_sm`)
- **Entity resolution:** RapidFuzz
- **Graph & analytics:** NetworkX (betweenness centrality, PageRank, Louvain community detection)
- **Backend:** FastAPI
- **Frontend:** Vanilla HTML/CSS/JS (SVG-based graph rendering, no external dependencies)
- **Visualization (dev-side):** Matplotlib

---

## Extending This Project

- Add more data sources (surveillance reports, criminal history databases) by following the same pattern as Step 1b.
- Swap NetworkX for Neo4j if you need a persistent graph database for larger-scale data.
- Fine-tune a custom NER model on real domain text (with proper data governance) instead of the general-purpose spaCy model.
- Add authentication/RBAC to `step10_api.py` before any real deployment.
