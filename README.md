# Campus Knowledge Agent

FastAPI serves the static HTML/CSS/JavaScript interface and JSON API from one origin. MongoDB Atlas stores documents, chunks, and query analytics; Gemini provides embeddings and grounded point selection.

## Project Structure

- `backend/` — FastAPI routes, authentication, Atlas access, PDF ingestion, and RAG flow
- `frontend/` — static single-page UI; there is no React, Vite, Node package, or frontend build
- `sample_docs/` — committed PDFs indexed by the faculty Seed action
- `uploaded_docs/` — ignored local legacy upload folder; new uploads are parsed in memory and stored as chunks/metadata in Atlas
- `render.yaml` — single Render Python Web Service

## Local Run

Requires Python 3.11 and pip. In PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. Development defaults are configured in `backend/config.py`; they are not accepted in production. Set `MONGODB_URI` and `GEMINI_API_KEY` in `.env` to use Atlas and Gemini.

## API

- `GET /health` — deployment health, returns `{"status":"ok"}` without service details
- `GET /api/health` — application/database status for the UI
- `POST /api/login` — authenticates a student or admin account
- `GET /api/me` — current authenticated account
- `GET /api/documents` — indexed document list
- `POST /api/upload` — admin-only PDF ingestion
- `POST /api/seed` — admin-only indexing of `sample_docs/*.pdf`
- `POST /api/query` — authenticated English/Tamil/Tanglish RAG query
- `GET /api/analytics` — admin-only query analytics and knowledge gaps

All endpoints except health require a bearer token where indicated by the route. The browser sends same-origin API requests; do not add a production localhost URL.

## Render Deployment

This repository uses one **Web Service**, not a Static Site: the frontend is served by FastAPI and shares relative `/api/*` routes. No React Router rewrite or frontend publish directory is needed.

Create a Render Web Service from the GitHub repository with:

- Root directory: repository root
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`

Set these Render environment variables:

```text
APP_ENV=production
PYTHON_VERSION=3.11.9
DATABASE_NAME=campus_knowledge_db
SIMILARITY_THRESHOLD=0.35
MONGODB_URI=<Atlas connection string>
GEMINI_API_KEY=<Gemini key>
APP_SECRET_KEY=<unique random value, at least 32 characters>
STUDENT_USERNAME=<student login name>
STUDENT_PASSWORD=<unique password, at least 12 characters>
ADMIN_USERNAME=<faculty login name>
ADMIN_PASSWORD=<different unique password, at least 12 characters>
FRONTEND_URL=https://YOUR-SERVICE.onrender.com
```

Enter secret values in Render's dashboard, not in this repository or `render.yaml`. Production startup fails if Atlas/Gemini credentials, a strong signing key, or distinct strong passwords are missing. CORS permits the configured `FRONTEND_URL` and the local development origins; same-origin requests on the single service do not require CORS.

Before deploy, remove/rotate any credential that may have been valid in the previous tracked `.env.example`. Keep `.env` local; it is ignored by Git. Atlas must allow connections from Render's outbound IP ranges, or use a restricted network policy appropriate for the Render plan. Use a dedicated Atlas database user with only the required database permissions.

## GitHub And Smoke Tests

Commit source, `requirements.txt`, `render.yaml`, `.env.example`, and intended sample PDFs. Do not commit `.env`, uploaded PDFs, keys, or generated local data. Check with `git status` before pushing.

After deployment, check `https://YOUR-SERVICE.onrender.com/health`, sign in as both roles, verify a student receives `403` from `/api/analytics`, upload a PDF as admin, then ask a question from it and check the citation. Test an unrelated question for the exact “I couldn't find this information in the available campus documents.” fallback.
