"""Flask entry point for the e-discovery platform."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from flask import Flask, flash, render_template, request

from .collector import DocumentCollector
from .insights import InsightEngine
from .parser import DocumentParser
from .storage import DocumentStorage

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
COLLECTED_DIR = DATA_DIR / "collected"
DB_PATH = DATA_DIR / "ediscovery.db"

app = Flask(__name__)
app.secret_key = "change-this-secret"

DATA_DIR.mkdir(exist_ok=True)
COLLECTED_DIR.mkdir(parents=True, exist_ok=True)

collector = DocumentCollector(COLLECTED_DIR)
parser = DocumentParser()
storage = DocumentStorage(DB_PATH)
insights = InsightEngine(storage)


def _collect_sources(sources: str) -> List[str]:
    return [line.strip() for line in sources.splitlines() if line.strip()]


@app.route("/", methods=["GET", "POST"])
def index():
    messages: List[str] = []
    if request.method == "POST":
        action = request.form.get("action")
        if action == "collect":
            sources_text = request.form.get("sources", "")
            collected = collector.collect(_collect_sources(sources_text))
            parsed_docs = parser.parse_documents([doc.local_path for doc in collected])
            storage.store_documents(parsed_docs)
            insights.refresh_index()
            messages.append(f"Collected and parsed {len(parsed_docs)} document(s).")
        elif action == "query":
            query = request.form.get("query", "")
            results = insights.answer_query(query)
            if results:
                return render_template(
                    "index.html",
                    insights=results,
                    query=query,
                )
            flash("No relevant information found in the documents." if query.strip() else "Enter a query.")
        elif action == "upload":
            file = request.files.get("document")
            if file and file.filename:
                destination = COLLECTED_DIR / Path(file.filename).name
                file.save(destination)
                parsed_docs = parser.parse_documents([destination])
                storage.store_documents(parsed_docs)
                insights.refresh_index()
                messages.append(f"Uploaded and parsed {len(parsed_docs)} document(s).")
            else:
                flash("No file selected for upload.")
        else:
            flash("Unsupported action.")
    return render_template("index.html", messages=messages)


@app.route("/health")
def health() -> str:
    return json.dumps({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
