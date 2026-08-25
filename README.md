# SkuPhase - Quick Start Guide

## Phase 1: Foundation & Infrastructure

**Status:** 🚀 In Development  
**Current Stage:** Week 1 - Database & Authentication (COMPLETED)

### What's been implemented:

✅ **FastAPI Application Setup**
- Main app with CORS and middleware
- Health check and root endpoints
- OpenAPI documentation enabled

✅ **Configuration System**
- Environment-based settings
- All required env variables defined
- .env.example template

✅ **Database Layer**
- SQLAlchemy async ORM setup
- PostgreSQL connection pooling
- Database initialization and cleanup

✅ **Authentication System**
- JWT token generation and validation
- Password hashing with bcrypt
- Password strength validation
- Token refresh functionality

✅ **Database Models**
- School (tenant)
- User (with school association)
- Plan and Subscription
- Exam and Question
- SchoolDocument and DocumentChunk (RAG)
- UsageLog (billing/rate limiting)

✅ **API Endpoints**
- POST `/api/v1/auth/register` - School registration with admin
- POST `/api/v1/auth/login` - User login
- POST `/api/v1/auth/refresh-token` - Token refresh
- GET `/api/v1/auth/me` - Get current user
- POST `/api/v1/auth/logout` - Logout

✅ **Security**
- HTTPBearer authentication
- Current user dependency injection
- School-based data isolation ready

---

## Local Development Setup

### 1. Create Virtual Environment

```bash
cd c:\Users\Meshell\Desktop\Backends\SkuPhase
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables

```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your values:
# - DATABASE_URL (PostgreSQL connection)
# - SUPABASE credentials
# - JWT_SECRET_KEY (generate: openssl rand -hex 16)
# - Google OAuth credentials
# - LLM API keys
```

### 4. Initialize Database

```bash
# Migration-first setup (recommended and required)
alembic -c alembic.ini upgrade head

# Optional seed helper (applies migrations + seeds default plans)
python init_db.py
```

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API Documentation:** http://localhost:8000/docs

---

## Testing Phase 1 Endpoints

### 1. Register a School

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "school_name": "Test School Lagos",
    "contact_email": "admin@testschool.edu.ng",
    "contact_phone": "+2348012345678",
    "address": "123 Education Road, Lagos",
    "plan_id": "uuid-of-starter-plan",
    "admin_user": {
      "full_name": "Adebayo Folake",
      "email": "admin@testschool.edu.ng",
      "password": "TestPass123!"
    }
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@testschool.edu.ng",
    "password": "TestPass123!"
  }'
```

### 3. Get Current User

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### 4. Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh-token \
  -H "Authorization: Bearer <refresh_token>"
```

---

## Next Steps (Week 2)

- [ ] Create Alembic migrations
- [ ] Add User management endpoints (invite, list, update roles)
- [ ] Add School settings endpoints
- [ ] Implement Google OAuth callback
- [ ] Add tests for auth endpoints

---

## Project Structure

```
SkuPhase/
├── app/
│   ├── __init__.py
│   ├── main.py                 ✅ FastAPI app
│   │
│   ├── api/
│   │   └── v1/
│   │       └── auth_router.py  ✅ Auth endpoints
│   │
│   ├── core/
│   │   ├── database.py         ✅ DB connection
│   │   ├── security.py         ✅ JWT, password
│   │   └── dependencies.py     ✅ Dependency injection
│   │
│   ├── models/                 ✅ All database models
│   ├── schemas/                ✅ Request/response schemas
│   ├── services/               ✅ Business logic
│   ├── config/                 ✅ Settings
│   └── utils/                  (For prompts, helpers)
│
├── migrations/                 (TODO: Alembic setup)
├── tests/                      (TODO: Test suite)
├── requirements.txt            ✅ Dependencies
├── .env.example                ✅ Environment template
└── README.md                   (This file)
```

---

## Database Schema

**Core Tables Created:**

```
Schools (tenant)
  ├─ Users (with school_id FK)
  ├─ SchoolSubscriptions → Plans
  ├─ SchoolSettings
  ├─ SchoolDocuments (RAG source)
  │   └─ DocumentChunks (with embeddings)
  ├─ Exams
  │   ├─ Questions
  │   └─ ExamContext → SchoolDocuments
  └─ UsageLogs
```

---

## Key Implementation Details

### School-First Tenancy
Every user has a `school_id`. All queries must filter by school_id to ensure data isolation.

```python
# ✅ CORRECT
query = select(User).filter(
    User.id == user_id,
    User.school_id == current_user.school_id
)

# ❌ WRONG
query = select(User).filter(User.id == user_id)
```

### JWT Token Structure
```json
{
  "user_id": "uuid",
  "school_id": "uuid",
  "email": "user@school.ng",
  "role": "school_admin|teacher",
  "token_type": "access|refresh",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

---

## Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
- `JWT_SECRET_KEY` - Min 32 characters
- `GROK_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_EMBEDDING_API_KEY`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

**Optional:**
- `APP_ENV` - development|staging|production (default: development)
- `DEBUG` - true|false (default: false)
- `LOG_LEVEL` - DEBUG|INFO|WARNING|ERROR (default: INFO)
- `CORS_ORIGINS` - Comma-separated list

---

## Troubleshooting

### Database Connection Error
```
psycopg2.OperationalError: could not connect to server
```
✅ Check DATABASE_URL in .env  
✅ Ensure PostgreSQL is running  
✅ Verify credentials

### JWT Secret Key Error
```
ValueError: JWT_SECRET_KEY must be at least 32 characters
```
✅ Generate: `openssl rand -hex 16` (gives 32 chars)

### Port Already in Use
```
OSError: [Errno 98] Address already in use
```
✅ Change PORT in .env or command line:
```bash
uvicorn app.main:app --port 8001
```

### Import Errors
```
ModuleNotFoundError: No module named 'app'
```
✅ Ensure you're in the SkuPhase directory  
✅ Virtual environment is activated  
✅ Run: `pip install -e .`

---

## Quick Reference

### API Endpoints Summary
```
POST   /api/v1/auth/register        Register school + admin
POST   /api/v1/auth/login           User login
POST   /api/v1/auth/refresh-token   Refresh JWT token
GET    /api/v1/auth/me              Get current user
POST   /api/v1/auth/logout          Logout user

GET    /health                      Health check
GET    /                            Root info
GET    /docs                        OpenAPI docs
GET    /redoc                       ReDoc docs
```

### Database Models
- `School` - Tenant entity
- `User` - Staff members (teacher, admin)
- `Plan` - Subscription tiers
- `SchoolSubscription` - School → Plan link
- `SchoolSettings` - Branding, LLM provider prefs
- `SchoolDocument` - Uploaded curriculum (RAG)
- `DocumentChunk` - Text chunks with embeddings
- `Exam` - Generated exams
- `Question` - Individual questions
- `ExamContext` - Exam → Document citations
- `UsageLog` - Billing/rate limiting

---

## Next Milestone: Phase 2 (Week 3-4)

Document Management & RAG Foundation:
- [ ] Document upload endpoints
- [ ] Text extraction (PDF, DOCX, OCR)
- [ ] Embedding generation (OpenAI)
- [ ] Vector storage in pgvector
- [ ] Semantic search implementation

---

## Support

For issues or questions:
1. Check QUICK_REFERENCE.md
2. Review DEVELOPMENT_GUIDELINES.md
3. Check IMPLEMENTATION_ROADMAP.md

---

**Happy coding!** 🚀
