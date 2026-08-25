# SkuPhase: Quick Reference Guide

## API Endpoints Cheat Sheet

```
AUTHENTICATION
──────────────────────────────────────────────
POST   /api/v1/auth/register           Register school + admin
POST   /api/v1/auth/login               Email/password login
POST   /api/v1/auth/google-oauth        Google OAuth callback
POST   /api/v1/auth/refresh-token       Refresh access token
POST   /api/v1/auth/logout              Logout user

SCHOOL MANAGEMENT
──────────────────────────────────────────────
GET    /api/v1/schools/{id}             Get school details
PUT    /api/v1/schools/{id}             Update school
GET    /api/v1/schools/{id}/settings    Get school settings
PUT    /api/v1/schools/{id}/settings    Update settings (branding, LLM provider)

USER MANAGEMENT
──────────────────────────────────────────────
GET    /api/v1/users/                   List school users
POST   /api/v1/users/invite             Invite staff member
PUT    /api/v1/users/{id}/role          Change user role
DELETE /api/v1/users/{id}               Remove user from school

DOCUMENT MANAGEMENT (RAG)
──────────────────────────────────────────────
POST   /api/v1/documents/upload         Upload curriculum material
GET    /api/v1/documents/               List school documents
GET    /api/v1/documents/{id}           Get document details
DELETE /api/v1/documents/{id}           Delete document
GET    /api/v1/documents/search?q=...   Search documents

EXAM GENERATION & MANAGEMENT
──────────────────────────────────────────────
POST   /api/v1/exams/generate           ⭐ Generate exam (SINGLE CALL)
GET    /api/v1/exams/                   List exams
GET    /api/v1/exams/{id}               Get exam + questions
PUT    /api/v1/exams/{id}               Update exam metadata
DELETE /api/v1/exams/{id}               Delete exam
POST   /api/v1/exams/{id}/refine        Refine specific questions
POST   /api/v1/exams/{id}/approve       Approve exam
POST   /api/v1/exams/{id}/export        Export to PDF/Word

ANALYTICS & BILLING
──────────────────────────────────────────────
GET    /api/v1/analytics/usage          School usage statistics
GET    /api/v1/analytics/exams-quality  Exam quality metrics
GET    /api/v1/billing/plans            Available subscription plans
GET    /api/v1/billing/subscription     Current subscription
POST   /api/v1/billing/upgrade          Change subscription plan
GET    /api/v1/billing/invoices         Billing history
```

---

## Database Entity Relationships

```
School (Tenant)
    │
    ├─→ SchoolSubscription → Plan
    │
    ├─→ SchoolSettings
    │
    ├─→ User (has school_id)
    │   ├─→ Exam (created_by)
    │   └─→ UsageLog
    │
    └─→ SchoolDocument (curriculum material)
        │
        ├─→ DocumentChunk (with embedding vector)
        │
        └─→ ExamContext
            └─→ Exam (citation tracking)
                │
                └─→ Question (MCQ/short/essay)
```

---

## Authentication Flow

```
USER SIGNUP
┌─────────────────────────────────────────┐
│ POST /auth/register                     │
│ {                                       │
│   "school_name": "Lagos School",        │
│   "contact_email": "admin@school.ng",   │
│   "admin_user": {                       │
│     "full_name": "Admin Name",          │
│     "email": "admin@school.ng",         │
│     "password": "SecurePass123!"        │
│   },                                    │
│   "plan_id": "uuid"                     │
│ }                                       │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ RESPONSE (201 Created)                  │
│ {                                       │
│   "school_id": "uuid",                  │
│   "admin_user": {...},                  │
│   "subscription": {...}                 │
│ }                                       │
└──────────┬──────────────────────────────┘
           │
           ▼
      Use credentials to LOGIN

SUBSEQUENT LOGINS
┌─────────────────────────────────────────┐
│ POST /auth/login                        │
│ {                                       │
│   "email": "admin@school.ng",           │
│   "password": "SecurePass123!"          │
│ }                                       │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ RESPONSE (200 OK)                       │
│ {                                       │
│   "access_token": "jwt_token",          │
│   "refresh_token": "jwt_token",         │
│   "token_type": "bearer",               │
│   "expires_in": 3600                    │
│ }                                       │
└──────────┬──────────────────────────────┘
           │
           ▼
   Use in Authorization header:
   Authorization: Bearer <access_token>
```

---

## Exam Generation Flow (THE CORE)

```
SINGLE INTELLIGENT CALL APPROACH
═══════════════════════════════════════════

Step 1: PREPARE CONTEXT
┌──────────────────────────────────────────┐
│ Teacher selects curriculum documents     │
│ system retrieves relevant chunks via RAG │
│ (semantic search in pgvector)            │
└──────────┬───────────────────────────────┘
           │
           ▼
Step 2: BUILD COMPLETE PROMPT
┌──────────────────────────────────────────┐
│ Section 1: Curriculum alignment          │
│ Section 2: Lesson content                │
│ Section 3: Nigerian education context    │
│ Section 4: <internal_planning>           │
│   - Analyze                              │
│   - Plan distribution                    │
│   - Map to Bloom's taxonomy              │
│   - Calibrate difficulty                 │
│   (DO NOT OUTPUT)                        │
│ Section 5: Question specifications       │
│ Section 6: Quality standards             │
│ Section 7: Output format (strict JSON)   │
└──────────┬───────────────────────────────┘
           │
           ▼
Step 3: SINGLE LLM CALL
┌──────────────────────────────────────────┐
│ LLM (Grok or OpenRouter)                 │
│                                          │
│ Internally:                              │
│ 1. Reads <internal_planning> section     │
│ 2. Plans: distribution, difficulty, etc  │
│ 3. Generates 50 coordinated questions    │
│ 4. Applies quality checks                │
│ 5. Formats as JSON                       │
│                                          │
│ Returns: Valid JSON with 50 questions    │
└──────────┬───────────────────────────────┘
           │
           ▼
Step 4: PARSE & VALIDATE
┌──────────────────────────────────────────┐
│ Parse JSON response                      │
│ Validate:                                │
│   - 50 questions                         │
│   - 100 total marks                      │
│   - All required fields                  │
│   - Correct JSON structure               │
└──────────┬───────────────────────────────┘
           │
           ▼
Step 5: STORE & TRACK
┌──────────────────────────────────────────┐
│ Store exam and questions in database     │
│ Track source documents (citations)       │
│ Log usage for billing/analytics          │
│ Return exam to teacher as draft          │
└──────────┬───────────────────────────────┘
           │
           ▼
RESULT: Professional exam with 50 questions
        all coordinated, curriculum-aligned,
        Nigerian context, <60 seconds
```

---

## RAG Semantic Search Flow

```
DOCUMENT PROCESSING PIPELINE
┌─────────────────────────────────────────┐
│ 1. UPLOAD                               │
│    Teacher uploads PDF/DOCX/image       │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ 2. EXTRACT TEXT                         │
│    PDF → PyPDF2/pdfplumber              │
│    DOCX → python-docx                   │
│    Image → Tesseract OCR                │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ 3. CHUNK TEXT                           │
│    Break into 100-500 token chunks      │
│    Maintain overlap for context         │
│    Store chunk metadata                 │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ 4. GENERATE EMBEDDINGS                  │
│    For each chunk:                      │
│    - Call OpenAI embedding API          │
│    - Get 1536-dim vector                │
│    - Store in pgvector column           │
└──────────┬──────────────────────────────┘
           │
           ▼
        STORED IN DATABASE

RETRIEVAL (During Exam Generation)
┌─────────────────────────────────────────┐
│ Teacher: "Generate Biology exam"        │
│ System: "Which curriculum to use?"      │
│ Teacher selects documents               │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ SEMANTIC SEARCH                         │
│ Query: "Photosynthesis factors"         │
│ 1. Embed query → 1536-dim vector        │
│ 2. Cosine similarity in pgvector        │
│ 3. Return top 10 chunks with scores     │
│ 4. Filter by relevance threshold (0.7)  │
└──────────┬──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ INJECT INTO PROMPT                      │
│ "Here's relevant curriculum content:"   │
│ [Chunks 1-5 embedded in prompt]         │
│ "Generate questions based on this..."   │
└──────────┬──────────────────────────────┘
           │
           ▼
      LLM generates exam with context
```

---

## Rate Limiting (School Quotas)

```
QUOTA CHECK BEFORE ACTION
┌────────────────────────────────────────┐
│ School wants to generate exam          │
│ System checks: plan = "Professional"   │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Professional Plan Limits (per month):  │
│ - max_exams: 200                       │
│ - max_refinements: 500                 │
│ - max_exports: 500                     │
│ - max_documents: 50                    │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Query this month's usage:              │
│ SELECT COUNT(*) FROM usage_logs        │
│ WHERE school_id = ?                    │
│ AND action = 'exam_generation'         │
│ AND DATE_TRUNC('month', now()) =       │
│     DATE_TRUNC('month', created_at)    │
│ RESULT: 145 exams so far               │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ CHECK: 145 < 200? YES ✓                │
│ Proceed with exam generation           │
│ Log usage: +1 exam                     │
└────────────────────────────────────────┘
```

---

## Question Type Examples

```
MULTIPLE CHOICE (2 marks)
┌────────────────────────────────────────┐
│ Q1. Which organelle produces energy?   │
│                                        │
│ A. Nucleus                             │
│ B. Mitochondria ✓                      │
│ C. Ribosome                            │
│ D. Lysosome                            │
│                                        │
│ Explanation: Mitochondria is the       │
│ powerhouse of the cell...              │
└────────────────────────────────────────┘

SHORT ANSWER (3 marks)
┌────────────────────────────────────────┐
│ Q2. Explain photosynthesis.            │
│                                        │
│ Marking Scheme:                        │
│ - Definition (1 mark)                  │
│ - Process explanation (1 mark)         │
│ - Raw materials/products (1 mark)      │
└────────────────────────────────────────┘

ESSAY (10 marks)
┌────────────────────────────────────────┐
│ Q3. A farmer in Oyo state...           │
│                                        │
│ (a) Identify 3 limiting factors (3m)   │
│ (b) Explain each factor (6m)           │
│ (c) Suggest improvements (1m)          │
│                                        │
│ Total: 10 marks                        │
└────────────────────────────────────────┘

EXAM TOTALS (50 questions)
├─ 10 MCQ × 2 marks = 20 marks
├─ 20 Short answer × 3 marks = 60 marks
└─ 10 Essay × 2 marks = 20 marks
   ───────────────────────────
   TOTAL = 100 marks
```

---

## Cost Calculation

```
SINGLE EXAM GENERATION

Input Tokens:
  Prompt template:         500 tokens
  Curriculum context:      800 tokens
  Lesson notes:            700 tokens
  RAG retrieved chunks:    500 tokens
  Formatting/specs:        500 tokens
  ────────────────────────────────
  TOTAL INPUT:           3,000 tokens

Output Tokens:
  50 questions × 60 tokens = 3,000 tokens

Total: 6,000 tokens

Cost (Grok API - ~$0.0005 per 1K tokens):
  6,000 × $0.0005 / 1000 = $0.003
  
  In Naira (1 USD = ₦1,500):
  $0.003 × 1,500 = ₦4.50

Total cost per exam: ~₦40-50
School plan: ₦5,000/month (50 exams)
  = ₦100 per exam (includes support, storage, etc)

Gross margin: ~60-70%
```

---

## Debugging Checklist

```
❌ Exam generation returned null
├─ Check: Document uploaded successfully?
├─ Check: Document chunks created in database?
├─ Check: RAG retrieval returned results?
├─ Check: LLM API key valid?
├─ Check: Grok failing? Check OpenRouter fallback

❌ LLM returned invalid JSON
├─ Check: Prompt includes "Return ONLY valid JSON"?
├─ Check: Parser handles escaped quotes?
├─ Check: All 50 questions present?
├─ Check: Total marks = 100?

❌ School can't access exam
├─ Check: JWT token includes correct school_id?
├─ Check: Database query filters by school_id?
├─ Check: RLS policies enabled?

❌ Quota exceeded error
├─ Check: School has active subscription?
├─ Check: Plan has higher limits? (upgrade needed)
├─ Check: Current usage count correct?

❌ Document extraction failed
├─ Check: File format supported?
├─ Check: File not corrupted?
├─ Check: OCR service accessible?
├─ Check: Text extraction timeout?

❌ Slow exam generation
├─ Check: RAG search returning too many chunks?
├─ Check: OpenAI embedding API slow?
├─ Check: LLM provider overloaded?
├─ Check: Database connection pooling OK?
```

---

## Environment Variables Needed

```
APP
  APP_NAME=SkuPhase
  APP_ENV=development|staging|production
  DEBUG=true|false

DATABASE
  DATABASE_URL=postgresql://user:pass@host:5432/db

SUPABASE
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_ANON_KEY=xxx
  SUPABASE_SERVICE_KEY=xxx

AUTHENTICATION
  JWT_SECRET_KEY=min-32-chars-long-secret-key
  GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=xxx

LLM PROVIDERS
  GROK_API_KEY=xxxxxxxxxxx
  OPENROUTER_API_KEY=xxxxxxxxxxx
  OPENAI_EMBEDDING_API_KEY=sk-xxxxx

CORS
  CORS_ORIGINS=http://localhost:3000,https://exam.com

STRIPE (Phase 5)
  STRIPE_API_KEY=sk_live_xxx
  STRIPE_WEBHOOK_KEY=whsec_xxx
```

---

## File Structure Reference

```
SkuPhase/
├── docs/
│   ├── PRD.md (Product requirements)
│   ├── TDD.md (Technical design)
│   ├── IMPLEMENTATION_PLAN.md (Roadmap)
│   ├── api_specification.md (All endpoints)
│   ├── RAG_IMPLEMENTATION.md (Vector DB)
│   ├── exam_generation_prompt.txt (🔑 Key prompt)
│   ├── refinement_prompt.txt
│   └── ... (other specs)
│
├── docs/ (NEW - I created)
│   ├── PROJECT_ANALYSIS_SUMMARY.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   ├── ARCHITECTURE_COMPARISON.md
│   ├── DEVELOPMENT_GUIDELINES.md
│   ├── EXECUTIVE_SUMMARY.md
│   └── QUICK_REFERENCE.md (this file)
│
├── app/
│   ├── main.py (FastAPI app)
│   ├── api/v1/ (Routes)
│   ├── models/ (Database entities)
│   ├── schemas/ (Pydantic models)
│   ├── services/ (Business logic)
│   ├── core/ (Auth, DB, LLM)
│   ├── utils/ (Prompts, helpers)
│   └── config/ (Settings)
│
├── migrations/ (Alembic)
├── tests/ (Unit + integration)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Key Files to Study First

1. **EXECUTIVE_SUMMARY.md** - Start here (5 min read)
2. **ARCHITECTURE_COMPARISON.md** - Understand the innovation (10 min)
3. **IMPLEMENTATION_ROADMAP.md** - Detailed steps (30 min)
4. **exam_generation_prompt.txt** - The core prompt (20 min)
5. **DEVELOPMENT_GUIDELINES.md** - Coding patterns (30 min)
6. **api_specification.md** - Endpoint details (reference)
7. **RAG_IMPLEMENTATION.md** - Vector database (reference)

**Total onboarding time: ~2 hours**

---

## Remember

✅ Single LLM call per exam
✅ Check school_id on every query
✅ Use semantic search for context
✅ Parse JSON strictly
✅ Log everything important
✅ Test thoroughly
✅ Check quotas before actions
✅ Include <internal_planning> in prompts
✅ Use Nigerian education context
✅ Handle failures gracefully

You've got this! 🚀

