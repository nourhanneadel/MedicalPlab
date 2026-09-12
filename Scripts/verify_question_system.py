import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import sqlite3
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app, DB_PATH
from Scripts.agents import MedicalAgents
from Scripts.question_generator import generate_question

ADMIN_KEY = os.getenv("ADMIN_API_KEY", "medplab_admin_secret_98765")
os.environ["ADMIN_API_KEY"] = ADMIN_KEY

client = TestClient(app)

def mock_call_llm(system_prompt: str, user_prompt: str, api_key: str = None, provider: str = "gemini"):
    # Return realistic grounded PLAB 1 question JSON based on NICE guideline chunks
    return json.dumps({
        "question_text": "A 42-year-old woman presents to her GP reporting persistent low mood, lack of energy, and loss of interest in her usual activities for the past 2 months. She has no psychotic symptoms and no active suicidal ideation. According to current NICE guidelines (NG222), which of the following is the most appropriate first-line treatment option for less severe to moderate depression?",
        "choice_a": "Evidence-based psychological intervention (e.g. Cognitive Behavioural Therapy) or an SSRI antidepressant",
        "choice_b": "Immediate initiation of lithium augmentation therapy",
        "choice_c": "Electroconvulsive therapy (ECT)",
        "choice_d": "Oral haloperidol monotherapy",
        "choice_e": "High-dose tricyclic antidepressant (e.g. amitriptyline 150mg) as first line",
        "correct_answer": "Evidence-based psychological intervention (e.g. Cognitive Behavioural Therapy) or an SSRI antidepressant",
        "explanation": "NICE Guideline NG222 recommends discussing treatment options and offering either evidence-based psychological treatment (such as CBT) or an SSRI antidepressant as initial treatment for depression in adults.",
        "topic": "Depression"
    })

def run_all_checks():
    print("=================================================================")
    print("  RUNNING 6 MANDATORY VERIFICATION CHECKS (MEDPLAB QUESTION GEN) ")
    print("=================================================================")

    admin_headers = {"X-Admin-Key": ADMIN_KEY}

    # Setup Candidate User
    cand_email = "candidate_test@nhs.net"
    cand_pass = "PlabPass2026!"
    signup_res = client.post("/auth/signup", json={"email": cand_email, "password": cand_pass})
    if signup_res.status_code == 200:
        token = signup_res.json()["token"]
    else:
        login_res = client.post("/auth/login", json={"email": cand_email, "password": cand_pass})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["token"]

    user_headers = {"Authorization": f"Bearer {token}"}
    print("[INIT] Candidate test user authenticated with token.")

    # -------------------------------------------------------------
    # CHECK 4: Confirm the 15 pre-existing migrated questions still work
    # -------------------------------------------------------------
    print("\n[CHECK 4] Verifying 15 pre-existing migrated questions...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM generated_questions WHERE reviewed_by = 'migration' AND review_status = 'approved'")
    migrated_count = c.fetchone()[0]
    conn.close()
    print(f" -> Found {migrated_count} migrated approved questions in generated_questions table.")
    assert migrated_count == 15, f"Expected 15 migrated questions, got {migrated_count}"

    # Test candidate retrieval via /plabable and /uni
    resp_plab = client.get("/plabable?n=5", headers=user_headers)
    assert resp_plab.status_code == 200, f"/plabable failed: {resp_plab.text}"
    plab_qs = resp_plab.json()
    assert len(plab_qs) == 5, f"Expected 5 questions, got {len(plab_qs)}"
    assert all("question" in q and "choices" in q and "answer" in q for q in plab_qs)
    print(" -> Successfully retrieved 5 questions via GET /plabable.")

    resp_uni = client.get("/uni?n=3", headers=user_headers)
    assert resp_uni.status_code == 200, f"/uni failed: {resp_uni.text}"
    uni_qs = resp_uni.json()
    assert len(uni_qs) == 3, f"Expected 3 questions, got {len(uni_qs)}"
    print(" -> Successfully retrieved 3 questions via GET /uni.")
    print(">>> CHECK 4 PASSED: 15 legacy questions migrated and accessible to candidates.")

    # -------------------------------------------------------------
    # CHECK 5: GET /topics only lists topics with at least one approved question
    # -------------------------------------------------------------
    print("\n[CHECK 5] Verifying GET /topics only lists approved topics...")
    resp_topics = client.get("/topics")
    assert resp_topics.status_code == 200, f"/topics failed: {resp_topics.text}"
    topics_res = resp_topics.json()
    topics_list = topics_res.get("topics", [])
    print(f" -> GET /topics returned {len(topics_list)} topics: {topics_list}")
    assert len(topics_list) > 0

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT topic FROM generated_questions WHERE review_status = 'approved' AND topic IS NOT NULL AND topic != ''")
    db_approved_topics = {r[0] for r in c.fetchall()}
    conn.close()

    for t in topics_list:
        assert t in db_approved_topics, f"Topic '{t}' listed in /topics is NOT approved in database!"
    print(">>> CHECK 5 PASSED: GET /topics strictly returns topics with at least one approved question.")

    # -------------------------------------------------------------
    # CHECK 6: Confirm LLM-failure path returns a clear error (no ungrounded fallback)
    # -------------------------------------------------------------
    print("\n[CHECK 6] Verifying strict grounding and LLM-failure path...")
    # 1. Endpoint call with no API key
    gen_fail_resp = client.post(
        "/admin/questions/generate",
        json={"clinical_domain": "mental_health", "topic": "Depression", "count": 1},
        headers=admin_headers
    )
    print(f" -> Admin generate without key returned status {gen_fail_resp.status_code}")
    assert gen_fail_resp.status_code == 500, f"Expected 500, got {gen_fail_resp.status_code}: {gen_fail_resp.text}"
    assert "Question generation failed: No valid GEMINI_API_KEY or OPENAI_API_KEY provided" in gen_fail_resp.json()["detail"]
    print(f" -> Confirmed clear error message: '{gen_fail_resp.json()['detail']}'")

    # 2. Python direct function call with no API key
    try:
        generate_question(clinical_domain="mental_health", topic="Depression", api_key=None, db_path=DB_PATH)
        assert False, "Expected RuntimeError when API key is missing!"
    except RuntimeError as re:
        print(f" -> Confirmed direct call raises RuntimeError: {re}")
    print(">>> CHECK 6 PASSED: Strict grounding enforced; no ungrounded fabrication allowed.")

    # -------------------------------------------------------------
    # CHECK 1: Call POST /admin/questions/generate for clinical_domain="mental_health", count=3.
    # Verify 3 rows in generated_questions with status="pending_review".
    # -------------------------------------------------------------
    print("\n[CHECK 1] Calling POST /admin/questions/generate (domain='mental_health', count=3)...")
    with patch.object(MedicalAgents, "call_llm", side_effect=mock_call_llm):
        gen_resp = client.post(
            "/admin/questions/generate",
            json={
                "clinical_domain": "mental_health",
                "topic": "Depression",
                "count": 3,
                "api_key": "verified_test_key"
            },
            headers=admin_headers
        )
    assert gen_resp.status_code == 200, f"Generation failed: {gen_resp.text}"
    gen_data = gen_resp.json()
    assert gen_data.get("generated_count") == 3, f"Expected 3 generated questions, got {gen_data}"
    generated_questions = gen_data["questions"]
    gen_ids = [q["id"] for q in generated_questions]
    print(f" -> Generated 3 questions with IDs: {gen_ids}")

    # Verify rows in SQLite DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    placeholders = ",".join("?" for _ in gen_ids)
    c.execute(f"SELECT id, review_status, clinical_domain, topic, source_chunk_id FROM generated_questions WHERE id IN ({placeholders})", gen_ids)
    db_rows = c.fetchall()
    conn.close()

    assert len(db_rows) == 3, f"Expected 3 rows in DB, found {len(db_rows)}"
    for r in db_rows:
        q_id, status, domain, topic, chunk_id = r
        print(f" -> DB Row Q#{q_id}: status='{status}', domain='{domain}', topic='{topic}', chunk='{chunk_id}'")
        assert status == "pending_review", f"Question #{q_id} status is '{status}', expected 'pending_review'!"
        assert domain == "mental_health", f"Question #{q_id} domain is '{domain}', expected 'mental_health'!"
    print(">>> CHECK 1 PASSED: 3 questions generated and stored with review_status='pending_review'.")

    # -------------------------------------------------------------
    # CHECK 2: Confirm GET /plabable and candidate GET /questions do NOT return these 3 questions
    # -------------------------------------------------------------
    print("\n[CHECK 2] Confirming candidate endpoints do NOT return pending questions...")
    # Candidate request for mental_health domain
    cand_resp1 = client.get("/questions?clinical_domain=mental_health&n=10", headers=user_headers)
    assert cand_resp1.status_code == 200, f"/questions failed: {cand_resp1.text}"
    cand_qs1 = cand_resp1.json()
    cand_ids1 = [q["id"] for q in cand_qs1 if isinstance(q, dict) and "id" in q]
    for pid in gen_ids:
        assert pid not in cand_ids1, f"LEAK DETECTED: Pending question #{pid} returned to candidate via /questions!"

    # Candidate request for plabable
    cand_resp2 = client.get("/plabable?n=15", headers=user_headers)
    assert cand_resp2.status_code == 200, f"/plabable failed: {cand_resp2.text}"
    cand_qs2 = cand_resp2.json()
    cand_ids2 = [q["id"] for q in cand_qs2 if isinstance(q, dict) and "id" in q]
    for pid in gen_ids:
        assert pid not in cand_ids2, f"LEAK DETECTED: Pending question #{pid} returned to candidate via /plabable!"

    print(" -> Verified: None of the pending question IDs appear in candidate responses.")
    print(">>> CHECK 2 PASSED: Pending questions are strictly gated and invisible to candidates.")

    # -------------------------------------------------------------
    # CHECK 3: Approve 1 question via POST /admin/questions/{id}/approve.
    # Verify it now appears in GET /questions and counts toward quota.
    # -------------------------------------------------------------
    target_id = gen_ids[0]
    print(f"\n[CHECK 3] Approving question #{target_id} via POST /admin/questions/{target_id}/approve...")
    appr_resp = client.post(
        f"/admin/questions/{target_id}/approve?reviewed_by=LeadClinicalConsultant",
        headers=admin_headers
    )
    assert appr_resp.status_code == 200, f"Approval failed: {appr_resp.text}"

    # Verify status in database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT review_status, reviewed_by, reviewed_at FROM generated_questions WHERE id = ?", (target_id,))
    appr_row = c.fetchone()
    conn.close()
    assert appr_row[0] == "approved", f"Expected review_status='approved', got {appr_row[0]}"
    assert appr_row[1] == "LeadClinicalConsultant", f"Expected reviewed_by='LeadClinicalConsultant', got {appr_row[1]}"
    print(f" -> Database record updated: status='{appr_row[0]}', reviewer='{appr_row[1]}', at='{appr_row[2]}'")

    # Check candidate /auth/me before access
    me_before = client.get("/auth/me", headers=user_headers).json()
    accessed_before = me_before.get("distinct_questions_accessed", 0)

    # Now candidate requests mental_health questions
    fetch_appr_res = client.get("/questions?clinical_domain=mental_health&n=5", headers=user_headers)
    assert fetch_appr_res.status_code == 200, f"/questions failed: {fetch_appr_res.text}"
    fetched_data = fetch_appr_res.json()
    fetched_ids = [q["id"] for q in fetched_data if isinstance(q, dict) and "id" in q]
    print(f" -> Candidate received questions: {fetched_ids}")
    assert target_id in fetched_ids, f"Approved question #{target_id} was NOT served to candidate!"

    # Verify quota increment in /auth/me
    me_after = client.get("/auth/me", headers=user_headers).json()
    accessed_after = me_after.get("distinct_questions_accessed", 0)
    print(f" -> Distinct questions accessed: before={accessed_before}, after={accessed_after}")
    assert accessed_after > accessed_before, f"Quota was not incremented! before={accessed_before}, after={accessed_after}"
    print(f" -> Confirmed question #{target_id} successfully counted toward candidate quota.")

    # Also test rejection on second pending question
    rej_id = gen_ids[1]
    print(f" -> Testing rejection on Question #{rej_id}...")
    rej_resp = client.post(f"/admin/questions/{rej_id}/reject?reviewed_by=QualityAuditor", headers=admin_headers)
    assert rej_resp.status_code == 200, f"Reject failed: {rej_resp.text}"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT review_status, reviewed_by FROM generated_questions WHERE id = ?", (rej_id,))
    rej_row = c.fetchone()
    conn.close()
    assert rej_row[0] == "rejected"
    assert rej_row[1] == "QualityAuditor"
    print(f" -> Confirmed Question #{rej_id} updated to 'rejected' in database.")

    print(">>> CHECK 3 PASSED: Human review approval gate verified end-to-end.")

    print("\n=================================================================")
    print(" ALL 6 MANDATORY VERIFICATION CHECKS COMPLETED AND PASSED 100%!  ")
    print("=================================================================")

if __name__ == "__main__":
    run_all_checks()
