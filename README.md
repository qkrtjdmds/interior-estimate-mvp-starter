# Interior Estimate MVP Starter

MVP v0.1 개발 착수용 골격입니다.

## Stack
- Frontend: React + Vite + TypeScript
- Backend: FastAPI
- DB: PostgreSQL

## Run
### 1. PostgreSQL
```bash
docker compose up -d db
```

### 2. Backend
```bash
cd backend
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Sprint 0 Check
1. Backend `/api/health` returns `{ "status": "ok" }`
2. Frontend home opens
3. Frontend health badge shows backend connection success

## Next
Sprint 1: Category / Item / Option / Default Price reference-data CRUD.
