# E-Discovery Platform

This project provides a lightweight e-discovery platform tailored for legal disputes. It collects documents from local paths or URLs, parses their contents, stores the structured data in SQLite, and exposes a retrieval-augmented question answering interface through a Flask web UI.

## Features

- **Document collection** from local files or downloadable URLs with safe local storage
- **Multi-format parsing** for PDF, plain text, Markdown/RTF, and EML email files
- **Structured storage** in SQLite with documents and paragraph-level sections
- **Insight generation** using TF-IDF retrieval with grounded citations from the source text
- **Flask web interface** for uploading documents, providing source lists, and querying insights
- **Unit tests** covering document parsing and insight retrieval flows

## Project Structure

```
app/
  collector.py     # Document collection utilities
  parser.py        # File format parsers and metadata extraction
  storage.py       # SQLite persistence layer
  insights.py      # TF-IDF search engine providing grounded insights
  main.py          # Flask entry point and view logic
  templates/
    index.html     # Simple UI for collection, upload, and query

tests/
  test_parser.py   # Parser unit tests
  test_insights.py # Insight engine unit tests
```

## Getting Started

### Prerequisites

- Python 3.9+
- Recommended virtual environment (``python -m venv .venv``)

### Installation

```bash
pip install -r requirements.txt
```

If you prefer manual installation, the core dependencies are:

- Flask
- PyPDF2
- gunicorn
- scikit-learn

### Running the Platform

```bash
export FLASK_APP=app.main:app
gunicorn app.main:app --bind 0.0.0.0:8000
```

Gunicorn serves the Flask application locally using the same WSGI entry point that Vercel invokes. You can still run `flask run` for quick iteration if desired.

Navigate to `http://localhost:8000` (or the port you choose) to access the UI. Upload files or provide paths/URLs to build the corpus, then ask natural-language questions. Each insight cites the originating document and provides the supporting snippet.

### Environment Configuration

- `FLASK_SECRET_KEY`: Set this in production (e.g., the Vercel dashboard) to secure session cookies.
- `EDISCOVERY_BASE_DIR`: Optional override for the runtime storage base directory. Defaults to `/tmp/ediscovery` so that serverless targets such as Vercel can persist data in the writable temporary file system. Point this at a persistent location for long-running servers.

### Running Tests

```bash
python -m unittest
```

## Extending the Platform

- Add new parsers by extending `DocumentParser.parse_documents` to recognise more file types (e.g., DOCX).
- Enhance insight quality by swapping `InsightEngine` with more advanced NLP models while keeping the citation requirement.
- Integrate authentication or encrypted storage for secure deployments.

## Security & Privacy Notes

- All processing occurs locally without third-party API calls.
- Review the Flask `secret_key` and database storage location before production use.
- Ensure uploads are stored in a secure location with appropriate access controls.

## Deploying to Vercel

The included `vercel.json` configures the Python runtime and routes all requests to the Flask application via Gunicorn. Deploy with:

```bash
vercel --prod
```

Make sure to add `FLASK_SECRET_KEY` (and optionally `EDISCOVERY_BASE_DIR`) as environment variables in the Vercel dashboard. The application stores collected files and the SQLite database under `/tmp`, recreating the database automatically when new serverless instances start.
