"""Tiny retrieval smoke evaluation; requires downloading the real embedding model."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.store import Store

cases = [
    ("How are PDF page numbers retained in search results?", "Atlas architecture"),
    ("Will my indexed documents survive a Space rebuild?", "Deployment and tradeoffs"),
    ("What prevents web requests to internal network addresses?", "Security and evidence"),
]
with tempfile.TemporaryDirectory() as directory:
    store = Store(path=directory)
    try:
        for file in (Path(__file__).resolve().parents[1] / "sample_docs").glob("*.txt"):
            store.ingest(file.stem.replace("_", " "), "sample", [(None, file.read_text(encoding="utf-8"))], public=True)
        results = []
        for query, expected in cases:
            found = store.search(query)
            rank = next((i+1 for i,s in enumerate(found) if s["title"] == expected), None)
            results.append({"question":query,"expected":expected,"rank":rank})
        print(json.dumps({"fixture_size":len(cases),"hit_at_5":sum(r["rank"] is not None for r in results)/len(cases),"mrr":sum(1/r["rank"] if r["rank"] else 0 for r in results)/len(cases),"results":results}, indent=2))
    finally:
        store.client.close()
