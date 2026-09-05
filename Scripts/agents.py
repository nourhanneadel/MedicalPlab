import os
import json
import requests
from typing import Dict, Any, List, Optional
from Scripts.rag_engine import rag_engine

class MedicalAgents:
    """
    Multi-Agent System for MedPlab:
    1. SocraticTutorAgent: Conducts Socratic dialogue & generates Differential Diagnosis Matrix with NICE RAG.
    2. VirtualPatientAgent: Realistic roleplay of clinical patients in OSCE stations.
    3. ExaminerAgent: Evaluates clinical performance based on GMC UK assessment standards.
    """

    @staticmethod
    def call_llm(system_prompt: str, user_prompt: str, api_key: Optional[str] = None, provider: str = "gemini") -> Optional[str]:
        # Priority: passed api_key -> environment variable
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            return None

        # 1. Google Gemini via direct REST API
        if provider == "gemini" or key.startswith("AIza"):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": 0.2}
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    print(f"Gemini API returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"Gemini REST call failed: {e}")

        # 2. OpenAI via direct REST API
        elif provider == "openai" or key.startswith("sk-"):
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"OpenAI REST call failed: {e}")

        return None

    # -------------------------------------------------------------
    # AGENT 1: Socratic Medical Tutor
    # -------------------------------------------------------------
    @classmethod
    def socratic_tutor_analysis(cls, question_data: Dict[str, Any], user_choice: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        question = question_data.get("question", "")
        choices = question_data.get("choices", [])
        correct_answer = question_data.get("answer", "")
        base_explanation = question_data.get("explanation", "")

        # RAG Retrieval from NICE Guidelines
        rag_matches = rag_engine.search(question + " " + correct_answer, top_k=2)
        citation_text = ""
        rag_excerpt = ""
        if rag_matches:
            citation_text = rag_matches[0]["citation"]
            rag_excerpt = rag_matches[0]["content"]

        is_correct = (user_choice.strip().lower() == correct_answer.strip().lower())

        system_prompt = (
            "You are an expert UK Senior Clinical Consultant and PLAB Medical Tutor. "
            "Guide medical candidates using the Socratic method, highlighting clinical reasoning, "
            "differential diagnosis, and ruling out incorrect options according to current UK NICE Guidelines."
        )
        user_prompt = f"""
Clinical Question: {question}
Options: {choices}
Correct Answer: {correct_answer}
Candidate's Selected Option: {user_choice}
Is Candidate Correct: {is_correct}
NICE Guideline Excerpt: {rag_excerpt}

Provide your analysis in clean JSON format with these exact keys:
{{
  "socratic_verdict": "An encouraging Socratic assessment explaining whether they are right or wrong and the clinical rationale",
  "differentiating_matrix": [
    {{"option": "option text", "verdict": "CORRECT or RULED OUT", "clinical_reason": "Specific clinical reason why this option applies or is discarded"}}
  ],
  "clinical_pearl": "A high-yield takeaway rule for the PLAB exam",
  "nice_recommendation": "Summary of what the relevant NICE guideline mandates"
}}
"""
        llm_response = cls.call_llm(system_prompt, user_prompt, api_key)
        if llm_response:
            try:
                clean_json = llm_response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                parsed = json.loads(clean_json.strip())
                parsed["rag_citation"] = citation_text
                return parsed
            except Exception:
                pass

        # Intelligent Fallback
        matrix = []
        for c in choices:
            c_str = str(c).strip()
            if not c_str:
                continue
            if c_str.lower() == correct_answer.strip().lower():
                matrix.append({
                    "option": c_str,
                    "verdict": "CORRECT (Gold Standard)",
                    "clinical_reason": f"First-line intervention according to NICE guidelines. {base_explanation[:140]}..."
                })
            else:
                matrix.append({
                    "option": c_str,
                    "verdict": "RULED OUT (Distractor)",
                    "clinical_reason": "Contraindicated, inadequate for acute stabilization, or secondary to the definitive gold-standard therapy in this clinical setting."
                })

        if is_correct:
            verdict = f"Excellent clinical judgment! You correctly selected **{correct_answer}**. This aligns with best practice."
        else:
            verdict = f"Let's review this together. You selected **{user_choice}**, but the gold-standard recommendation is **{correct_answer}**. Notice the acute markers and symptom duration in the vignette."

        return {
            "socratic_verdict": verdict,
            "differentiating_matrix": matrix,
            "clinical_pearl": "In PLAB exams, always prioritize hemodynamic stabilization and time-critical interventions (e.g. PPCI within 120 mins) over elective workups.",
            "nice_recommendation": rag_excerpt[:250] + "..." if rag_excerpt else "Follow established NICE clinical pathways for primary management.",
            "rag_citation": citation_text or "NICE Clinical Guidelines Reference"
        }

    # -------------------------------------------------------------
    # AGENT 2: Virtual Patient (OSCE Simulation)
    # -------------------------------------------------------------
    @classmethod
    def virtual_patient_reply(cls, station: Dict[str, Any], chat_history: List[Dict[str, str]], user_message: str, api_key: Optional[str] = None) -> str:
        patient_info = station.get("patient_brief", {})
        patient_name = station.get("patient_name", "Patient")
        vitals = station.get("vital_signs", "")

        system_prompt = f"""
You are roleplaying as {patient_name}, a real patient in a UK PLAB 2 (OSCE) clinical exam.
Your personality: {patient_info.get('personality')}
Your chief complaint: {patient_info.get('chief_complaint')}
History of Present Illness: {patient_info.get('history_of_present_illness')}
Associated symptoms: {patient_info.get('associated_symptoms')}
Past Medical History: {patient_info.get('past_medical_history')}
Medications: {patient_info.get('medications')}
Social History: {patient_info.get('social_history')}
Family History: {patient_info.get('family_history')}
Your vital signs: {vitals}
Key fear/concern: {patient_info.get('key_concerns')}

RULES FOR ROLEPLAYING:
1. Speak in first person ('I', 'me') as a patient in the UK.
2. DO NOT reveal all your history in one go! Answer only what the doctor explicitly asks.
3. If the doctor shows empathy, express relief. If they use too much medical jargon, ask what it means.
4. Keep answers conversational, realistic, and concise (1-3 sentences).
"""
        history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history[-6:]])
        user_prompt = f"{history_text}\nDoctor: {user_message}\nPatient:"

        llm_response = cls.call_llm(system_prompt, user_prompt, api_key)
        if llm_response:
            return llm_response.strip()

        # Intelligent Fallback based on keywords
        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ["hello", "hi", "good morning", "good afternoon", "introduce"]):
            return f"Hello, Doctor. Thank you for seeing me... I'm really feeling quite awful with this {patient_info.get('chief_complaint', 'problem')}."
        elif any(w in msg_lower for w in ["when", "start", "long", "onset", "began"]):
            return f"It started {patient_info.get('history_of_present_illness', 'a few hours ago')}."
        elif any(w in msg_lower for w in ["pain", "feel like", "describe", "character"]):
            return f"It feels like {patient_info.get('chief_complaint', 'a heavy ache')}. {patient_info.get('history_of_present_illness', '')[:120]}."
        elif any(w in msg_lower for w in ["spread", "radiat", "arm", "neck", "jaw", "back"]):
            return f"Yes, {patient_info.get('history_of_present_illness', 'it seems to spread slightly')}."
        elif any(w in msg_lower for w in ["smoke", "cigarette", "pack", "alcohol", "drink"]):
            return f"{patient_info.get('social_history', 'I do smoke occasionally.')}"
        elif any(w in msg_lower for w in ["medication", "tablets", "pills", "drugs"]):
            return f"I take {patient_info.get('medications', 'some routine medication')}."
        elif any(w in msg_lower for w in ["family", "father", "mother", "brother", "sister"]):
            return f"{patient_info.get('family_history', 'My family has some health issues.')}"
        elif any(w in msg_lower for w in ["worry", "afraid", "scared", "fear", "anxious", "concern"]):
            return f"{patient_info.get('key_concerns', 'Doctor, I just want to know if I am going to be okay.')}"
        else:
            return f"{patient_info.get('associated_symptoms', 'I just feel exhausted and really worried about what is happening.')}"

    # -------------------------------------------------------------
    # AGENT 3: Clinical Examiner (OSCE Evaluation)
    # -------------------------------------------------------------
    @classmethod
    def evaluate_osce_consultation(cls, station: Dict[str, Any], chat_history: List[Dict[str, str]], api_key: Optional[str] = None) -> Dict[str, Any]:
        marking_scheme = station.get("marking_scheme", {})
        patient_name = station.get("patient_name", "Patient")
        
        conversation_transcript = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history])

        system_prompt = (
            "You are a GMC UK Senior Examiner for the PLAB 2 Clinical Examination. "
            "Evaluate the candidate's consultation with the patient according to GMC standards."
        )
        user_prompt = f"""
Station Title: {station.get('title')}
Patient: {patient_name}
Candidate Consultation Transcript:
{conversation_transcript}

Marking Scheme Criteria:
{json.dumps(marking_scheme, indent=2)}

Provide a strict, professional evaluation in JSON with these exact keys:
{{
  "history_score": 4,  // out of 5
  "clinical_judgment_score": 4, // out of 5
  "communication_empathy_score": 4, // out of 5
  "total_score": 12, // out of 15
  "candidate_verdict": "PASS (Good Clinical Practice) or BORDERLINE or FAIL",
  "key_strengths": ["list of what the candidate did well"],
  "areas_for_improvement": ["list of what was missed or can be improved"],
  "critical_safety_comment": "Assessment of patient safety"
}}
"""
        llm_response = cls.call_llm(system_prompt, user_prompt, api_key)
        if llm_response:
            try:
                clean_json = llm_response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                return json.loads(clean_json.strip())
            except Exception:
                pass

        # Intelligent Heuristic Fallback
        num_exchanges = len([m for m in chat_history if m["role"] == "user"])
        history_score = min(5, max(2, int(num_exchanges * 0.7)))
        comm_score = 4 if any("empath" in m["content"].lower() or "sorry" in m["content"].lower() or "worry" in m["content"].lower() for m in chat_history if m["role"] == "user") else 3
        clin_score = min(5, max(2, int(num_exchanges * 0.6)))
        total = history_score + comm_score + clin_score
        verdict = "PASS" if total >= 10 else "BORDERLINE"

        return {
            "history_score": history_score,
            "clinical_judgment_score": clin_score,
            "communication_empathy_score": comm_score,
            "total_score": total,
            "candidate_verdict": f"{verdict} ({total}/15)",
            "key_strengths": [
                "Maintained polite and structured professional demeanor",
                "Explored primary symptoms and patient's concerns actively",
                "Kept communication clear and respectful"
            ],
            "areas_for_improvement": [
                "Screen more deeply for secondary red flags (e.g. syncope, constitutional signs)",
                "Explicitly address patient concerns early in the consultation",
                "Structure SOCRATES symptom history more systematically"
            ],
            "critical_safety_comment": "Patient was safely managed without immediate hazard; appropriate investigative pathway triggered."
        }
