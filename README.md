# ⚡ Personal Intelligence Hub

> **Multi-Agent AI System for Task & Schedule Management**
> Built with Google ADK, A2A Protocol, Gemini, and deployed on Google Cloud Platform

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Cloud_Run-4285F4?style=for-the-badge)](https://intel-hub-678311736751.us-central1.run.app)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Google ADK](https://img.shields.io/badge/Google_ADK-Agent_Dev_Kit-EA4335?style=for-the-badge&logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## 📌 Overview

The **Personal Intelligence Hub** is a multi-agent AI system that demonstrates real-world implementation of Google's Agent Development Kit (ADK) and Agent-to-Agent (A2A) protocol. A central **Coordinator Agent** intelligently routes user requests to specialized sub-agents — a **Task Agent** for to-do management and a **Schedule Agent** for calendar events — all powered by Gemini and backed by PostgreSQL.

### Key Highlights

- **Multi-Agent Architecture** — Coordinator Agent routes queries to specialized sub-agents via A2A protocol
- **Natural Language Interface** — Chat naturally to manage tasks and schedule events
- **Smart Date Parsing** — Say "tomorrow at 3pm" instead of rigid date formats
- **Conflict Detection** — Automatic scheduling conflict detection when creating events
- **Real-time Dashboard** — Tabbed UI showing tasks and schedule side-by-side
- **Production Deployed** — Live on Google Cloud Run with Cloud SQL PostgreSQL

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│              Chat + Quick Actions + Dashboard                   │
│           ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│           │ 📋 Tasks │ │ 📅 Events│ │ 💬 Chat  │               │
│           └──────────┘ └──────────┘ └──────────┘               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / REST
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│                  (Cloud Run: intel-hub)                          │
│                                                                 │
│   /api/v1/query ──► POST natural language                       │
│   /api/v1/tasks ──► GET/POST/PATCH/DELETE                       │
│   /api/v1/schedules ──► GET/POST/PATCH/DELETE                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              🧠 COORDINATOR AGENT (Gemini)                      │
│                                                                 │
│   "What does the user want?"                                    │
│                                                                 │
│   ┌─ task, todo, priority ──► delegate_to_task_agent()          │
│   │                                                             │
│   └─ schedule, meeting,   ──► delegate_to_schedule_agent()      │
│      calendar, event                                            │
└───────────┬─────────────────────────────┬───────────────────────┘
            │ A2A Protocol                │ A2A Protocol
            ▼                             ▼
┌───────────────────────┐   ┌────────────────────────────┐
│  📋 TASK AGENT        │   │  📅 SCHEDULE AGENT         │
│  (Gemini + ADK)       │   │  (Gemini + ADK)            │
│                       │   │                            │
│  FunctionTools:       │   │  FunctionTools:            │
│  • create_task        │   │  • create_schedule         │
│  • list_tasks         │   │  • list_schedules          │
│  • update_task        │   │  • update_schedule         │
│  • delete_task        │   │  • delete_schedule         │
│                       │   │  • get_daily_summary       │
│                       │   │  • conflict detection      │
└───────────┬───────────┘   └──────────────┬─────────────┘
            │                              │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   🗄️ PostgreSQL Database                        │
│              (Cloud SQL: intel-hub-db)                           │
│                                                                 │
│   ┌──────────┐  ┌──────────────┐  ┌────────────────┐           │
│   │  tasks   │  │  schedules   │  │ agent_sessions │           │
│   │          │  │              │  │                │           │
│   │ id       │  │ id           │  │ id             │           │
│   │ title    │  │ title        │  │ history (JSON) │           │
│   │ status   │  │ event_date   │  └────────────────┘           │
│   │ priority │  │ start_time   │                               │
│   │ due_date │  │ end_time     │                               │
│   └──────────┘  │ status       │                               │
│                 └──────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Communication Flow

```
User: "Schedule a team meeting tomorrow 10:00 to 11:00"
  │
  ▼
Coordinator Agent (Gemini)
  │ Detects: "schedule", "meeting" → Schedule Agent
  │ Converts: "tomorrow" → 2026-04-07
  │
  ▼ A2A Protocol
Schedule Agent (Gemini + FunctionTools)
  │ Calls: create_schedule(title="Team meeting", date="2026-04-07", ...)
  │ Checks: Conflict detection against existing events
  │ Returns: "Event 'Team meeting' created for 2026-04-07 (10:00-11:00)"
  │
  ▼
Coordinator relays response → User sees result + Dashboard updates
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Framework** | Google ADK (Agent Development Kit) |
| **Agent Protocol** | A2A (Agent-to-Agent) |
| **LLM** | Google Gemini 2.5 Flash |
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL (async via SQLAlchemy + asyncpg) |
| **Frontend** | Vanilla HTML/CSS/JS (Single-page app) |
| **Cloud** | Google Cloud Run, Cloud SQL, Secret Manager |
| **Container** | Docker |

---

## 📁 Project Structure

```
intel-hub/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point, routers, startup
│   ├── config.py               # Pydantic settings (env vars)
│   ├── database.py             # Async SQLAlchemy engine + session
│   ├── models.py               # Task, Schedule, AgentSession models
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── coordinator.py      # 🧠 Routes queries to sub-agents via A2A
│   │   ├── task_agent.py       # 📋 4 FunctionTools for task CRUD
│   │   └── schedule_agent.py   # 📅 5 FunctionTools + conflict detection
│   └── routers/
│       ├── __init__.py
│       ├── tasks.py            # REST endpoints + /query (NL interface)
│       └── schedules.py        # REST endpoints for schedule CRUD
├── static/
│   └── index.html              # Chat UI + tabbed dashboard
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── .gcloudignore
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL (local or Cloud SQL)
- Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Local Setup

**1. Clone the repository**

```bash
git clone https://github.com/Ujjawal0204/personal-intel-hub.git
cd personal-intel-hub
```

**2. Create virtual environment**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set up PostgreSQL**

```sql
CREATE DATABASE intel_hub;
```

**5. Configure environment**

```bash
cp .env.example .env
# Edit .env with your database URL and Gemini API key
```

**6. Run the server**

```bash
uvicorn app.main:app --reload --port 8080
```

**7. Open the app**

Navigate to `http://localhost:8080`

---

## ☁️ Cloud Deployment

### Deploy to Google Cloud Run

```bash
# Build container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/intel-hub

# Deploy
gcloud run deploy intel-hub \
  --image gcr.io/YOUR_PROJECT_ID/intel-hub \
  --region us-central1 \
  --add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:intel-hub-db \
  --set-env-vars="ENV=cloud,GEMINI_MODEL=gemini-2.5-flash,GOOGLE_API_KEY=your-key,DATABASE_URL=your-db-url,API_KEY=your-api-key"
```

> **Note**: Always use Dockerfile-based deploy (`gcloud builds submit`), not `gcloud run deploy --source` (Buildpacks crash with TypeError for this project).

---

## 💬 Usage Examples

| You say... | Agent | What happens |
|-----------|-------|-------------|
| "Add a task to review the report" | Task Agent | Creates task with medium priority |
| "Show all my tasks" | Task Agent | Lists all tasks with status & priority |
| "Schedule a meeting tomorrow 10-11am" | Schedule Agent | Creates event, checks for conflicts |
| "What's my agenda for today?" | Schedule Agent | Returns daily summary with total hours |
| "Mark the report task as done" | Task Agent | Updates task status to done |
| "Cancel my 3pm meeting" | Schedule Agent | Sets event status to cancelled |

---

## 🔌 API Endpoints

All endpoints (except `/health`) require `x-api-key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/query` | Natural language → Agent (returns response + session_id) |
| `GET` | `/api/v1/tasks` | List all tasks (filter by status/priority) |
| `POST` | `/api/v1/tasks` | Create a task |
| `PATCH` | `/api/v1/tasks/{id}` | Update a task |
| `DELETE` | `/api/v1/tasks/{id}` | Delete a task |
| `GET` | `/api/v1/schedules` | List all events (filter by date/status) |
| `POST` | `/api/v1/schedules` | Create an event |
| `PATCH` | `/api/v1/schedules/{id}` | Update an event |
| `DELETE` | `/api/v1/schedules/{id}` | Delete an event |
| `GET` | `/health` | Health check (no auth required) |

---

## 🧪 Key Technical Decisions

1. **AsyncSessionLocal per tool call** — Each agent tool opens its own DB session, avoiding session-sharing issues across the A2A boundary.

2. **Coordinator handles date parsing** — The coordinator instruction includes today's date and converts relative dates ("tomorrow", "next Monday") before delegating to sub-agents.

3. **Retry with backoff** — Rate-limited Gemini calls retry automatically with configurable delays.

4. **JSONResponse for all errors** — Every error path returns structured JSON with `error_type` field, preventing frontend JSON parse failures.

5. **Unpinned requirements.txt** — Avoids google-adk version conflicts that occur with pinned dependencies.

---

## 📝 Lessons Learned

- **Never use Buildpacks** for this project — always use Dockerfile-based deploy
- **Gemini model naming matters** — exact strings required, minor variations cause 404s
- **URL-encode DB passwords** — special characters like `/` must be `%2F` in connection strings
- **Null guards are critical** — `event.content.parts` can be null in ADK runner events
- **Separate API keys per environment** — local and cloud should use different Gemini keys to avoid shared quota issues

---

## 🏆 Built For

**H2S GenAI Academy APAC Edition Hackathon**

Demonstrating real-world implementation of:
- Google Agent Development Kit (ADK)
- Agent-to-Agent (A2A) Protocol
- Google Gemini LLM
- Google Cloud Platform deployment

---

## 👤 Author

**Ujjawal Jaiswal** — [@Ujjawal0204](https://github.com/Ujjawal0204)

---

## 📄 License

This project is built for educational and hackathon demonstration purposes.