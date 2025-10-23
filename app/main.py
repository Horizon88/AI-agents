"""Flask entry point for the e-discovery platform."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List

from flask import Flask, flash, render_template, request

from .collector import DocumentCollector
from .insights import InsightEngine
from .parser import DocumentParser
from .storage import DocumentStorage

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

BASE_DIR = Path(os.environ.get("EDISCOVERY_BASE_DIR", "/tmp/ediscovery"))
DATA_DIR = BASE_DIR
COLLECTED_DIR = DATA_DIR / "collected"
DB_PATH = DATA_DIR / "ediscovery.db"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "development-secret")
app.config["UPLOAD_FOLDER"] = str(COLLECTED_DIR)

DATA_DIR.mkdir(parents=True, exist_ok=True)
COLLECTED_DIR.mkdir(parents=True, exist_ok=True)

collector = DocumentCollector(COLLECTED_DIR)
parser = DocumentParser()
storage = DocumentStorage(DB_PATH)
insights = InsightEngine(storage)
insights.refresh_index()


def _collect_sources(sources: str) -> List[str]:
    return [line.strip() for line in sources.splitlines() if line.strip()]


@app.route("/", methods=["GET", "POST"])
def index():
    messages: List[str] = []
    if request.method == "POST":
        action = request.form.get("action")
        try:
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
                flash(
                    "No relevant information found in the documents."
                    if query.strip()
                    else "Enter a query."
                )
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
        except Exception:  # pragma: no cover - defensive logging for production
            logger.exception("Error handling action '%s'", action)
            flash("An error occurred while processing your request.")
    return render_template("index.html", messages=messages)


@app.route("/health")
def health() -> str:
    return json.dumps({"status": "ok"})
