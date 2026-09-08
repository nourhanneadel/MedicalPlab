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

### 3. 📖 NICE Guidelines RAG Knowledge Base
- **Hybrid Retrieval Engine (BM25 + Dense Embeddings + RRF):** Uses hybrid retrieval combining BM25 lexical search and dense semantic embeddings (`BAAI/bge-small-en-v1.5`) via Reciprocal Rank Fusion, indexing verified UK clinical guidelines for acute coronary syndromes, COPD, asthma, diabetes emergencies, hypertension pathways, stroke, and sepsis.

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
       └─── Medical RAG Engine ─────► NICE Guidelines Knowledge Base
```

---

## 📁 Project Structure

```
MedicalPlab/
├── main.py                      # FastAPI Backend Server
├── streamlit_app.py             # Streamlit Frontend Web App
├── Data/
│   ├── Guidelines/              # Official NICE Guidelines (Markdown)
│   ├── OSCE_Stations/           # PLAB 2 Clinical Scenarios & Rubrics
│   └── db/                      # SQLite Database (PLAB 1 & Uni questions)
├── Scripts/
│   ├── agents.py                # Multi-Agent AI System (Tutor, Patient, Examiner)
│   ├── rag_engine.py            # Clinical Knowledge RAG Search
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
embeddings via `BAAI/bge-small-en-v1.5`, combined through Reciprocal Rank Fusion) instead of simple
keyword matching. This was benchmarked against a 21-case evaluation set covering NICE guidelines on
cardiology, respiratory, endocrinology, hypertension, and acute emergencies — split into two batches
to test different retrieval demands, plus one out-of-domain negative control.

**Batch 1 — Exact clinical terminology** (14 cases, e.g. "PPCI", "GRACE score", "FEV1/FVC"):

| Metric | BM25-only | Hybrid (BM25+Dense) |
|---|---|---|
| Hit@1 | 100.00% | 100.00% |
| Hit@3 | 100.00% | 100.00% |
| MRR | 1.0000 | 1.0000 |

**Batch 2 — Paraphrased / lay-language queries** (6 cases, e.g. "clot-busting injection", "puffers for a chest flare up"):

| Metric | BM25-only | Hybrid (BM25+Dense) | Gain |
|---|---|---|---|
| Hit@1 | 33.33% | 50.00% | +16.67% |
| Hit@3 | 50.00% | 83.33% | +33.33% |
| MRR | 0.4821 | 0.7000 | +0.2179 |

**Takeaway:** BM25 alone is sufficient when queries use exact clinical terms, but dense embeddings
provide a substantial and measurable improvement when queries use everyday or paraphrased language —
the scenario most representative of real PLAB candidates and patients. In one case, BM25 completely
failed to retrieve the correct guideline section within the top 10 results, while the hybrid engine
recovered it at rank 5.

**Negative control:** An out-of-domain query (pediatric oncology, not covered by any guideline in
this repository) returned a fused retrieval score of 0.0325 — well below the confidence threshold —
confirming the system does not force irrelevant matches on unsupported topics.

*Full evaluation cases and reproducible benchmark script are available in `Data/eval/retrieval_eval_v1.json` and `Scripts/evaluate_retrieval.py`.*

---

## 📜 License & Compliance
Medical guidelines referenced adhere to public UK NHS & NICE open educational standards.
