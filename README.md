# 🩺 MedPlab-Agent: Dual-Brain Clinical Copilot & OSCE Simulator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Knowledge Base](https://img.shields.io/badge/RAG-NICE%20Guidelines-success.svg)](https://www.nice.org.uk/)

**MedPlab-Agent** is an Agentic GenAI platform designed to revolutionize medical licensing exam preparation (specifically the UK PLAB 1 & PLAB 2 / UKMLA exams). It bridges the gap between rote multiple-choice memorization and real-world clinical decision-making.

---

## 🌟 Key Features

### 1. 📝 Socratic Clinical Tutor (PLAB 1)
- **Beyond Static Answer Keys:** When a candidate answers an MCQ, the AI acts as a Senior Clinical Consultant using the Socratic method to explore clinical reasoning.
- **Differential Diagnosis Matrix:** Automatically breaks down every distractor option (A, B, C, D, E), explaining clinically why the correct choice is the gold standard and why each other option is ruled out.
- **Zero-Hallucination Guardrails:** Every explanation is anchored in official British clinical practice (**NICE Guidelines**) with direct section citations.
- **Dynamic Topic & Pool Filtering:** Candidates can select specific question pools (`All Approved Questions`, `Plabable`, or `Uni`) and filter by dynamically discovered clinical topics with intelligent practice fallback.

### 2. ⚡ GenAI Question Generator & Mandatory Human-Review Gate
- **Grounded On-Demand Question Generation:** Replaces static fixtures with on-demand PLAB 1 Single Best Answer (SBA) questions strictly grounded in the 88 canonical NICE & GMC guideline chunks (`Data/canonical_chunks.json`) across acute medicine, mental health, and medical ethics.
- **Strict Human-in-the-Loop Clinical Gate:** In compliance with clinical safety standards, **no AI-generated medical question is served to candidates without prior human review and approval**. All generated questions are placed into a `pending_review` queue.
- **Administrative Review Panel:** Built into both the Streamlit UI and secured FastAPI endpoints (`/admin/questions/*`), enabling clinician administrators to review clinical vignettes, examine choices A–E, inspect citations, and approve or reject questions with reviewer attribution.
- **Zero-Fabrication Guardrail:** Requires server-side LLM credentials; ungrounded heuristic fabrication is strictly blocked with explicit error feedback.

### 3. 👤 User Accounts, Question Gating & Server-Side Metering
- **User Authentication:** Multi-tenant candidate accounts with bcrypt password hashing and JWT bearer tokens (`/auth/signup`, `/auth/login`, `/auth/me`).
- **Free/Paid Tier Access Gating:** Free users have a configurable question quota (`free_tier_question_limit: 30`, managed via `Data/config/app_settings.json`). Once exhausted, an upgrade paywall is displayed.
- **Request Access Upgrade Flow:** Candidates can submit upgrade requests (`/billing/request-access`) directly from the paywall; administrators review and grant unlimited access via the admin dashboard.
- **Server-Side Key Management & Daily Rate Limits:** API keys (`GEMINI_API_KEY` / `OPENAI_API_KEY`) are managed server-side. Candidates are protected by per-user daily rate limiting (`daily_llm_limit: 20`) returning HTTP 429 when exceeded.

### 4. 🩺 Interactive Virtual Clinic (PLAB 2 OSCE Simulator)
- **Live Simulated Patients:** Roleplay consultations with realistic AI patients (e.g. *Arthur Pendelton* with acute chest pain or *Brenda Higgins* with chronic dyspnea).
- **Dynamic Hidden Backstory:** Patients have real emotions, vital signs, and fears, disclosing history progressively only when appropriately elicited by the doctor.
- **Senior GMC Examiner Agent:** At the end of the station, an automated examiner scores the consultation out of 15 across **History Taking (/5)**, **Clinical Judgment (/5)**, and **Communication & Empathy (/5)**, highlighting missed red flags and patient safety assessments.

### 5. 📖 Multi-Source Clinical & Regulatory Knowledge Base
- **Hybrid Retrieval Engine (BM25 + Dense Embeddings + RRF):** Uses hybrid retrieval combining BM25 lexical search and dense semantic embeddings (`BAAI/bge-small-en-v1.5`) via Reciprocal Rank Fusion across 88 canonical chunks spanning three major authorities and clinical domains:
  - **NICE Acute Clinical Guidelines (`acute_physical_medicine`):** Verified UK management protocols for acute coronary syndromes (NG185), COPD and acute asthma (NG115/NG80), type 2 diabetes (NG28), hypertension (NG136), and acute stroke & sepsis emergencies (NG128/NG51).
  - **NICE Mental Health (`mental_health`):** Depression in adults (NG222), covering recognition, PHQ-9 severity thresholds, stepped care, first-line pharmacotherapy, and augmentation strategies.
  - **GMC Professional Standards (`ethics_professionalism`):** *Good Medical Practice (2024)* across Domains 1–4, covering statutory regulatory duties, patient consent, confidentiality, candour, and probity.
- **Domain-Aware Contamination Prevention:** Every chunk is classified with an extensible `clinical_domain` attribute (`acute_physical_medicine`, `mental_health`, `ethics_professionalism`). The system combines prompt-level strict silent exclusion and domain-aware plurality fallback in `Scripts/agents.py` to prevent cross-specialty and cross-authority contamination in retrieved results and generated advice.

---

## 🏗️ System Architecture

```
User (Medical Candidate / Clinician Admin)
       │
       ▼
Streamlit Interactive UI (Port 8501)
 ├── Candidate Portal (Auth, PLAB 1 Smart Exam, OSCE Simulator, Guidelines)
 └── Admin Dashboard (Grounded Question Generator, Human Review Queue, Access Requests)
       │
       ▼
FastAPI Backend (Port 8000)
 ├── Question Generator ────► Strictly Grounded in Canonical Chunks (Pending Review Gate)
 ├── Socratic Tutor Agent ──► Differential Diagnosis Matrix & Zero-Hallucination Advice
 ├── Virtual Patient Agent ─► Dynamic Clinical Roleplay (5 Stations)
 ├── GMC Examiner Agent ────► Scoring & Rubric Feedback (/15)
 ├── Auth & Metering DB ────► Bcrypt Auth, Quota Capping, Daily Rate Limits, Access Approval
 └── Medical RAG Engine ────► Hybrid Retrieval (BM25 + Dense + RRF) across NICE & GMC
```

---

## 📁 Project Structure

```
MedicalPlab/
├── main.py                      # FastAPI Backend Server (Candidate & Admin Endpoints)
├── streamlit_app.py             # Streamlit Frontend Web App (Candidate & Admin Views)
├── Dockerfile.backend           # Container configuration for Backend
├── Dockerfile.frontend          # Container configuration for Frontend
├── docker-compose.yml           # Multi-container orchestration
├── schemas/                     # JSON Schemas for Document & Chunk validation
│   ├── document.schema.json
│   └── chunk.schema.json
├── Data/
│   ├── config/                  # Runtime Configuration
│   │   └── app_settings.json    # Dynamic quotas (free_tier_question_limit, daily_llm_limit)
│   ├── Guidelines/              # Clinical & Regulatory Guidelines (Markdown)
│   │   ├── NICE/                # Acute & Mental Health Guidelines
│   │   │   ├── nice_acs_chest_pain.md
│   │   │   ├── nice_acute_emergencies.md
│   │   │   ├── nice_copd_asthma.md
│   │   │   ├── nice_diabetes_type2.md
│   │   │   ├── nice_hypertension.md
│   │   │   └── nice_depression_ng222.md
│   │   └── GMC/                 # Regulatory & Professional Ethics
│   │       └── good_medical_practice.md
│   ├── canonical_chunks.json    # 88 Canonical Chunks with clinical_domain metadata
│   ├── eval/                    # Retrieval evaluation suite & benchmarks
│   │   └── retrieval_eval_v1.json
│   ├── OSCE_Stations/           # PLAB 2 Clinical Scenarios & Rubrics
│   │   └── stations.json
│   └── db/                      # SQLite Database (Auth, Access, Questions, Generated Pool)
│       └── merged.db
├── Scripts/
│   ├── question_generator.py    # GenAI question generator, migration & human-review gate
│   ├── auth_db.py               # User accounts, JWT auth, metering, and access requests
│   ├── agents.py                # Multi-Agent AI System (Tutor, Patient, Examiner)
│   ├── rag_engine.py            # Hybrid RAG Engine (BM25 + Dense + RRF)
│   ├── build_canonical_chunks.py# Canonical chunking & domain classification
│   ├── evaluate_retrieval.py    # 4-batch retrieval ablation & contamination audit
│   ├── verify_question_system.py# Comprehensive verification suite (6 mandatory checks)
│   ├── populate_medical_data.py # Automated Data Setup Script
│   ├── utils.py                 # PDF & Data extraction utilities
│   ├── RetrieveQuestionsFromPlabable.py
│   └── RetrieveQuestionsFromUni.py
├── requirements.txt             # Python Dependencies
├── pyproject.toml               # Project Metadata
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/MedicalPlab.git
cd MedicalPlab
```

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate environment (Windows)
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Data & Guidelines
```bash
python Scripts/populate_medical_data.py
```

### 4. Run the Backend API
```bash
uvicorn main:app --reload --port 8000
```
Interactive API docs available at: `http://localhost:8000/docs`

### 5. Run the Streamlit Interface
In a new terminal:
```bash
streamlit run streamlit_app.py
```
Open your browser at: `http://localhost:8501`

---

## 🐳 Run with Docker

Run the entire MedPlab-Agent stack (FastAPI backend + Streamlit frontend) with a single Docker Compose command without needing to manually configure a local Python environment.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) (included in Docker Desktop)

### 1. Environment Configuration (Optional)
Copy the example environment template and configure your API keys if available (the application functions in offline heuristic mode if left unconfigured):
```bash
cp .env.example .env
```

### 2. Build & Launch Containers
```bash
docker compose up --build
```
Or run in detached background mode:
```bash
docker compose up --build -d
```

### 3. Access Services
- **FastAPI Backend & Interactive Swagger Docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Streamlit Interactive UI:** [`http://localhost:8501`](http://localhost:8501)

### Features & Persistence
- **Zero Re-download:** Embedding model weights are cached in a named volume (`medplab_hf_cache`) so models persist across container restarts.
- **Hot Data Mounting:** The `Data/` directory is mounted via volume, allowing SQLite databases and NICE guideline markdown files to be updated dynamically without image rebuilds.
- **Fast Rebuilds:** Layer caching separates dependency installation from application code.

---

## 🛠️ Question Bank Administration & Clinical Safety

To ensure patient safety and high pedagogical quality, MedPlab-Agent enforces a **strict human-review approval gate** before any AI-generated question is served to real medical candidates.

### 1. Streamlit Admin Dashboard
1. Open [`http://localhost:8501`](http://localhost:8501) and locate **`🛠️ Question Bank Admin`** in the left sidebar.
2. Enter the configured `ADMIN_API_KEY` (e.g. `medplab_admin_secret_98765`).
3. **⚡ Generate Questions:** Select clinical domain (`acute_physical_medicine`, `mental_health`, `ethics_professionalism`), optional keyword/topic, and count (1–5). Questions are generated strictly grounded in canonical chunks and stored with `review_status = 'pending_review'`.
4. **📋 Review Queue:** Inspect full clinical vignettes, choices A through E, correct answers, explanations, and exact NICE/GMC citations. Click **`✅ Approve`** to make a question live for candidates, or **`❌ Reject`** to permanently discard it.
5. **👥 User Access Upgrades:** Review pending upgrade requests from free-tier candidates and grant full access with a single click.

### 2. Admin REST API Endpoints

All admin endpoints require the `X-Admin-Key` header:

```bash
# 1. Generate questions on-demand (inserted as pending_review)
curl -X POST "http://localhost:8000/admin/questions/generate" \
     -H "Content-Type: application/json" \
     -H "X-Admin-Key: <YOUR_ADMIN_API_KEY>" \
     -d '{"clinical_domain": "mental_health", "topic": "Depression", "count": 2}'

# 2. List all questions awaiting review
curl -X GET "http://localhost:8000/admin/questions/pending" \
     -H "X-Admin-Key: <YOUR_ADMIN_API_KEY>"

# 3. Approve a question for candidate delivery
curl -X POST "http://localhost:8000/admin/questions/16/approve?reviewed_by=DrLeadExaminer" \
     -H "X-Admin-Key: <YOUR_ADMIN_API_KEY>"

# 4. Reject an unsuitable question
curl -X POST "http://localhost:8000/admin/questions/17/reject?reviewed_by=QualityAuditor" \
     -H "X-Admin-Key: <YOUR_ADMIN_API_KEY>"
```

---

## ⚙️ Configuration & Environment Variables

| Variable / Setting | Default / Location | Description |
| :--- | :--- | :--- |
| `ADMIN_API_KEY` | Environment variable | **Required for Admin operations**. Read strictly with **NO default fallback**. If unset, admin endpoints return HTTP 503. |
| `GEMINI_API_KEY` | Environment variable | Server-side key for Google Gemini 1.5/2.0 Flash models. |
| `OPENAI_API_KEY` | Environment variable | Server-side key for OpenAI models (fallback provider). |
| `free_tier_question_limit` | `Data/config/app_settings.json` | Number of distinct questions a free user can practice (default: `30`) before triggering the paywall. Dynamic without restart. |
| `daily_llm_limit` | `Data/config/app_settings.json` | Daily LLM reasoning/chat calls per user (default: `20`) returning HTTP 429 when exceeded. Dynamic without restart. |

---

## 🧪 Evaluation & Verification

The test suite validates both question generation and clinical review gating:

```bash
# Run inside Docker backend container:
docker exec medplab-backend python Scripts/verify_question_system.py
```

### Mandatory Verification Checklist (100% Pass Rate)
- **Check 1 (On-Demand Generation):** Calls `/admin/questions/generate` for `clinical_domain="mental_health"` and verifies rows are created with `status="pending_review"`.
- **Check 2 (Candidate Gating):** Queries candidate endpoints (`/questions`, `/plabable`) and confirms pending questions are strictly invisible to candidates.
- **Check 3 (Review & Quota Metering):** Approves a pending question via `/admin/questions/{id}/approve`, confirms it immediately becomes servable to candidates, and verifies it counts toward candidate quota in `/auth/me`. Confirms rejection workflow.
- **Check 4 (Legacy Migration):** Confirms all 15 pre-existing questions were migrated as pre-approved and remain fully functional.
- **Check 5 (Approved-Only Topics):** Confirms `GET /topics` strictly returns topics that have at least one approved question.
- **Check 6 (Zero-Fabrication Guardrail):** Confirms that missing API keys return clear error feedback (`RuntimeError` / HTTP 500) and ungrounded fabrication is blocked.

---

## 📊 Retrieval Evaluation Results

The RAG knowledge base uses a **hybrid retrieval engine** (BM25 lexical search + dense semantic
embeddings via `BAAI/bge-small-en-v1.5`, combined through Reciprocal Rank Fusion) across 88 canonical
chunks rather than simple keyword matching. This was benchmarked against an expanded 46-case evaluation
suite (`Data/eval/retrieval_eval_v1.json`) spanning four distinct batches across all three indexed sources,
plus three out-of-domain negative controls:

### Batch 1 — NICE Acute: Exact Clinical Terminology (14 cases, TC-001 to TC-014)
*Tests exact guideline vocabulary (e.g. "PPCI", "GRACE score", "FEV1/FVC", "Alteplase").*

| Metric | BM25-only | Hybrid (BM25+Dense) | Gain |
|---|---|---|---|
| Hit@1 | 100.00% | 100.00% | 0.00% |
| Hit@3 | 100.00% | 100.00% | 0.00% |
| MRR | 1.0000 | 1.0000 | 0.0000 |
| nDCG@10 | 1.0000 | 1.0000 | 0.0000 |

### Batch 2 — NICE Acute: Paraphrased / Lay Queries (6 cases, TC-016 to TC-021)
*Tests everyday colloquial phrasing (e.g. "clot-busting injection", "puffers for a chest flare up").*

| Metric | BM25-only | Hybrid (BM25+Dense) | Gain |
|---|---|---|---|
| Hit@1 | 16.67% | 33.33% | +16.66% |
| Hit@3 | 33.33% | 33.33% | 0.00% |
| MRR | 0.2500 | 0.3750 | +0.1250 |
| nDCG@10 | 0.2718 | 0.4051 | +0.1333 |

### Batch 3 — GMC Ethics & Professional Standards (12 cases, TC-022 to TC-033)
*Tests regulatory concepts, patient autonomy, confidentiality, consent, and duty of candour.*

| Metric | BM25-only | Hybrid (BM25+Dense) | Gain |
|---|---|---|---|
| Hit@1 | 75.00% | 91.67% | +16.67% |
| Hit@3 | 83.33% | 91.67% | +8.34% |
| MRR | 0.8000 | 0.9167 | +0.1167 |
| nDCG@10 | 0.8267 | 0.9167 | +0.0900 |

### Batch 4 — NICE Mental Health: NG222 Depression in Adults (11 cases, TC-035 to TC-045)
*Tests psychiatric management, PHQ-9 thresholds, stepped care, and antidepressant switching.*

| Metric | BM25-only | Hybrid (BM25+Dense) | Gain |
|---|---|---|---|
| Hit@1 | 100.00% | 100.00% | 0.00% |
| Hit@3 | 100.00% | 100.00% | 0.00% |
| MRR | 1.0000 | 1.0000 | 0.0000 |
| nDCG@10 | 1.0000 | 1.0000 | 0.0000 |

### Multi-Source Overall Performance (43 Answerable Cases)

| Metric | BM25-only | Hybrid (BM25+Dense) | Gain |
|---|---|---|---|
| **Hit@1** | 81.40% | **88.37%** | **+6.97%** |
| **Hit@3** | 86.05% | **88.37%** | **+2.32%** |
| **MRR** | 0.8395 | **0.8895** | **+0.0500** |
| **nDCG@10** | 0.8500 | **0.8937** | **+0.0437** |

**Takeaway:** While BM25 performs robustly on structured textbook terminology, dense semantic embeddings deliver critical gains on lay-language paraphrased questions (+16.66% Hit@1, +0.1250 MRR) and GMC ethical scenarios (+16.67% Hit@1, +8.34% Hit@3), bringing overall multi-source Hit@1 to **88.37%**.

### Negative Controls (Out-of-Domain Safety)
To verify guardrails against hallucinations on unsupported clinical specialties or legislation:
- **TC-015 (Pediatric Oncology):** Query on pediatric Ewing sarcoma margins returned a low max fused score of 0.0164 (**PASS**).
- **TC-034 (Corporate Crime Legislation):** Query on Section 7 of the UK Bribery Act 2010 returned a low max fused score of 0.0313 (**PASS**).
- **TC-046 (Paediatric Depression):** Query on adolescent depression pathways returned a low max fused score of 0.0312, correctly recognizing NICE NG222's scope restriction to adults ≥ 18 (**PASS**).

### Cross-Source Contamination Audit & Resolution
During multi-source indexing, evaluation revealed that lay-language NICE acute queries occasionally pulled NG222 Depression chunks at rank 2–3 (25.0% overlap) due to shared metabolic/clinical terms (e.g. HbA1c monitoring), and GMC ethical paragraphs (5.0% overlap). 

To ensure complete clinical separation:
1. **Schema & Chunk Classification:** Every chunk is assigned a `clinical_domain` (`acute_physical_medicine`, `mental_health`, `ethics_professionalism`).
2. **Prompt-Layer Strict Silent Exclusion:** The LLM tutor prompt mandates silent exclusion of off-specialty and off-authority excerpts with zero meta-commentary, preventing leaked references in final explanations.
3. **Domain-Aware Plurality Fallback:** The heuristic fallback uses plurality domain voting across top retrieved hits to guard against out-of-specialty rank-1 chunks when running in offline mode.

*Live end-to-end API testing across all contaminated test cases verified 100% elimination of cross-specialty contamination in user-facing tutor outputs.*

*Full evaluation cases and reproducible benchmark script are available in `Data/eval/retrieval_eval_v1.json` and `Scripts/evaluate_retrieval.py`.*

---

## 📜 License & Compliance
Medical guidelines referenced adhere to public UK NHS & NICE open educational standards.
