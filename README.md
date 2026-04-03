# Personal Intelligence Hub

> A multi-agent AI system that helps you manage tasks, schedules, and information through natural language — built with Google ADK, Gemini, FastAPI, and PostgreSQL, deployed on Google Cloud Run.

**Live Demo:** https://intel-hub-678311736751.us-central1.run.app
**API Docs:** https://intel-hub-678311736751.us-central1.run.app/docs

---

## What it does

Talk to it like a human. The coordinator agent figures out what you want and delegates to the right sub-agent.

```
"Create a high priority task to review ADK docs by Friday"
→ Task created ✓

"What's pending?"
→ Lists all pending tasks with priorities and due dates

"Mark the ADK docs task as done"
→ Status updated ✓
```

---

## Architecture

```
User / UI
    │
    ▼
FastAPI (Cloud Run)
    │
    ▼
Coordinator Agent (Gemini via ADK)
    │  A2A Protocol
    ▼
Task Agent
    │
    ▼
PostgreSQL (Cloud SQL)
```

The coordinator agent receives natural language input, decides which sub-agent to delegate to using the A2A protocol, and returns a human-friendly response. All state — tasks and session history — is persisted in PostgreSQL.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 2.5 Flash |
| Agent framework | Google ADK (Agent Development Kit) |
| Agent communication | A2A Protocol |
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL (Cloud SQL) |
| ORM | SQLAlchemy (async) |
| Deployment | Google Cloud Run |
| Secrets | Google Secret Manager |
| UI | Vanilla HTML/CSS/JS (served from Cloud Run) |

---

## Project structure

```
personal-intel-hub/
├── app/
│   ├── main.py              # FastAPI entry point + CORS + static UI
│   ├── config.py            # Settings via pydantic
│   ├── database.py          # Async PostgreSQL connection
│   ├── models.py            # SQLAlchemy models (Task, AgentSession)
│   ├── agents/
│   │   ├── coordinator.py   # Primary ADK coordinator agent
│   │   └── task_agent.py    # Task sub-agent with CRUD tools
│   └── routers/
│       └── tasks.py         # REST endpoints + /query
├── static/
│   └── index.html           # Chat UI + task dashboard
├── Dockerfile
└── requirements.txt
```

---

## API reference

All endpoints require header: `x-api-key: YOUR_KEY`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/query` | Natural language → coordinator agent |
| GET | `/api/v1/tasks` | List tasks (filter by status/priority) |
| POST | `/api/v1/tasks` | Create task directly |
| GET | `/api/v1/tasks/{id}` | Get single task |
| PATCH | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Delete task |
| GET | `/health` | Health check |

### Example — natural language query

```bash
curl -X POST https://intel-hub-678311736751.us-central1.run.app/api/v1/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-key" \
  -d '{"message": "Create a high priority task to prepare demo by Friday"}'
```

Response:
```json
{
  "response": "I have created a high priority task 'Prepare demo' due Friday. Task ID: abc-123, status: pending.",
  "session_id": "6670dead-156d-46ee-9fed-eb93ecfbdec6"
}
```

Pass `session_id` back in subsequent requests to maintain conversation context.

---

## Local setup

### Prerequisites
- Python 3.12+
- PostgreSQL
- Gemini API key — get one at https://aistudio.google.com/app/apikey

### 1. Clone and install
```bash
git clone https://github.com/Ujjawal0204/personal-intel-hub.git
cd personal-intel-hub
pip install -r requirements.txt
```

### 2. Create database
```bash
psql -U postgres -c "CREATE DATABASE intel_hub;"
```

### 3. Configure environment
Create a `.env` file:
```
DATABASE_URL_LOCAL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/intel_hub
GOOGLE_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
API_KEY=dev-key
ENV=local
```

### 4. Run
```bash
uvicorn app.main:app --reload --port 8080
```

Open http://localhost:8080 for the UI or http://localhost:8080/docs for the API explorer.

---

## Cloud Run deployment

### 1. Create Cloud SQL instance
```bash
gcloud sql instances create intel-hub-db \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --edition=ENTERPRISE \
  --region=us-central1

gcloud sql databases create intel_hub --instance=intel-hub-db
gcloud sql users create intel_hub_user --instance=intel-hub-db --password=YOUR_PASSWORD
```

### 2. Store secrets
```bash
echo -n "postgresql+asyncpg://intel_hub_user:PASSWORD@/intel_hub?host=/cloudsql/PROJECT:us-central1:intel-hub-db" \
  | gcloud secrets create intel-hub-db-url --data-file=-

echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create intel-hub-gemini-key --data-file=-
echo -n "YOUR_API_KEY" | gcloud secrets create intel-hub-api-key --data-file=-
```

### 3. Create service account
```bash
gcloud iam service-accounts create intel-hub-sa
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:intel-hub-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:intel-hub-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Deploy
```bash
gcloud run deploy intel-hub \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT:us-central1:intel-hub-db \
  --set-secrets="DATABASE_URL=intel-hub-db-url:latest,GOOGLE_API_KEY=intel-hub-gemini-key:latest,API_KEY=intel-hub-api-key:latest" \
  --set-env-vars="ENV=cloud,GCP_PROJECT_ID=PROJECT,GCP_REGION=us-central1" \
  --service-account="intel-hub-sa@PROJECT.iam.gserviceaccount.com" \
  --memory=512Mi
```

---

## Built for

H2S GenAI Academy — multi-agent AI system hackathon project demonstrating agent coordination, tool use, A2A protocol, and cloud deployment.
