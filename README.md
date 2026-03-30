# Personal Intelligence Hub

Multi-agent AI system built with FastAPI + Google ADK + Gemini, deployed on Cloud Run.

## Architecture

```
POST /api/v1/query  →  Coordinator Agent (Gemini)  →  Task Agent  →  PostgreSQL
GET/POST /api/v1/tasks  →  Direct CRUD  →  PostgreSQL
```

## Local setup

### 1. PostgreSQL
```bash
# Using Docker for local Postgres
docker run -d \
  --name intel-hub-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=intel_hub \
  -p 5432:5432 \
  postgres:16
```

### 2. Environment
```bash
cp .env .env.local
# Edit .env with your values
# For local: DATABASE_URL_LOCAL is used automatically
```

### 3. Install & run
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### 4. Test
```bash
# Health check
curl http://localhost:8080/health

# Natural language query
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-key" \
  -d '{"message": "Create a high priority task to review ADK docs by Friday"}'

# List tasks
curl http://localhost:8080/api/v1/tasks \
  -H "x-api-key: dev-key"
```

## Cloud Run deploy

### Prerequisites
```bash
# 1. Create Cloud SQL PostgreSQL instance
gcloud sql instances create intel-hub-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1

# 2. Create database and user
gcloud sql databases create intel_hub --instance=intel-hub-db
gcloud sql users create intel_hub_user --instance=intel-hub-db --password=YOUR_PASSWORD

# 3. Store secrets
echo -n "postgresql+asyncpg://intel_hub_user:YOUR_PASSWORD@/intel_hub?host=/cloudsql/PROJECT:REGION:intel-hub-db" \
  | gcloud secrets create intel-hub-db-url --data-file=-

echo -n "your-secret-api-key" \
  | gcloud secrets create intel-hub-api-key --data-file=-

# 4. Create service account
gcloud iam service-accounts create intel-hub-sa
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:intel-hub-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:intel-hub-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
gcloud secrets add-iam-policy-binding intel-hub-db-url \
  --member="serviceAccount:intel-hub-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding intel-hub-api-key \
  --member="serviceAccount:intel-hub-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Deploy
```bash
# Edit PROJECT_ID and CLOUD_SQL_INSTANCE in deploy.sh first
chmod +x deploy.sh
./deploy.sh
```

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/query` | Natural language → agent |
| GET | `/api/v1/tasks` | List all tasks |
| POST | `/api/v1/tasks` | Create task directly |
| GET | `/api/v1/tasks/{id}` | Get single task |
| PATCH | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Delete task |
| GET | `/health` | Health check |

All endpoints (except `/health`) require header: `x-api-key: YOUR_KEY`

## Interactive docs
http://localhost:8080/docs
