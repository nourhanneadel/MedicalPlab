import os
import json
from fastapi import FastAPI, HTTPException, Query, Body, Header, Depends
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel

from Scripts.RetrieveQuestionsFromPlabable import getRandom_p_questions
from Scripts.RetrieveQuestionsFromUni import getRandom_u_questions
from Scripts.rag_engine import rag_engine
from Scripts.agents import MedicalAgents
from Scripts.question_generator import (
    init_generated_questions_table,
    migrate_existing_questions,
    generate_question,
    get_approved_questions,
    approve_question,
    reject_question,
    get_pending_questions,
    get_approved_topics
)
from Scripts.auth_db import (
    init_auth_tables,
    create_user,
    authenticate_user,
    get_user_by_id,
    create_access_token,
    decode_access_token,
    get_app_settings,
    get_distinct_questions_accessed_count,
    get_accessed_question_ids,
    record_question_access,
    increment_questions_answered,
    check_and_increment_daily_llm_limit,
    create_access_request,
    get_user_access_request_status,
    get_all_access_requests,
    approve_access_request
)

DB_PATH = "Data/db/merged.db"
OSCE_PATH = "Data/OSCE_Stations/stations.json"

app = FastAPI(
    title="MedPlab-Agent API",
    description="Dual-Brain GenAI API for Medical Exams: Socratic PLAB 1 Tutor & PLAB 2 OSCE Clinical Simulator.",
    version="2.1.0"
)

# Initialize authentication, metering, and question generator tables on startup
@app.on_event("startup")
def startup_event():
    init_auth_tables(db_path=DB_PATH)
    init_generated_questions_table(db_path=DB_PATH)
    migrate_existing_questions(db_path=DB_PATH)

# -----------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------
class AuthRequest(BaseModel):
    email: str
    password: str

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

class GenerateQuestionRequest(BaseModel):
    clinical_domain: str
    topic: Optional[str] = None
    count: int = 1
    api_key: Optional[str] = None

# Helper to load OSCE stations
def _load_stations() -> List[Dict[str, Any]]:
    if not os.path.exists(OSCE_PATH):
        return []
    with open(OSCE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Helper for JWT user authentication
def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication token required. Please log in.")
    token = authorization[7:].strip() if authorization.startswith("Bearer ") else authorization.strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token. Please log in again.")
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    user = get_user_by_id(user_id, db_path=DB_PATH)
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")
    return user

# -----------------------------------------------------------------
# Authentication Endpoints
# -----------------------------------------------------------------
@app.post("/auth/signup", summary="Register a new user account")
def auth_signup(req: AuthRequest):
    ok, msg, user = create_user(req.email, req.password, db_path=DB_PATH)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    token = create_access_token({"sub": str(user["id"]), "email": user["email"]})
    return {"token": token, "user": user, "message": msg}

@app.post("/auth/login", summary="Authenticate an existing user")
def auth_login(req: AuthRequest):
    user = authenticate_user(req.email, req.password, db_path=DB_PATH)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token({"sub": str(user["id"]), "email": user["email"]})
    return {"token": token, "user": user}

@app.get("/auth/me", summary="Get current user details and usage statistics")
def auth_me(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    distinct_count = get_distinct_questions_accessed_count(user["id"], db_path=DB_PATH)
    settings = get_app_settings()
    access_status = get_user_access_request_status(user["id"], db_path=DB_PATH)
    return {
        "user": user,
        "distinct_questions_accessed": distinct_count,
        "free_tier_question_limit": int(settings.get("free_tier_question_limit", 30)),
        "daily_llm_limit": int(settings.get("daily_llm_limit", 20)),
        "access_request_status": access_status
    }

# -----------------------------------------------------------------
# -----------------------------------------------------------------
# Gated Question Endpoints (Approved Clinical Questions)
# -----------------------------------------------------------------
@app.get("/topics", summary="Get distinct topics available among approved questions")
def get_topics():
    return get_approved_topics(db_path=DB_PATH)

@app.get("/questions", summary="Get random approved clinical questions with tier gating")
def get_questions_unified(
    n: int = Query(5, gt=0, le=100),
    clinical_domain: Optional[str] = None,
    topic: Optional[str] = None,
    source: str = "questions",
    authorization: Optional[str] = Header(None)
):
    user = get_current_user(authorization)
    user_id = user["id"]
    sub_status = user["subscription_status"]

    settings = get_app_settings()
    free_limit = int(settings.get("free_tier_question_limit", 30))
    distinct_accessed = get_distinct_questions_accessed_count(user_id, db_path=DB_PATH)

    if sub_status == "free" and distinct_accessed >= free_limit:
        return {
            "paywall_triggered": True,
            "message": f"Free tier limit reached ({distinct_accessed}/{free_limit} questions accessed). Request full access to unlock the complete question bank.",
            "distinct_accessed": distinct_accessed,
            "free_limit": free_limit,
            "questions": []
        }

    try:
        limit_to_fetch = n
        exclude_ids = None
        if sub_status == "free":
            seen_ids = get_accessed_question_ids(user_id, source, db_path=DB_PATH)
            remaining = max(0, free_limit - distinct_accessed)
            limit_to_fetch = min(n, remaining)
            exclude_ids = seen_ids

        questions = get_approved_questions(
            clinical_domain=clinical_domain,
            topic=topic,
            exclude_ids=exclude_ids,
            limit=limit_to_fetch,
            db_path=DB_PATH
        )

        q_ids = [q["id"] for q in questions if "id" in q]
        record_question_access(user_id, source, q_ids, db_path=DB_PATH)
        return questions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/plabable", summary="Get random questions from PLAB pool with tier gating (serves approved questions)")
def get_plabable_questions(
    n: int = Query(5, gt=0, le=100),
    topic: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    return get_questions_unified(n=n, clinical_domain=None, topic=topic, source="plabable", authorization=authorization)

@app.get("/uni", summary="Get random questions from University pool with tier gating (serves approved questions)")
def get_uni_questions(
    n: int = Query(10, gt=0, le=100),
    topic: Optional[str] = None,
    level: Optional[int] = None,
    authorization: Optional[str] = Header(None)
):
    return get_questions_unified(n=n, clinical_domain="acute_physical_medicine", topic=topic, source="uni", authorization=authorization)

# -----------------------------------------------------------------
# GenAI Feature 1: Socratic Tutor & Differential Diagnosis (Metered)
# -----------------------------------------------------------------
@app.post("/tutor/analyze", summary="Analyze answer with Socratic guidance & differential diagnosis")
def tutor_analyze(req: TutorRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    allowed, current_count, max_limit = check_and_increment_daily_llm_limit(user["id"], db_path=DB_PATH)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached ({max_limit} calls). Please try again tomorrow."
        )

    # Server-side key management: use environment variables strictly
    server_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    try:
        analysis = MedicalAgents.socratic_tutor_analysis(
            question_data={
                "question": req.question,
                "choices": req.choices,
                "answer": req.answer,
                "explanation": req.explanation
            },
            user_choice=req.user_choice,
            api_key=server_key
        )
        increment_questions_answered(user["id"], db_path=DB_PATH)
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
# GenAI Feature 3: PLAB 2 OSCE Virtual Clinic & Simulation (Metered)
# -----------------------------------------------------------------
@app.get("/osce/stations", summary="List all OSCE clinical stations")
def list_osce_stations():
    stations = _load_stations()
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
def osce_chat(req: OSCEChatRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    allowed, current_count, max_limit = check_and_increment_daily_llm_limit(user["id"], db_path=DB_PATH)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached ({max_limit} calls). Please try again tomorrow."
        )

    stations = _load_stations()
    station = next((s for s in stations if s["id"] == req.station_id), None)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {req.station_id} not found")

    server_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    reply = MedicalAgents.virtual_patient_reply(
        station=station,
        chat_history=req.chat_history,
        user_message=req.message,
        api_key=server_key
    )
    return {"reply": reply}

@app.post("/osce/evaluate", summary="Evaluate OSCE consultation via Examiner Agent")
def osce_evaluate(req: OSCEEvaluateRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    allowed, current_count, max_limit = check_and_increment_daily_llm_limit(user["id"], db_path=DB_PATH)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily limit reached ({max_limit} calls). Please try again tomorrow."
        )

    stations = _load_stations()
    station = next((s for s in stations if s["id"] == req.station_id), None)
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {req.station_id} not found")

    server_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    evaluation = MedicalAgents.evaluate_osce_consultation(
        station=station,
        chat_history=req.chat_history,
        api_key=server_key
    )
    return evaluation

# -----------------------------------------------------------------
# Billing & Manual Access Request Flow
# -----------------------------------------------------------------
@app.post("/billing/request-access", summary="Submit a manual request for full access upgrade")
def billing_request_access(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    ok, msg, data = create_access_request(user["id"], user["email"], db_path=DB_PATH)
    return {"success": ok, "message": msg, "data": data}

@app.get("/billing/request-status", summary="Check access upgrade request status")
def billing_request_status(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    status = get_user_access_request_status(user["id"], db_path=DB_PATH)
    return {"status": status}

# -----------------------------------------------------------------
# Admin Endpoints (Access Requests Approval)
# -----------------------------------------------------------------
# WARNING: ADMIN_API_KEY must be read strictly from the environment with NO default value.
# Under NO circumstances should any fallback secret or hardcoded default ever be added here.

def verify_admin_key(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key or not admin_key.strip():
        raise HTTPException(
            status_code=503,
            detail="Admin functionality is disabled: ADMIN_API_KEY environment variable is not configured."
        )
    provided_key = x_admin_key
    if not provided_key and authorization:
        if authorization.startswith("Bearer "):
            provided_key = authorization[7:].strip()
        else:
            provided_key = authorization.strip()

    if not provided_key or provided_key.strip() != admin_key.strip():
        raise HTTPException(status_code=403, detail="Invalid admin API key.")
    return True

@app.get("/admin/access-requests", summary="List all access requests (Admin Only)")
def admin_get_access_requests(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    verify_admin_key(x_admin_key=x_admin_key, authorization=authorization)
    return get_all_access_requests(db_path=DB_PATH)

@app.post("/admin/access-requests/{request_id}/approve", summary="Approve an access request (Admin Only)")
def admin_approve_access_request(
    request_id: int,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    verify_admin_key(x_admin_key=x_admin_key, authorization=authorization)
    ok, msg = approve_access_request(request_id, db_path=DB_PATH)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "message": msg}

@app.post("/admin/questions/generate", summary="Generate new questions from canonical chunks (Admin Only)")
def admin_generate_questions(
    req: GenerateQuestionRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    verify_admin_key(x_admin_key=x_admin_key, authorization=authorization)
    server_key = req.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    results = []
    errors = []
    for _ in range(max(1, min(req.count, 10))):
        try:
            q = generate_question(
                clinical_domain=req.clinical_domain,
                topic=req.topic,
                api_key=server_key,
                db_path=DB_PATH
            )
            results.append(q)
        except Exception as e:
            errors.append(str(e))
            break

    if not results and errors:
        raise HTTPException(status_code=500, detail=errors[0])

    return {
        "success": True,
        "generated_count": len(results),
        "questions": results,
        "errors": errors if errors else None
    }

@app.get("/admin/questions/pending", summary="List pending questions awaiting review (Admin Only)")
def admin_get_pending_questions(
    limit: int = Query(50, gt=0, le=200),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    verify_admin_key(x_admin_key=x_admin_key, authorization=authorization)
    return get_pending_questions(limit=limit, db_path=DB_PATH)

@app.post("/admin/questions/{question_id}/approve", summary="Approve a generated question (Admin Only)")
def admin_approve_question(
    question_id: int,
    reviewed_by: Optional[str] = Query("admin"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    verify_admin_key(x_admin_key=x_admin_key, authorization=authorization)
    ok = approve_question(question_id, reviewed_by=reviewed_by or "admin", db_path=DB_PATH)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Question #{question_id} not found or update failed.")
    return {"success": True, "message": f"Question #{question_id} approved successfully."}

@app.post("/admin/questions/{question_id}/reject", summary="Reject a generated question (Admin Only)")
def admin_reject_question(
    question_id: int,
    reviewed_by: Optional[str] = Query("admin"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None)
):
    verify_admin_key(x_admin_key=x_admin_key, authorization=authorization)
    ok = reject_question(question_id, reviewed_by=reviewed_by or "admin", db_path=DB_PATH)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Question #{question_id} not found or update failed.")
    return {"success": True, "message": f"Question #{question_id} rejected successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
