import os
import streamlit as st
import requests
import json

API_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="MedPlab-Agent | Dual-Brain Clinical Copilot",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .badge-card {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        background-color: #F3F4F6;
        border-left: 4px solid #2563EB;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR: AI Configuration & Knowledge Base Status
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-doctor.png", width=64)
    st.title("MedPlab-Agent")
    st.markdown("**Dual-Brain GenAI Clinical Copilot**")
    st.caption("Designed for UK PLAB 1 & PLAB 2 (OSCE) Excellence")
    st.divider()

    st.subheader("⚙️ GenAI Settings")
    llm_provider = st.selectbox("LLM Engine", ["Google Gemini (Recommended)", "OpenAI", "Offline Demo (Heuristic)"])
    api_key_input = st.text_input(
        "API Key (Optional)",
        type="password",
        help="Leave blank to use the intelligent built-in offline simulation mode."
    )
    api_key = api_key_input.strip() if api_key_input.strip() else None

    st.divider()
    st.subheader("📚 Grounded Knowledge Base")
    st.markdown("""
    - ✅ **NICE Guidelines RAG:**
      - NG185: Acute Coronary Syndromes
      - NG115/80: COPD & Acute Asthma
      - NG28: Type 2 Diabetes Management
      - NG136: Hypertension in Adults
      - NG128/51: Stroke & Sepsis Emergencies
    - ✅ **OSCE Virtual Stations:** 5 Active
    - ✅ **Zero-Hallucination Guardrails:** Enabled
    """)
    st.caption(f"Backend Server: `{API_URL}`")

# -------------------------------------------------------------
# MAIN APP HEADER
# -------------------------------------------------------------
st.markdown('<div class="main-title">🩺 MedPlab-Agent: Clinical Decision & OSCE Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">An Agentic GenAI platform combining <b>Socratic MCQ Differential Reasoning (PLAB 1)</b> and <b>Interactive Virtual Patient Consultations (PLAB 2 OSCE)</b>.</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "📝 PLAB 1: Smart Exam & Socratic Tutor",
    "🩺 PLAB 2: Virtual Clinic (OSCE Simulator)",
    "📖 NICE Guidelines RAG Explorer"
])

# -------------------------------------------------------------
# TAB 1: PLAB 1 SMART EXAM & SOCRATIC TUTOR
# -------------------------------------------------------------
with tab1:
    st.markdown("### 📝 PLAB 1 Socratic Clinical Tutor")
    st.caption("Test your clinical knowledge. If you make a mistake, the AI Tutor discusses your reasoning and builds a Differential Diagnosis Matrix.")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        source = st.selectbox("Question Pool", ["plabable", "uni"], key="p1_source")
    with col2:
        topic_filter = st.text_input("Filter by Topic (e.g. CARDIOLOGY, RESPIRATORY)", value="", key="p1_topic")
    with col3:
        n_q = st.number_input("Number of Questions", min_value=1, max_value=30, value=5, key="p1_n")

    if st.button("🔄 Fetch Clinical Questions", type="primary"):
        with st.spinner("Retrieving verified questions from database..."):
            try:
                params = {"n": n_q}
                if topic_filter.strip():
                    params["topic"] = topic_filter.strip()
                res = requests.get(f"{API_URL}/{source}", params=params)
                res.raise_for_status()
                st.session_state["plab_questions"] = res.json()
                st.session_state["tutor_analysis"] = {}
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

    questions = st.session_state.get("plab_questions", [])

    if questions:
        for idx, q in enumerate(questions, 1):
            with st.container():
                st.markdown(f"#### Question {idx}")
                st.info(q.get("question", ""))

                choices = [c for c in q.get("choices", []) if c]
                answer_key = f"q_answer_{idx}"
                user_selection = st.radio(
                    f"Select your clinical decision for Question {idx}:",
                    choices,
                    key=answer_key
                )

                if st.button(f"🔍 Submit & Analyze with Socratic Tutor (Q{idx})", key=f"btn_analyze_{idx}"):
                    with st.spinner("AI Tutor is conducting Socratic analysis & consulting NICE Guidelines..."):
                        try:
                            payload = {
                                "question": q.get("question", ""),
                                "choices": choices,
                                "answer": q.get("answer", ""),
                                "explanation": q.get("explanation", ""),
                                "user_choice": user_selection,
                                "api_key": api_key
                            }
                            resp = requests.post(f"{API_URL}/tutor/analyze", json=payload)
                            resp.raise_for_status()
                            analysis = resp.json()
                            st.session_state[f"analysis_{idx}"] = analysis
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

                # Display Tutor Analysis if available
                analysis_data = st.session_state.get(f"analysis_{idx}")
                if analysis_data:
                    st.divider()
                    st.markdown("##### 🧑‍🏫 Senior Consultant Feedback:")
                    st.markdown(f"> {analysis_data.get('socratic_verdict', '')}")

                    # Differential Diagnosis Matrix
                    st.markdown("##### 🔬 Differential Diagnosis Matrix (Why Options are Ruled Out):")
                    matrix = analysis_data.get("differentiating_matrix", [])
                    if matrix:
                        cols = st.columns([2, 1, 3])
                        cols[0].markdown("**Option**")
                        cols[1].markdown("**Verdict**")
                        cols[2].markdown("**Clinical Rationale**")
                        st.markdown("---")
                        for item in matrix:
                            c1, c2, c3 = st.columns([2, 1, 3])
                            c1.write(item.get("option", ""))
                            verdict = item.get("verdict", "")
                            if "CORRECT" in verdict:
                                c2.markdown(f"<span style='color:green;font-weight:bold;'>{verdict}</span>", unsafe_allow_html=True)
                            else:
                                c2.markdown(f"<span style='color:red;font-weight:bold;'>{verdict}</span>", unsafe_allow_html=True)
                            c3.write(item.get("clinical_reason", ""))

                    # NICE Grounding
                    st.markdown("##### 📜 NICE Guideline Evidence (Zero-Hallucination):")
                    st.success(f"**Reference:** `{analysis_data.get('rag_citation', 'NICE Clinical Knowledge')}`\n\n{analysis_data.get('nice_recommendation', '')}")

                    # Clinical Pearl
                    st.markdown("##### 💡 Clinical Exam Pearl:")
                    st.warning(analysis_data.get("clinical_pearl", ""))

                st.divider()
    else:
        st.info("Click 'Fetch Clinical Questions' above to start your practice session.")

# -------------------------------------------------------------
# TAB 2: PLAB 2 VIRTUAL CLINIC (OSCE SIMULATOR)
# -------------------------------------------------------------
with tab2:
    st.markdown("### 🩺 PLAB 2 Virtual Clinic (OSCE Simulator)")
    st.caption("Practice history taking and clinical communication with realistic AI patients. Receive GMC-standard marking from the Senior Examiner Agent.")

    # Fetch Stations
    try:
        stations_res = requests.get(f"{API_URL}/osce/stations")
        stations = stations_res.json() if stations_res.status_code == 200 else []
    except Exception:
        stations = []

    if not stations:
        st.warning("No OSCE stations found. Ensure the backend is running.")
    else:
        station_titles = {s["id"]: f"{s['title']} ({s['specialty']})" for s in stations}
        selected_id = st.selectbox(
            "Select an OSCE Station:",
            options=list(station_titles.keys()),
            format_func=lambda x: station_titles[x]
        )

        selected_station = next(s for s in stations if s["id"] == selected_id)

        # Reset chat if station changes
        if st.session_state.get("current_station_id") != selected_id:
            st.session_state["current_station_id"] = selected_id
            st.session_state["osce_chat"] = []
            st.session_state["osce_eval"] = None

        # Candidate Briefing Card
        with st.expander("📋 Candidate Briefing & Patient Information (Read Before Consultation)", expanded=True):
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                st.markdown(f"**Setting:** Acute Consultation Room")
                st.markdown(f"**Patient:** {selected_station['patient_name']}, {selected_station['patient_age']} years old ({selected_station['patient_gender']})")
                st.info(selected_station['candidate_brief'])
            with col_b2:
                st.markdown("**Vital Signs:**")
                st.code(selected_station['vital_signs'].replace(", ", "\n"))

        st.markdown("---")
        st.markdown("#### 🗣️ Live Consultation with the Patient")

        # Display Chat History
        chat_history = st.session_state.get("osce_chat", [])
        for msg in chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🧑‍🦱"):
                    st.markdown(f"**{selected_station['patient_name']}:** {msg['content']}")

        # Suggested Questions
        st.markdown("**Quick Clinical Prompts:**")
        q_cols = st.columns(4)
        quick_prompt = None
        if q_cols[0].button("👋 Introduce Yourself"):
            quick_prompt = f"Good day, {selected_station['patient_name']}. I am the doctor on duty today. How can I help you?"
        if q_cols[1].button("⏱️ Explore Onset & Timing"):
            quick_prompt = "Could you tell me when this problem started and what you were doing at the time?"
        if q_cols[2].button("📍 Radiation & Character"):
            quick_prompt = "Can you describe what the feeling is like, and does it spread anywhere else?"
        if q_cols[3].button("❤️ Address Anxiety & Concerns"):
            quick_prompt = "I can see you are uncomfortable. What is your main concern or fear about this today?"

        user_input = st.chat_input("Ask the patient a question or explore symptoms...")
        active_msg = user_input or quick_prompt

        if active_msg:
            # Append user message
            st.session_state["osce_chat"].append({"role": "user", "content": active_msg})
            with st.chat_message("user"):
                st.write(active_msg)

            # Get Patient Reply
            with st.spinner(f"{selected_station['patient_name']} is responding..."):
                try:
                    payload = {
                        "station_id": selected_id,
                        "chat_history": st.session_state["osce_chat"],
                        "message": active_msg,
                        "api_key": api_key
                    }
                    p_resp = requests.post(f"{API_URL}/osce/chat", json=payload)
                    p_resp.raise_for_status()
                    reply = p_resp.json().get("reply", "")
                    st.session_state["osce_chat"].append({"role": "assistant", "content": reply})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error chatting with patient: {e}")

        # End Consultation & Evaluation Button
        st.divider()
        col_end1, col_end2 = st.columns([2, 1])
        with col_end1:
            st.caption("When you have completed history taking, click to have the Senior GMC Examiner mark your station.")
        with col_end2:
            if st.button("🏁 Complete Station & Get Evaluation", type="primary"):
                if len(st.session_state["osce_chat"]) < 2:
                    st.warning("Please conduct at least a brief consultation with the patient before requesting evaluation.")
                else:
                    with st.spinner("Senior GMC Examiner is reviewing consultation transcript and scoring criteria..."):
                        try:
                            eval_payload = {
                                "station_id": selected_id,
                                "chat_history": st.session_state["osce_chat"],
                                "api_key": api_key
                            }
                            e_resp = requests.post(f"{API_URL}/osce/evaluate", json=eval_payload)
                            e_resp.raise_for_status()
                            st.session_state["osce_eval"] = e_resp.json()
                        except Exception as e:
                            st.error(f"Evaluation error: {e}")

        # Display Evaluation Report
        eval_result = st.session_state.get("osce_eval")
        if eval_result:
            st.markdown("### 🎓 Senior Examiner Marking & Feedback Report")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("History Taking", f"{eval_result.get('history_score', 0)} / 5")
            m2.metric("Clinical Judgment", f"{eval_result.get('clinical_judgment_score', 0)} / 5")
            m3.metric("Empathy & Communication", f"{eval_result.get('communication_empathy_score', 0)} / 5")
            m4.metric("Total Score", f"{eval_result.get('total_score', 0)} / 15", eval_result.get("candidate_verdict", ""))

            st.markdown("#### ✅ Key Strengths Demonstrated:")
            for s in eval_result.get("key_strengths", []):
                st.markdown(f"- {s}")

            st.markdown("#### ⚠️ Areas for Improvement & Missed Checks:")
            for a in eval_result.get("areas_for_improvement", []):
                st.markdown(f"- {a}")

            st.info(f"**Patient Safety Assessment:** {eval_result.get('critical_safety_comment', '')}")

# -------------------------------------------------------------
# TAB 3: NICE GUIDELINES RAG EXPLORER
# -------------------------------------------------------------
with tab3:
    st.markdown("### 📖 NICE Clinical Guidelines RAG Knowledge Base")
    st.caption("Search through official British clinical guidelines directly powering the MedPlab-Agent knowledge base.")

    rag_query = st.text_input("Search Clinical Guidelines (e.g. 'STEMI treatment', 'COPD criteria', 'Type 2 diabetes HbA1c'):", value="chest pain STEMI")
    if st.button("Search Guidelines"):
        with st.spinner("Searching indexed NICE documentation..."):
            try:
                g_res = requests.get(f"{API_URL}/rag/search", params={"query": rag_query})
                g_data = g_res.json().get("results", [])
                if not g_data:
                    st.warning("No direct guideline match found. Try broader clinical keywords.")
                else:
                    for g in g_data:
                        st.markdown(f"#### 📘 {g['title']}")
                        st.markdown(f"**Section:** `{g['section']}` | **Relevance Score:** `{g['score']}`")
                        st.markdown(g["content"])
                        st.divider()
            except Exception as e:
                st.error(f"Error querying RAG engine: {e}")
