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
    .paywall-box {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
if "auth_token" not in st.session_state:
    st.session_state["auth_token"] = None
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "distinct_accessed" not in st.session_state:
    st.session_state["distinct_accessed"] = 0
if "free_limit" not in st.session_state:
    st.session_state["free_limit"] = 30
if "access_request_status" not in st.session_state:
    st.session_state["access_request_status"] = "none"
if "plab_questions" not in st.session_state:
    st.session_state["plab_questions"] = []
if "tutor_analysis" not in st.session_state:
    st.session_state["tutor_analysis"] = {}
if "paywall_info" not in st.session_state:
    st.session_state["paywall_info"] = None
if "osce_chat" not in st.session_state:
    st.session_state["osce_chat"] = []
if "osce_eval" not in st.session_state:
    st.session_state["osce_eval"] = None

def get_auth_headers():
    token = st.session_state.get("auth_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def refresh_user_profile():
    token = st.session_state.get("auth_token")
    if not token:
        return None
    try:
        res = requests.get(f"{API_URL}/auth/me", headers=get_auth_headers())
        if res.status_code == 200:
            data = res.json()
            st.session_state["current_user"] = data.get("user")
            st.session_state["distinct_accessed"] = data.get("distinct_questions_accessed", 0)
            st.session_state["free_limit"] = data.get("free_tier_question_limit", 30)
            st.session_state["access_request_status"] = data.get("access_request_status", "none")
            return data
        elif res.status_code == 401:
            st.session_state["auth_token"] = None
            st.session_state["current_user"] = None
            return None
    except Exception:
        return None

# Refresh user profile if authenticated
if st.session_state.get("auth_token"):
    refresh_user_profile()

# -------------------------------------------------------------
# SIDEBAR: Account Profile & Knowledge Base Status
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-doctor.png", width=64)
    st.title("MedPlab-Agent")
    st.markdown("**Dual-Brain GenAI Clinical Copilot**")
    st.caption("Designed for UK PLAB 1 & PLAB 2 (OSCE) Excellence")
    st.divider()

    if st.session_state.get("auth_token") and st.session_state.get("current_user"):
        user = st.session_state["current_user"]
        st.subheader("👤 Candidate Profile")
        st.write(f"**Email:** `{user.get('email')}`")
        sub_status = user.get("subscription_status", "free")
        if sub_status == "active":
            st.success("💎 **Status: Full Access (Active)**")
        else:
            st.info("🎟️ **Status: Free Tier**")
            accessed = st.session_state.get("distinct_accessed", 0)
            limit = st.session_state.get("free_limit", 30)
            st.write(f"**Questions Accessed:** `{accessed} / {limit}`")
            req_status = st.session_state.get("access_request_status", "none")
            if req_status == "pending":
                st.warning("⏳ Full Access: **Pending Approval**")
            elif req_status == "approved":
                st.success("✅ Full Access: **Approved**")

        if st.button("🚪 Log Out", key="btn_logout", use_container_width=True):
            st.session_state["auth_token"] = None
            st.session_state["current_user"] = None
            st.session_state["plab_questions"] = []
            st.session_state["tutor_analysis"] = {}
            st.session_state["paywall_info"] = None
            st.session_state["osce_chat"] = []
            st.session_state["osce_eval"] = None
            st.rerun()
    else:
        st.info("🔒 Please sign in or register to access clinical training modules.")

    st.divider()
    st.subheader("📚 Grounded Knowledge Base")
    st.markdown("""
    - ✅ **NICE Guidelines RAG (Acute & Mental Health):**
      - NG185: Acute Coronary Syndromes
      - NG115/80: COPD & Acute Asthma
      - NG28: Type 2 Diabetes Management
      - NG136: Hypertension in Adults
      - NG128/51: Stroke & Sepsis Emergencies
      - NG222: Depression in Adults
    - ✅ **GMC Standards RAG (Ethics & Professionalism):**
      - Good Medical Practice (2024): Domains 1–4 (38 Topics)
    - ✅ **OSCE Virtual Stations:** 5 Active
    - ✅ **Zero-Hallucination Guardrails:** Enabled
    """)
    st.caption(f"Backend Server: `{API_URL}`")

# -------------------------------------------------------------
# AUTHENTICATION GATE (Block access to tabs if not logged in)
# -------------------------------------------------------------
if not st.session_state.get("auth_token") or not st.session_state.get("current_user"):
    st.markdown('<div class="main-title">🩺 Welcome to MedPlab-Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">An Agentic GenAI platform combining <b>Socratic MCQ Differential Reasoning (PLAB 1)</b> and <b>Interactive Virtual Patient Consultations (PLAB 2 OSCE)</b>.</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_mode = st.radio("Choose Option:", ["Log In", "Create Free Account"], horizontal=True)
        with st.form("auth_box"):
            email_val = st.text_input("Email Address", placeholder="doctor@nhs.net")
            pass_val = st.text_input("Password", type="password", placeholder="Enter password (min 6 characters)")
            auth_submit = st.form_submit_button("Continue", type="primary", use_container_width=True)

        if auth_submit:
            if not email_val.strip() or not pass_val.strip():
                st.error("Please enter both email and password.")
            elif auth_mode == "Create Free Account":
                try:
                    r = requests.post(f"{API_URL}/auth/signup", json={"email": email_val.strip(), "password": pass_val.strip()})
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state["auth_token"] = data["token"]
                        st.session_state["current_user"] = data["user"]
                        st.success("Account created successfully! Welcome to MedPlab-Agent.")
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Sign up failed."))
                except Exception as e:
                    st.error(f"Error connecting to backend: {e}")
            else: # Log In
                try:
                    r = requests.post(f"{API_URL}/auth/login", json={"email": email_val.strip(), "password": pass_val.strip()})
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state["auth_token"] = data["token"]
                        st.session_state["current_user"] = data["user"]
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Invalid email or password."))
                except Exception as e:
                    st.error(f"Error connecting to backend: {e}")

    st.stop()

# -------------------------------------------------------------
# MAIN APP (Only accessible once authenticated)
# -------------------------------------------------------------
st.markdown('<div class="main-title">🩺 MedPlab-Agent: Clinical Decision & OSCE Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">An Agentic GenAI platform combining <b>Socratic MCQ Differential Reasoning (PLAB 1)</b> and <b>Interactive Virtual Patient Consultations (PLAB 2 OSCE)</b>.</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "📝 PLAB 1: Smart Exam & Socratic Tutor",
    "🩺 PLAB 2: Virtual Clinic (OSCE Simulator)",
    "📖 NICE & GMC Guidelines Explorer"
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
                res = requests.get(f"{API_URL}/{source}", params=params, headers=get_auth_headers())
                res.raise_for_status()
                res_data = res.json()

                if isinstance(res_data, dict) and res_data.get("paywall_triggered"):
                    st.session_state["paywall_info"] = res_data
                    st.session_state["plab_questions"] = []
                else:
                    st.session_state["plab_questions"] = res_data
                    st.session_state["paywall_info"] = None
                    st.session_state["tutor_analysis"] = {}
                refresh_user_profile()
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

    # Paywall Triggered Banner & Request Access Button
    paywall = st.session_state.get("paywall_info")
    if paywall:
        st.markdown("""
        <div class="paywall-box">
            <h3 style="color:#B45309; margin-top:0;">🔒 Free Tier Limit Reached</h3>
            <p style="font-size:1.05rem; color:#92400E;">
                You have reached your free tier question quota. Upgrade to Full Access to unlock the complete PLAB question bank and unlimited clinical consultations.
            </p>
        </div>
        """, unsafe_allow_html=True)

        req_status = st.session_state.get("access_request_status", "none")
        if req_status == "pending":
            st.info("⏳ **Access Upgrade Pending:** Your request for full access has been submitted and is awaiting administrator approval.")
        else:
            if st.button("🚀 Request Full Access Upgrade", type="primary"):
                with st.spinner("Submitting access request..."):
                    try:
                        r_req = requests.post(f"{API_URL}/billing/request-access", headers=get_auth_headers())
                        if r_req.status_code == 200:
                            st.session_state["access_request_status"] = "pending"
                            st.success("✅ Access request submitted! An administrator will review and approve your account.")
                            st.rerun()
                        else:
                            st.error(r_req.json().get("detail", "Failed to submit access request."))
                    except Exception as e:
                        st.error(f"Request failed: {e}")

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
                                "user_choice": user_selection
                            }
                            resp = requests.post(f"{API_URL}/tutor/analyze", json=payload, headers=get_auth_headers())
                            if resp.status_code == 429:
                                err_msg = resp.json().get("detail", "Daily limit reached, try again tomorrow.")
                                st.warning(f"⚠️ {err_msg}")
                            elif resp.status_code == 200:
                                analysis = resp.json()
                                st.session_state[f"analysis_{idx}"] = analysis
                                refresh_user_profile()
                            else:
                                st.error(f"Analysis failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

                # Display Tutor Analysis if available
                analysis_data = st.session_state.get(f"analysis_{idx}")
                if analysis_data:
                    st.divider()

                    # Offline Fallback Banner
                    if analysis_data.get("is_offline_fallback"):
                        st.info("ℹ️ Running in Offline Demonstration Mode (Heuristic Clinical Engine)")

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
    elif not paywall:
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
                        "message": active_msg
                    }
                    p_resp = requests.post(f"{API_URL}/osce/chat", json=payload, headers=get_auth_headers())
                    if p_resp.status_code == 429:
                        st.warning(f"⚠️ {p_resp.json().get('detail', 'Daily limit reached, try again tomorrow.')}")
                    elif p_resp.status_code == 200:
                        reply = p_resp.json().get("reply", "")
                        st.session_state["osce_chat"].append({"role": "assistant", "content": reply})
                        st.rerun()
                    else:
                        st.error(f"Error chatting with patient: {p_resp.text}")
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
                                "chat_history": st.session_state["osce_chat"]
                            }
                            e_resp = requests.post(f"{API_URL}/osce/evaluate", json=eval_payload, headers=get_auth_headers())
                            if e_resp.status_code == 429:
                                st.warning(f"⚠️ {e_resp.json().get('detail', 'Daily limit reached, try again tomorrow.')}")
                            elif e_resp.status_code == 200:
                                st.session_state["osce_eval"] = e_resp.json()
                            else:
                                st.error(f"Evaluation error: {e_resp.text}")
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
# TAB 3: NICE & GMC GUIDELINES RAG EXPLORER
# -------------------------------------------------------------
with tab3:
    st.markdown("### 📖 NICE Clinical Guidelines & GMC Ethical Standards Knowledge Base")
    st.caption("Search through official British clinical guidelines (NICE) and ethical standards (GMC) powering the MedPlab-Agent knowledge base.")

    rag_query = st.text_input(
        "Search Clinical Guidelines & GMC Ethics (e.g. 'chest pain STEMI', 'depression treatment', 'patient confidentiality', 'consent'):",
        value="patient confidentiality"
    )
    if st.button("Search Knowledge Base"):
        with st.spinner("Searching indexed NICE & GMC documentation..."):
            try:
                g_res = requests.get(f"{API_URL}/rag/search", params={"query": rag_query})
                g_data = g_res.json().get("results", [])
                if not g_data:
                    st.warning("No direct guideline match found. Try broader clinical or ethical keywords.")
                else:
                    for g in g_data:
                        source_icon = "⚖️" if g.get("source_body") == "GMC" else "📘"
                        domain_tag = g.get("clinical_domain", "general").replace("_", " ").title()
                        authority_note = g.get("source_authority_note", "")
                        st.markdown(f"#### {source_icon} {g['title']}")
                        st.markdown(f"**Section:** `{g['section']}` | **Domain:** `{domain_tag}` | **Relevance Score:** `{g['score']}`")
                        if authority_note:
                            st.caption(f"**Authority:** `{g.get('source_body', 'NICE')}` — {authority_note}")
                        st.markdown(g["content"])
                        st.divider()
            except Exception as e:
                st.error(f"Error querying RAG engine: {e}")
