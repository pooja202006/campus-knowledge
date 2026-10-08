# Campus Knowledge AI

A lightweight campus knowledge assistant that ingests institutional PDF documents, indexes them for retrieval, and answers student questions with source-backed citations.

## Features

- Multi-file PDF upload and ingestion
- Query processing with semantic retrieval and citation output
- Local fallback database mode when cloud services are unavailable
- Student chat UI with language support for English, Tamil, and Tanglish
- Admin analytics dashboard for query tracking

## Project structure

- `backend/` — FastAPI application, database logic, ingestion, and multi-agent query pipeline
- `frontend/` — static HTML, CSS, and JavaScript UI
- `sample_docs/` — sample campus PDFs used for local testing
- `.env.example` — environment variable template
- `requirements.txt` — Python dependencies

## Requirements

- Python 3.10+
- pip
- Optional: MongoDB Atlas connection string
- Optional: Gemini API key

## Setup

1. Open a terminal in the project root.
2. Create a virtual environment (optional but recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy the example environment file and set your real credentials if available:

```bash
copy .env.example .env
```

Then edit `.env` with values like:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_NAME=campus_knowledge_db
PORT=8000
SIMILARITY_THRESHOLD=0.35
```

If you do not provide MongoDB or Gemini credentials, the app will still run in local fallback mode and can still ingest sample documents for demo use.

## Run the app

From the project root:

```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Then open:

```text
http://localhost:8000
```

## Seed sample campus documents

You can use the built-in upload UI or call the API:

```bash
curl -X POST http://localhost:8000/api/seed
```

This processes the sample PDFs from the `sample_docs/` folder.

## Example query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"When do the end semester theory exams start?","language":"English"}'
```

## Notes

- The project is designed to work both with cloud services and without them.
- If cloud credentials are missing, queries still work against local memory storage and fallback synthesis for demonstrations.
- For production use, provide both a valid MongoDB URI and Gemini API key.
