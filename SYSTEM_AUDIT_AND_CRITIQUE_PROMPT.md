# SkuPhase: Deep Architectural, UX, Pedagogical & Engineering Audit Prompt

> **Instructions for the Auditing AI Agent**:  
> You have been granted full architectural and auditing authority over the **SkuPhase** codebase (`FastHTML + Faststrap + FastAPI + SQLAlchemy + PostgreSQL/Supabase`). Your objective is **not** to flatter, sugarcoat, or offer superficial compliments. Your mandate is to conduct an uncompromising, forensic, constructive, and highly pragmatic critique of the entire system—from foundational philosophy to line-by-line implementation, user experience in the Nigerian context, Faststrap compliance, and AI prompt engineering.
>
> You must balance **intellectual honesty** with **practical utility**: point out architectural flaws, cognitive friction, bloat, and missed opportunities, but **always pair every critique with a clear, concrete, and implementable solution**.

---

## Part 1: The Core Philosophy & Foundational Dilemma

### 1.1 Deterministic Pre-Computed Curriculum vs. Embedding-Based RAG
SkuPhase made a deliberate architectural bet: **store the Nigerian National Curriculum (NERDC) as pre-computed, relational, structured data** (Subjects -> Grade Levels -> Terms -> Weeks -> Topics -> Learning Objectives) rather than indexing curriculum documents into a vector database for dynamic embedding retrieval (RAG).

**Your Audit Tasks:**
1. **Stress-test this premise**:
   - In low-resource, high-throughput edtech for developing nations, is relational deterministic retrieval genuinely superior to vector RAG? Evaluate along:
     - **Cost per generation** (zero embedding inference cost vs. vector API roundtrips).
     - **Determinism & Hallucination Resistance** (guaranteeing topics exist in the syllabus vs. fuzzy cosine similarity matching).
     - **Offline & Low-Bandwidth Capability** (can a 2MB SQLite/JSON file or cached SQL query run on a local school server or service worker without internet?).
     - **Latency** (SQL indexed lookup in <2ms vs. vector DB query + embedding generation in 200–600ms).
2. **Expose the Blind Spots of this Approach**:
   - What happens when a state government modifies its scheme of work (e.g., Lagos State Unified Scheme vs. Federal NERDC)?
   - How does a rigid relational schema handle cross-cutting themes (e.g., environmental degradation taught across Civic Education, Basic Science, and Geography)?
   - Can teachers easily inject custom, school-specific syllabus topics into this pre-computed model without breaking database foreign keys?
3. **Propose the Ideal Hybrid**:
   - How should SkuPhase structure the curriculum layer to maintain **100% deterministic syllabus adherence** while remaining flexible enough for dynamic school adaptations?

---

## Part 2: The Nigerian Operational Reality & Contextual Fit

SkuPhase is built for Nigerian primary and secondary schools (Private Christian/Muslim schools, Federal Unity Colleges, State public schools, and community schools across Lagos, Ibadan, Enugu, Kaduna, Abuja, and rural/semi-urban zones).

**Your Audit Tasks:**
1. **The Device & Infrastructure Reality Check**:
   - **Hardware**: School administrators frequently use 5-to-10-year-old Dell/HP laptops running Windows 7/10 or budget Tecno/Infinix/Samsung Android phones.
   - **Connectivity**: Mobile data bundles (MTN, Airtel, Glo) with fluctuating 3G/4G latency and high packet loss.
   - **Power**: Intermittent national grid ("NEPA/PHCN"), reliant on generators or solar inverters.
   - **Question**: *Does our current frontend asset pipeline, PWA configuration, and HTMX payload size genuinely respect this constraint, or are we secretly building a Silicon Valley luxury web app?*
2. **The Printing & Examination Hall Reality**:
   - In Nigeria, examination papers are **rarely printed in full color on individual clean sheets**.
   - **Monochrome LaserJet printers** (e.g., HP LaserJet 1020 / P1102) with generic refill toner are the industry standard.
   - **Paper Economy**: Schools split A4 sheets into half (A5 booklet format) or print tight 2-column landscape grids to minimize ream consumption across 500+ pupils.
   - **Exam Formats**:
     - *Continuous Assessment (CA) Tests*: 10–20 quick questions (often 1 double-sided page).
     - *Terminal Examinations*: Section A (Objectives / 40–60 MCQs), Section B (Theory / 4–6 structured short answers), Section C (Compulsory / Essay / Comprehension).
   - **Audit Question**: *How robust is SkuPhase's print engine? Does `@media print` generate compact, zero-toner-waste, 2-column exam papers with page breaks that never cut questions in half? Does it automatically generate a separate, compact Answer Key / Marking Guide for teachers?*
3. **The National Standardized Testing Benchmark**:
   - How well does SkuPhase align with:
     - **NCEE** (National Common Entrance Examination for Primary 6)?
     - **BECE** (Basic Education Certificate Examination / Junior WAEC for JSS3)?
     - **WAEC / WASSCE** (West African Senior School Certificate Examination for SS3)?
     - **NECO** (National Examinations Council for SS3)?
     - **JAMB / UTME** (Computer-Based Test format)?
   - *Should SkuPhase ingest past question datasets (2015–2024)? How should past questions interface with the Question Bank and AI Generation Engine without copyright infringement or stale rote repetition?*

---

## Part 3: Architecture & Backend Engineering Audit

SkuPhase uses **FastAPI + SQLAlchemy 2.0 (AsyncPG) + Pydantic v2 + PostgreSQL (designed for Supabase & FastAPI Cloud)**.

**Your Audit Tasks:**
1. **Supabase & Serverless Cloud Preparedness**:
   - Does the connection string handling, connection pooling, and migration setup support **Supabase Transaction Pooler (PgBouncer on port 6543)** and direct connection (port 5432)?
   - Are async sessions cleanly scoped with `async_sessionmaker` and `expire_on_commit=False` to prevent leaky connections in serverless/containerized environments?
   - How are migrations managed across environments (`alembic upgrade head`)? Is there any risk of schema drift or migration locking?
2. **Data Model & Schema Cohesion**:
   - Inspect models: `Exam`, `Question`, `ExamSection`, `QuestionBankItem`, `SchoolProfile`, `User`, `GenerationJob`.
   - Is there normalization leakage or unnecessary duplication between `ExamQuestion` and `QuestionBankItem`?
   - How does the two-way insertion (Exam -> Bank, Bank -> Exam section) behave under concurrency?
   - Is `usage_count` transactional or subject to race conditions?
3. **Workflow State Machine & Preflight Engine**:
   - Trace the lifecycle: `draft -> teacher_review -> in_review (school admin) -> approved -> exported/printed`.
   - Evaluate the **Preflight Check engine**:
     - Are the validation rules actually helpful (total marks sum consistency, question count vs. duration, missing correct options, missing answer explanations)?
     - Or do they create bureaucratic blockers that frustrate a teacher trying to print an exam 15 minutes before the bell?
4. **Scoring, Quality Metrics & Bloom's Taxonomy**:
   - Does the quality scoring algorithm provide actionable pedagogy metrics (knowledge vs. comprehension vs. application distribution), or is it a pseudo-scientific vanity widget?

---

## Part 4: Frontend Engineering & Faststrap Skill Compliance

The frontend is built using **FastHTML + Faststrap** (Bootstrap 5.3 Python components) + **HTMX**.

**Your Audit Tasks:**
1. **Compliance with the `faststrap-app-builder` Skill Rules**:
   - Check strict rules:
     - *Import boundaries*: Are there collisions between `faststrap.Button` and `fasthtml.common.Button as HtmlButton`?
     - *Input signatures*: Is `Input("name", ...)` used consistently, or did any positional args leak into child text (e.g. the stray `"q"` bug)?
     - *Attribute syntax*: Is `cls=` used everywhere instead of `class=`?
     - *Component ownership*: Are native Faststrap components (`Card`, `Badge`, `Row`, `Col`, `Select`, `EmptyState`, `Alert`) used in place of verbose raw HTML `Div` hierarchies?
2. **Custom CSS vs. Bootstrap 5.3 Utilities (The "CSS Bloat" Audit)**:
   - SkuPhase has an extensive `custom.css` (1600+ lines).
   - **Critique this directly**:
     - *How much of this CSS is reinventing Bootstrap 5.3 utilities that already exist out of the box?*
     - *Where did we write hardcoded colors (`#00412E`, `#96BF8A`) instead of leveraging CSS variables or Faststrap theme tokens?*
     - *Is the CSS maintainable, or has it become an accretive graveyard of one-off overrides?*
   - Provide a refactoring strategy to trim custom CSS down to true brand tokens and surface treatments.
3. **PWA, Service Worker & Asset Delivery**:
   - We transitioned from local vendored static files to **Faststrap CDN mode + Native PWA Service Worker caching**.
   - Evaluate the current Service Worker setup:
     - Does the caching strategy (`network-first` for app routes/local assets, `cache-first` for CDN libraries) completely eradicate Flash of Unstyled Content (FOUC)?
     - What happens if the school's internet cuts out mid-session? Does the teacher lose unsaved edits, or does the PWA handle offline resilience gracefully?
     - Is the Content Security Policy (CSP) tight yet functional?

---

## Part 5: User Journey & Frontend Experience Critique

Walk through the actual user journey of a Nigerian school educator and identify points of friction, confusion, or cognitive overload.

**Your Audit Tasks:**
1. **Onboarding & Auth Flow**:
   - Landing Page -> Sign Up -> Role / Persona Selection (`individual_teacher`, `school_admin`, `school_staff`) -> Workspace.
   - Is the dual-pathway (Individual Teacher vs. School Institution) intuitive?
   - Does it demand too much information upfront before delivering value?
2. **Dashboard**:
   - What is the first thing a teacher sees?
   - Does it clearly answer: *"What exams do I need to prepare or review right now?"*
   - Are the quick actions (`Generate with AI`, `Manual Exam`, `Question Bank`) prominent and self-explanatory?
3. **Exam Creation: The AI Wizard vs. Manual Composer**:
   - Compare the two paths:
     - **AI Wizard**: Step 1 (Curriculum picker) -> Step 2 (Structure & Sections) -> Step 3 (Difficulty & Bloom presets) -> Step 4 (Generation & Live Progress).
     - **Manual Composer**: Low-bandwidth, form-based, direct entry.
   - Where does the AI Wizard feel tedious? Can a teacher skip directly to generation with sensible defaults?
   - Does the live generation screen handle timeouts or network drops without failing the entire exam?
4. **Exam Detail, Curation & Question Editor**:
   - Review the tab structure: `Questions`, `Sections`, `Preflight Check`, `Quality & Taxonomy`, `Audit & Comments`.
   - Are 5 tabs too many for an overworked teacher? Should some be consolidated?
   - Question Editing: Inline edit vs. Modal edit. Which reduces friction when proofreading 40 questions?
   - KaTeX scientific formulas: Does math and chemistry syntax render smoothly without slowing down the DOM on a budget phone?
5. **Question Bank**:
   - Filter tray layout (mobile vs. desktop).
   - Live HTMX search with 300ms debounce.
   - Two-way question insertion workflow:
     - Inbound: Clicking "Add from Bank" on Exam Detail Section Header.
     - Outbound: Clicking "Add to Exam Section..." in Question Bank card kebab menu.
   - Is this two-way flow obvious, or is it hidden behind multi-step modals?

---

## Part 6: AI Prompt Engineering & Pedagogical Rigor

Examine the prompts, system instructions, and schemas sent to the LLM (Gemini / Claude / OpenAI) for generating exam questions.

**Your Audit Tasks:**
1. **Pedagogical Alignment**:
   - Do the generated questions genuinely reflect the Nigerian NERDC standard for that grade level (e.g. Primary 4 vs. JSS 2 vs. SS 3)?
   - Are the distractors in Multiple Choice Questions plausible, educational distractors, or are they lazy, obviously wrong fillers?
   - Does the prompt enforce the Nigerian cultural and currency context (Naira `₦`, Nigerian names, local flora/fauna, African geography) without sounding forced?
2. **Output Structure & Resilience**:
   - How does the system enforce strict JSON / structured outputs?
   - What happens when the model hallucinates markdown inside a JSON string or returns invalid escape sequences in LaTeX formulas?
   - Are chemistry formulas using valid `\ce{...}` (mhchem) syntax?
3. **Cost & Token Efficiency**:
   - Are the prompts bloated with repetitive few-shot examples?
   - Could prompt caching or structured schema enforcement reduce token usage by 50%?

---

## Part 7: The "Radical Simplicity" & Gap Analysis

### 7.1 What We Built That Is Unnecessary (Bloat Audit)
Identify features, UI elements, database columns, or endpoints that add engineering complexity without solving a core problem for the user:
- Are audit comment threads necessary for a 2-teacher primary school?
- Are we over-complicating quality dimension radars when teachers just want to know if question 12 has an answer key?
- What should be deprecated, hidden, or deferred?

### 7.2 What We Ought to Have Built That Is Missing (Gap Analysis)
Identify the high-leverage features that are currently missing from SkuPhase:
- **Printable OMR / Bubble Answer Sheets**: Can teachers print a standardized 50-question bubble sheet for rapid physical marking?
- **Marking Guide & Solution Sheet**: An automated, compact, 1-page printable marking guide for the teacher or exam supervisor.
- **Batch Class Export**: Exporting all subjects for Primary 5 (Maths, English, Basic Science, Social Studies) in one click for the school exam committee.
- **WhatsApp Integration / Offline SMS delivery**: How could exams be shared directly with teachers on low-end phones?

---

## Deliverable Format for the Audit

When responding to this audit prompt, present your analysis in the following structured report:

```markdown
# SkuPhase Comprehensive Architectural & UX Audit Report

## 1. Executive Summary & Core Verdict
[High-level evaluation: Grade the current system A-F across Simplicity, Robustness, Nigerian Context Fit, Code Quality]

## 2. Deep Critique of Core Premises
[Analysis of Relational vs. RAG, Determinism, Offline resilience]

## 3. Nigerian Operational Reality Check
[Hardware, printing, network, paper budget, curriculum alignment]

## 4. Backend & Database Architecture Audit
[Schema design, Supabase readiness, async performance, preflight validation]

## 5. Faststrap & Frontend Engineering Review
[Faststrap API compliance, CSS bloat vs. Bootstrap utilities, PWA & Service Worker review]

## 6. The User Journey Breakdown (Friction Points)
[Onboarding -> Dashboard -> Wizard -> Curation -> Print -> Question Bank]

## 7. AI Prompt & Pedagogy Analysis
[Prompt quality, distractors, LaTeX/KaTeX, NERDC calibration, hallucination mitigation]

## 8. Radical Simplification: What to Remove vs. What to Add
[Specific list of bloat to cut, and specific list of must-have gaps to fill]

## 9. Concrete, Prioritized Action Plan
[Step-by-step technical and UX tasks ordered from immediate quick wins to structural evolutions]
```
