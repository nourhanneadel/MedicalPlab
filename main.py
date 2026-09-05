import os
import json
from fastapi import FastAPI, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from Scripts.RetrieveQuestionsFromPlabable import getRandom_p_questions
from Scripts.RetrieveQuestionsFromUni import getRandom_u_questions
from Scripts.rag_engine import rag_engine
from Scripts.agents import MedicalAgents

DB_PATH = "Data/db/merged.db"
OSCE_PATH = "Data/OSCE_Stations/stations.json"

app = FastAPI(
    title="MedPlab-Agent API",
    description="Dual-Brain GenAI API for Medical Exams: Socratic PLAB 1 Tutor & PLAB 2 OSCE Clinical Simulator.",
    version="2.0.0"
)

# -----------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------
class TutorRequest(BaseModel):
    question: str
    choices: List[str]
    answer: str
    explanation: Optional[str] = ""
    user_choice: str
    api_key: Optional[str] = None

class OSCEChatRequest(BaseModel):
    station_id: str
    chat_history: List[Dict[str, str]]
    message: str
    api_key: Optional[str] = None

class OSCEEvaluateRequest(BaseModel):
    station_id: str
    chat_history: List[Dict[str, str]]
    api_key: Optional[str] = None

# Helper to load OSCE stations
def _load_stations() -> List[Dict[str, Any]]:
    if not os.path.exists(OSCE_PATH):
        return []
    with open(OSCE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------------------------------------------------
# Original Endpoints (Preserved for backwards compatibility)
# -----------------------------------------------------------------
@app.get("/plabable", summary="Get random questions for plabable", response_model=List[dict])
def get_plabable_questions(n: int = Query(10, gt=0, le=100), topic: Optional[str] = None):
    try:
        if topic:
            questions = getRandom_p_questions(n=n, topic=topic.upper(), db_path=DB_PATH)
        else:
            questions = getRandom_p_questions(n=n, db_path=DB_PATH)
        return questions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/uni", summary="Get random questions for uni", response_model=List[dict])
def get_uni_questions(n: int = Query(10, gt=0, le=100), topic: Optional[str] = None, level: Optional[int] = None):
    try:
        questions = getRandom_u_questions(n=n, topic=topic, level=level, db_path=DB_PATH)
        return questions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------------------------------------------
# GenAI Feature 1: Socratic Tutor & Differential Diagnosis
# -----------------------------------------------------------------
@app.post("/tutor/analyze", summary="Analyze answer with Socratic guidance & differential diagnosis")
def tutor_analyze(req: TutorRequest):
    try:
        analysis = MedicalAgents.socratic_tutor_analysis(
            question_data={
                "question": req.question,
                "choices": req.choices,
                "answer": req.answer,
                "explanation": req.explanation
            },
            user_choice=req.user_choice,
            api_key=req.api_key
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------
# GenAI Feature 2: NICE Guidelines RAG Search
# -----------------------------------------------------------------
@app.get("/rag/search", summary="Search NICE clinical guidelines")
def rag_search(query: str = Query(..., description="Medical topic or clinical keyword")):
    try:
        results = rag_engine.search(query, top_k=3)
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------
# GenAI Feature 3: PLAB 2 OSCE Virtual Clinic & Simulation
# -----------------------------------------------------------------
@app.get("/osce/stations", summary="List all OSCE clinical stations")
def list_osce_stations():
    stations = _load_stations()
    # Return summaries without revealing full patient secrets
    summaries = []
    for s in stations:
        summaries.append({
            "id": s["id"],
            "title": s["title"],
            "specialty": s["specialty"],
            "patient_name": s["patient_name"],
            "patient_age": s["patient_age"],
            "patient_gender": s["patient_gender"],
            "vital_signs": s["vital_signs"],
            "candidate_brief": s["candidate_brief"]
        })
    return summaries

@app.post("/osce/chat", summary="Interact with the Virtual Patient")
def osce_chat(req: OSCEChatRequest):
    stations = _load_stations()
    station = next((s for s in stations if s["id"] == req.station_id), None)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {req.station_id} not found")

    reply = MedicalAgents.virtual_patient_reply(
        station=station,
        chat_history=req.chat_history,
        user_message=req.message,
        api_key=req.api_key
    )
    return {"reply": reply}

@app.post("/osce/evaluate", summary="Evaluate OSCE consultation via Examiner Agent")
def osce_evaluate(req: OSCEEvaluateRequest):
    stations = _load_stations()
    station = next((s for s in stations if s["id"] == req.station_id), None)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {req.station_id} not found")

    evaluation = MedicalAgents.evaluate_osce_consultation(
        station=station,
        chat_history=req.chat_history,
        api_key=req.api_key
    )
    return evaluation

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
