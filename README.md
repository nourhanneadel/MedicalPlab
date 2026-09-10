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

### 2. 🩺 Interactive Virtual Clinic (PLAB 2 OSCE Simulator)
- **Live Simulated Patients:** Roleplay consultations with realistic AI patients (e.g. *Arthur Pendelton* with acute chest pain or *Brenda Higgins* with chronic dyspnea).
- **Dynamic Hidden Backstory:** Patients have real emotions, vital signs, and fears, disclosing history progressively only when appropriately elicited by the doctor.
- **Senior GMC Examiner Agent:** At the end of the station, an automated examiner scores the consultation out of 15 across **History Taking (/5)**, **Clinical Judgment (/5)**, and **Communication & Empathy (/5)**, highlighting missed red flags and patient safety assessments.

### 3. 📖 Multi-Source Clinical & Regulatory Knowledge Base
- **Hybrid Retrieval Engine (BM25 + Dense Embeddings + RRF):** Uses hybrid retrieval combining BM25 lexical search and dense semantic embeddings (`BAAI/bge-small-en-v1.5`) via Reciprocal Rank Fusion across 88 canonical chunks spanning three major authorities and clinical domains:
  - **NICE Acute Clinical Guidelines (`acute_physical_medicine`):** Verified UK management protocols for acute coronary syndromes (NG185), COPD and acute asthma (NG115/NG80), type 2 diabetes (NG28), hypertension (NG136), and acute stroke & sepsis emergencies (NG128/NG51).
  - **NICE Mental Health (`mental_health`):** Depression in adults (NG222), covering recognition, PHQ-9 severity thresholds, stepped care, first-line pharmacotherapy, and augmentation strategies.
  - **GMC Professional Standards (`ethics_professionalism`):** *Good Medical Practice (2024)* across Domains 1–4, covering statutory regulatory duties, patient consent, confidentiality, candour, and probity.
- **Domain-Aware Contamination Prevention:** Every chunk is classified with an extensible `clinical_domain` attribute (`acute_physical_medicine`, `mental_health`, `ethics_professionalism`). The system combines prompt-level strict silent exclusion and domain-aware plurality fallback in `Scripts/agents.py` to prevent cross-specialty and cross-authority contamination in retrieved results and generated advice.

---

## 🏗️ System Architecture

```
User (Medical Candidate)
       │
       ▼
Streamlit Interactive UI (Port 8501)
       │
       ▼
FastAPI Backend (Port 8000)
       ├─── Socratic Tutor Agent ───► Differential Diagnosis Engine
       ├─── Virtual Patient Agent ──► Dynamic Clinical Roleplay
       ├─── GMC Examiner Agent ─────► Scoring & Rubric Feedback
       └─── Medical RAG Engine ─────► Multi-Source Knowledge Base (NICE + GMC)
```

---

## 📁 Project Structure

```
MedicalPlab/
├── main.py                      # FastAPI Backend Server
├── streamlit_app.py             # Streamlit Frontend Web App
├── Dockerfile.backend           # Container configuration for Backend
├── Dockerfile.frontend          # Container configuration for Frontend
├── docker-compose.yml           # Multi-container orchestration
├── schemas/                     # JSON Schemas for Document & Chunk validation
│   ├── document.schema.json
│   └── chunk.schema.json
├── Data/
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
│   └── db/                      # SQLite Database (PLAB 1 & Uni questions)
│       └── merged.db
├── Scripts/
│   ├── agents.py                # Multi-Agent AI System (Tutor, Patient, Examiner)
│   ├── rag_engine.py            # Hybrid RAG Engine (BM25 + Dense + RRF)
│   ├── build_canonical_chunks.py# Canonical chunking & domain classification
│   ├── evaluate_retrieval.py    # 4-batch retrieval ablation & contamination audit
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

## 🧪 Evaluation & Verification

- **Automated Verification:** All endpoints (`/plabable`, `/osce/stations`, `/osce/chat`, `/osce/evaluate`, `/tutor/analyze`, `/rag/search`) are verified with 100% pass rates.
- **Offline Demonstration Mode:** Works with high-quality clinical heuristic fallbacks even without an external API key, ensuring reliable presentation during live competition pitches.
- **API Keys Supported:** Direct support for Google Gemini 1.5/2.0 Flash (`GEMINI_API_KEY`) and OpenAI (`OPENAI_API_KEY`).

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
