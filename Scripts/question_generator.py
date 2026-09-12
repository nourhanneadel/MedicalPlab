import os
import json
import sqlite3
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("medplab.question_generator")
logging.basicConfig(level=logging.INFO)

DB_PATH_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data", "db", "merged.db")
CHUNKS_PATH_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data", "canonical_chunks.json")

VALID_DOMAINS = [
    "acute_physical_medicine",
    "mental_health",
    "ethics_professionalism"
]


def init_generated_questions_table(db_path: str = DB_PATH_DEFAULT):
    """Initializes the generated_questions table and relevant indexes."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        choice_a TEXT NOT NULL,
        choice_b TEXT NOT NULL,
        choice_c TEXT NOT NULL,
        choice_d TEXT NOT NULL,
        choice_e TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        explanation TEXT NOT NULL,
        topic TEXT NOT NULL,
        clinical_domain TEXT NOT NULL,
        source_chunk_id TEXT,
        source_citation TEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        review_status TEXT DEFAULT 'pending_review',
        reviewed_by TEXT,
        reviewed_at TIMESTAMP
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gen_q_status ON generated_questions(review_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gen_q_domain ON generated_questions(clinical_domain);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gen_q_topic ON generated_questions(topic);")
    conn.commit()
    conn.close()


def migrate_existing_questions(db_path: str = DB_PATH_DEFAULT) -> int:
    """
    Migrates the 10 plabable_all and 5 uni questions into generated_questions
    with review_status = 'approved', source_chunk_id = NULL, source_citation = NULL.
    Idempotent: skips questions that have already been migrated.
    """
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrated_count = 0

    # 1. Migrate plabable_all
    try:
        cursor.execute("SELECT id, question, choice_a, choice_b, choice_c, choice_d, choice_e, answer, explanation, topic FROM plabable_all")
        plab_rows = cursor.fetchall()
        for r in plab_rows:
            q_text = r[1].strip()
            # Check if already in generated_questions
            cursor.execute("SELECT id FROM generated_questions WHERE question_text = ?", (q_text,))
            if cursor.fetchone():
                continue

            cursor.execute("""
            INSERT INTO generated_questions (
                question_text, choice_a, choice_b, choice_c, choice_d, choice_e,
                correct_answer, explanation, topic, clinical_domain,
                source_chunk_id, source_citation, review_status, reviewed_by, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'approved', 'migration', CURRENT_TIMESTAMP)
            """, (
                q_text,
                r[2] or "",
                r[3] or "",
                r[4] or "",
                r[5] or "",
                r[6] or "",
                r[7] or "",
                r[8] or "",
                (r[9] or "GENERAL").strip().upper(),
                "acute_physical_medicine"
            ))
            migrated_count += 1
    except sqlite3.OperationalError as e:
        logger.warning(f"plabable_all table not found or error during migration: {e}")

    # 2. Migrate uni
    try:
        cursor.execute("""
        SELECT
            id,
            question,
            choice_a,
            choice_b,
            choice_c,
            choice_d,
            CASE answer
                WHEN 'A' THEN choice_a
                WHEN 'B' THEN choice_b
                WHEN 'C' THEN choice_c
                WHEN 'D' THEN choice_d
                ELSE answer
            END AS resolved_answer,
            topic,
            level
        FROM uni
        """)
        uni_rows = cursor.fetchall()
        default_uni_explanations = {
            1: "Mitochondria generate the vast majority of cellular ATP via the electron transport chain and oxidative phosphorylation in the inner mitochondrial membrane.",
            2: "The Vagus nerve (Cranial Nerve X) provides extensive parasympathetic autonomic innervation to the thoracic and abdominal viscera up to the splenic flexure.",
            3: "Beta-lactam antibiotics inhibit bacterial cell wall synthesis by covalently binding to penicillin-binding proteins (transpeptidases), preventing peptidoglycan cross-linking.",
            4: "Phase 0 rapid depolarization of the cardiac ventricular action potential is driven by sudden activation and influx of sodium through fast voltage-gated Na+ channels.",
            5: "Chronic kidney disease impairs phosphate excretion (leading to hyperphosphatemia) and decreases calcitriol synthesis, driving secondary hyperparathyroidism."
        }
        for r in uni_rows:
            q_id = r[0]
            q_text = r[1].strip()
            cursor.execute("SELECT id FROM generated_questions WHERE question_text = ?", (q_text,))
            if cursor.fetchone():
                continue

            expl = default_uni_explanations.get(q_id, "Verified medical sciences principle.")
            cursor.execute("""
            INSERT INTO generated_questions (
                question_text, choice_a, choice_b, choice_c, choice_d, choice_e,
                correct_answer, explanation, topic, clinical_domain,
                source_chunk_id, source_citation, review_status, reviewed_by, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'approved', 'migration', CURRENT_TIMESTAMP)
            """, (
                q_text,
                r[2] or "",
                r[3] or "",
                r[4] or "",
                r[5] or "",
                "",
                r[6] or "",
                expl,
                (r[7] or "Basic Science").strip(),
                "acute_physical_medicine"
            ))
            migrated_count += 1
    except sqlite3.OperationalError as e:
        logger.warning(f"uni table not found or error during migration: {e}")

    conn.commit()
    conn.close()
    if migrated_count > 0:
        logger.info(f"Successfully migrated {migrated_count} legacy questions into generated_questions.")
    return migrated_count


def _load_canonical_chunks(chunks_path: str = CHUNKS_PATH_DEFAULT) -> List[Dict[str, Any]]:
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"Canonical chunks file not found at {chunks_path}")
    with open(chunks_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_question(
    clinical_domain: str,
    topic: Optional[str] = None,
    api_key: Optional[str] = None,
    db_path: str = DB_PATH_DEFAULT,
    chunks_path: str = CHUNKS_PATH_DEFAULT
) -> Dict[str, Any]:
    """
    Generates a single PLAB 1 Single Best Answer (SBA) question grounded strictly
    in a selected canonical guideline chunk.

    Guarantees:
    - Questions are inserted with review_status = 'pending_review'.
    - If LLM call fails or no API key exists, raises RuntimeError (no heuristic fabrication).
    """
    from Scripts.agents import MedicalAgents

    if clinical_domain not in VALID_DOMAINS:
        raise ValueError(f"Invalid clinical_domain '{clinical_domain}'. Must be one of {VALID_DOMAINS}")

    chunks = _load_canonical_chunks(chunks_path)

    # Filter candidate chunks by clinical_domain
    domain_chunks = [
        c for c in chunks
        if c.get("clinical_domain") == clinical_domain and len(c.get("text", "")) > 100
    ]
    if not domain_chunks:
        domain_chunks = [c for c in chunks if len(c.get("text", "")) > 100]

    # Optional topic / section keyword filtering
    matching_chunks = domain_chunks
    if topic and topic.strip():
        t_term = topic.strip().lower()
        topic_matched = [
            c for c in domain_chunks
            if t_term in c.get("text", "").lower()
            or t_term in c.get("section", "").lower()
            or t_term in c.get("heading", "").lower()
            or t_term in c.get("title", "").lower()
        ]
        if topic_matched:
            matching_chunks = topic_matched

    chosen_chunk = random.choice(matching_chunks)
    chunk_id = chosen_chunk.get("chunk_id", "unknown_chunk")
    citation = chosen_chunk.get("citation") or chosen_chunk.get("title", "UK Clinical Guidelines")
    source_body = chosen_chunk.get("source_body", "NICE")
    chunk_text = chosen_chunk.get("text", "").strip()

    # Check for API key availability
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        err_msg = (
            "Question generation failed: No valid GEMINI_API_KEY or OPENAI_API_KEY provided. "
            "Ungrounded heuristic question generation is strictly prohibited for clinical exam content."
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    system_prompt = (
        "You are an expert UK Senior Clinical Medical Examiner and Medical Education Specialist "
        "writing official Single Best Answer (SBA) questions for the UK PLAB 1 / UKMLA licensing examination.\n\n"
        "STRICT GROUNDING RULE:\n"
        "You MUST generate a realistic clinical scenario and question strictly and exclusively grounded in the "
        "provided UK guideline/standard excerpt. The correct answer MUST directly reflect what the excerpt recommends. "
        "Create 5 options (A through E). Exactly one option must be the single best answer. The remaining 4 options "
        "must be plausible clinical distractors relevant to the scenario, but ruled out according to the excerpt or UK clinical standards.\n"
        "Do NOT contradict, extrapolate, or invent recommendations not supported by the provided text.\n\n"
        "Output your response strictly as valid JSON with NO markdown fences, matching this exact schema:\n"
        "{\n"
        '  "question_text": "Detailed clinical vignette ending with a precise question (e.g. \'What is the most appropriate next step in management?\')",\n'
        '  "choice_a": "Option A text",\n'
        '  "choice_b": "Option B text",\n'
        '  "choice_c": "Option C text",\n'
        '  "choice_d": "Option D text",\n'
        '  "choice_e": "Option E text",\n'
        '  "correct_answer": "Exact text of the correct choice (must be identical to one of choice_a..choice_e)",\n'
        '  "explanation": "Clear clinical explanation explaining why the correct choice is mandated and why other options are ruled out",\n'
        '  "topic": "Concise medical specialty or topic name in uppercase (e.g. DEPRESSION, CARDIOLOGY, MEDICAL_ETHICS)"\n'
        "}"
    )

    user_prompt = (
        f"CLINICAL DOMAIN: {clinical_domain}\n"
        f"AUTHORITY BODY: {source_body}\n"
        f"OFFICIAL CITATION: {citation}\n\n"
        f"REFERENCE GUIDELINE EXCERPT:\n\"\"\"\n{chunk_text}\n\"\"\"\n\n"
        f"Draft a high-yield PLAB 1 SBA question grounded strictly in this reference material."
    )

    raw_response = MedicalAgents.call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        api_key=key
    )

    if not raw_response or not raw_response.strip():
        err_msg = (
            f"Question generation failed: LLM call returned empty response for chunk '{chunk_id}'. "
            "No ungrounded question was created."
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    # Clean JSON
    cleaned = raw_response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        q_data = json.loads(cleaned)
    except Exception as e:
        err_msg = f"Failed to parse LLM question JSON: {e}\nRaw content: {raw_response[:300]}"
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    # Validate schema
    req_fields = ["question_text", "choice_a", "choice_b", "choice_c", "choice_d", "choice_e", "correct_answer", "explanation"]
    for field in req_fields:
        if not q_data.get(field):
            raise RuntimeError(f"Generated question is missing required field '{field}'.")

    choices = [q_data["choice_a"], q_data["choice_b"], q_data["choice_c"], q_data["choice_d"], q_data["choice_e"]]
    correct_ans = q_data["correct_answer"].strip()

    # Ensure correct answer matches one of the choices
    if correct_ans not in choices:
        letter_map = {"A": q_data["choice_a"], "B": q_data["choice_b"], "C": q_data["choice_c"], "D": q_data["choice_d"], "E": q_data["choice_e"]}
        if correct_ans.upper() in letter_map:
            correct_ans = letter_map[correct_ans.upper()]
            q_data["correct_answer"] = correct_ans
        else:
            raise RuntimeError(f"Generated question correct_answer '{correct_ans}' does not match any of the 5 choices.")

    resolved_topic = (q_data.get("topic") or topic or clinical_domain).strip().upper()

    # Store in database as pending_review
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO generated_questions (
        question_text, choice_a, choice_b, choice_c, choice_d, choice_e,
        correct_answer, explanation, topic, clinical_domain,
        source_chunk_id, source_citation, review_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review')
    """, (
        q_data["question_text"].strip(),
        q_data["choice_a"].strip(),
        q_data["choice_b"].strip(),
        q_data["choice_c"].strip(),
        q_data["choice_d"].strip(),
        q_data["choice_e"].strip(),
        correct_ans,
        q_data["explanation"].strip(),
        resolved_topic,
        clinical_domain,
        chunk_id,
        citation
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Generated question #{new_id} [{resolved_topic} | {clinical_domain}] from chunk '{chunk_id}' (status: pending_review).")

    return {
        "id": new_id,
        "question_text": q_data["question_text"].strip(),
        "choice_a": q_data["choice_a"].strip(),
        "choice_b": q_data["choice_b"].strip(),
        "choice_c": q_data["choice_c"].strip(),
        "choice_d": q_data["choice_d"].strip(),
        "choice_e": q_data["choice_e"].strip(),
        "correct_answer": correct_ans,
        "explanation": q_data["explanation"].strip(),
        "topic": resolved_topic,
        "clinical_domain": clinical_domain,
        "source_chunk_id": chunk_id,
        "source_citation": citation,
        "review_status": "pending_review"
    }


def approve_question(question_id: int, reviewed_by: str = "admin", db_path: str = DB_PATH_DEFAULT) -> bool:
    """Approves a pending question, making it eligible to be served to candidates."""
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE generated_questions
    SET review_status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (reviewed_by, question_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def reject_question(question_id: int, reviewed_by: str = "admin", db_path: str = DB_PATH_DEFAULT) -> bool:
    """Rejects a pending question."""
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE generated_questions
    SET review_status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (reviewed_by, question_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_pending_questions(limit: int = 50, db_path: str = DB_PATH_DEFAULT) -> List[Dict[str, Any]]:
    """Retrieves all questions currently awaiting manual human review."""
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, question_text, choice_a, choice_b, choice_c, choice_d, choice_e,
           correct_answer, explanation, topic, clinical_domain,
           source_chunk_id, source_citation, generated_at, review_status
    FROM generated_questions
    WHERE review_status = 'pending_review'
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_approved_questions(
    clinical_domain: Optional[str] = None,
    topic: Optional[str] = None,
    exclude_ids: Optional[List[int]] = None,
    limit: int = 5,
    db_path: str = DB_PATH_DEFAULT
) -> List[Dict[str, Any]]:
    """
    Retrieves random approved questions from generated_questions.
    Only questions with review_status = 'approved' are ever returned.
    Applies topic / domain filtering and unseen exclusion, with practice fallback.
    """
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT id FROM generated_questions WHERE review_status = 'approved'"
    conditions = []
    params = []

    if clinical_domain and clinical_domain.strip() and clinical_domain.lower() != "all domains":
        conditions.append("clinical_domain = ?")
        params.append(clinical_domain.strip())

    if topic and topic.strip() and topic.lower() != "all topics":
        conditions.append("LOWER(topic) = LOWER(?)")
        params.append(topic.strip())

    if exclude_ids:
        placeholders = ", ".join("?" for _ in exclude_ids)
        conditions.append(f"id NOT IN ({placeholders})")
        params.extend(exclude_ids)

    if conditions:
        query += " AND " + " AND ".join(conditions)

    cursor.execute(query, params)
    all_ids = [row["id"] for row in cursor.fetchall()]

    # Practice Fallback: if user has seen all matching approved questions,
    # fallback to all approved questions matching topic/domain so they can continue reviewing
    if not all_ids and exclude_ids:
        fallback_query = "SELECT id FROM generated_questions WHERE review_status = 'approved'"
        fallback_conditions = []
        fallback_params = []
        if clinical_domain and clinical_domain.strip() and clinical_domain.lower() != "all domains":
            fallback_conditions.append("clinical_domain = ?")
            fallback_params.append(clinical_domain.strip())
        if topic and topic.strip() and topic.lower() != "all topics":
            fallback_conditions.append("LOWER(topic) = LOWER(?)")
            fallback_params.append(topic.strip())
        if fallback_conditions:
            fallback_query += " AND " + " AND ".join(fallback_conditions)
        cursor.execute(fallback_query, fallback_params)
        all_ids = [row["id"] for row in cursor.fetchall()]

    if not all_ids:
        conn.close()
        return []

    sample_size = min(limit, len(all_ids))
    random_ids = random.sample(all_ids, sample_size)

    id_placeholders = ", ".join("?" for _ in random_ids)
    cursor.execute(f"""
    SELECT id, question_text, choice_a, choice_b, choice_c, choice_d, choice_e,
           correct_answer, explanation, topic, clinical_domain,
           source_chunk_id, source_citation
    FROM generated_questions
    WHERE id IN ({id_placeholders})
    """, random_ids)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        choices = [r["choice_a"], r["choice_b"], r["choice_c"], r["choice_d"]]
        if r["choice_e"]:
            choices.append(r["choice_e"])
        result.append({
            "id": r["id"],
            "question": r["question_text"],
            "question_text": r["question_text"],
            "choices": choices,
            "answer": r["correct_answer"],
            "correct_answer": r["correct_answer"],
            "explanation": r["explanation"],
            "topic": r["topic"],
            "clinical_domain": r["clinical_domain"],
            "source_chunk_id": r["source_chunk_id"],
            "source_citation": r["source_citation"]
        })
    return result


def get_approved_topics(db_path: str = DB_PATH_DEFAULT) -> Dict[str, Any]:
    """
    Returns distinct topics that currently have at least one APPROVED question,
    both overall and grouped by clinical_domain.
    """
    init_generated_questions_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DISTINCT topic, clinical_domain
    FROM generated_questions
    WHERE review_status = 'approved' AND topic IS NOT NULL AND topic != ''
    ORDER BY clinical_domain, topic
    """)
    rows = cursor.fetchall()
    conn.close()

    all_topics = sorted(list(set(r[0] for r in rows)))
    by_domain: Dict[str, List[str]] = {
        "acute_physical_medicine": [],
        "mental_health": [],
        "ethics_professionalism": []
    }
    for topic, domain in rows:
        if domain in by_domain and topic not in by_domain[domain]:
            by_domain[domain].append(topic)

    return {
        "topics": all_topics,
        "by_domain": by_domain
    }
