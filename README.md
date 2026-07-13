# ChatWithData

AI-powered Business Intelligence tool. Upload CSV/Excel files, ask questions in natural language, get charts and insights.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16 + React 19 + Tailwind CSS |
| Charts | Recharts |
| Backend | Python FastAPI |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Database | PostgreSQL 16 |
| AI | Google Gemini API |
| Vector DB | ChromaDB (local) |
| Auth | JWT + bcrypt |

## Quick Start

### Prerequisites

- Node.js 22+
- Python 3.12+
- PostgreSQL 16+

### 1. Database

```sql
CREATE DATABASE chatwithdata;
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# Copy and configure .env
copy .env.example .env
# Edit .env with your GEMINI_API_KEY

# Run migrations
alembic upgrade head

# Seed demo user
python seed.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Demo login: demo@chatwithdata.com / demo1234

## Docker (Alternative)

```bash
docker-compose up --build
```

## Project Structure

```
chatwithdata/
├── frontend/                 # Next.js 16 app
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   └── lib/             # API client, utils
│   └── package.json
│
└── backend/                  # FastAPI app
    ├── app/
    │   ├── models/          # SQLAlchemy ORM models
    │   ├── routers/         # API endpoints
    │   ├── services/        # AI, NL2SQL, parser
    │   └── storage/         # Local file storage
    ├── alembic/             # DB migrations
    ├── requirements.txt
    └── .env.example
```

## Features

- Upload CSV/Excel files
- Natural language to SQL (NL2SQL)
- Auto chart recommendation
- Chat history with conversations
- Data tables with pagination
- SQL query preview
- JWT authentication
- Local file storage
