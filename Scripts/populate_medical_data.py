import os
import json
import sqlite3

def populate_all():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "Data")
    guidelines_dir = os.path.join(data_dir, "Guidelines")
    osce_dir = os.path.join(data_dir, "OSCE_Stations")
    db_dir = os.path.join(data_dir, "db")

    os.makedirs(guidelines_dir, exist_ok=True)
    os.makedirs(osce_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)

    # -------------------------------------------------------------
    # 1. NICE GUIDELINES (Knowledge Base for RAG)
    # -------------------------------------------------------------
    guidelines = {
        "nice_acs_chest_pain.md": """# NICE Guideline [NG185]: Acute Coronary Syndromes (ACS) & Chest Pain
Published: November 2020 | Last updated: 2023

## Initial Assessment of Suspected Cardiac Chest Pain
- Take a resting 12-lead ECG as soon as possible.
- Do not rule out ACS simply because chest pain is atypical or relieved by sublingual nitrates.
- Key signs of STEMI: ST-segment elevation of ≥1 mm in two or more contiguous limb leads or ≥2 mm in contiguous chest leads, or new LBBB.

## Immediate Emergency Management of STEMI
1. **Dual Antiplatelet Therapy (DAPT):**
   - Aspirin: 300 mg loading dose orally (unless allergic).
   - Second antiplatelet: Ticagrelor 180 mg (preferred) or Prasugrel 60 mg or Clopidogrel 300-600 mg.
2. **Reperfusion Therapy:**
   - Offer immediate coronary angiography with a view to primary PCI if presentation is within 12 hours of symptom onset and PCI can be delivered within 120 minutes of when fibrinolysis could have been given.
   - If primary PCI cannot be delivered within 120 minutes, offer fibrinolysis immediately.
3. **Analgesia & Oxygen:**
   - Offer IV opioids (diamorphine or morphine) titrated to relieve pain.
   - Supplemental oxygen only if SpO2 < 94% on room air (or < 88% in COPD/hypercapnic respiratory failure risk).

## Management of NSTEMI and Unstable Angina
- Assess baseline risk of future adverse cardiovascular events using a validated tool such as GRACE score.
- Offer fondaparinux to patients without a high bleeding risk.
- Perform coronary angiography within 72 hours for patients with intermediate or high risk (GRACE score > 3%).
""",
        "nice_copd_asthma.md": """# NICE Guideline [NG115 & NG80]: COPD & Acute Asthma Management
Published: 2019 - 2024

## Diagnosis and Assessment of COPD
- Consider a diagnosis of COPD in patients aged >35 years who have a risk factor (usually smoking) and recurrent cough, sputum, dyspnea, or frequent winter bronchitis.
- Post-bronchodilator spirometry showing FEV1/FVC < 0.70 confirms persistent airflow obstruction.

## Acute Exacerbation of COPD (AECOPD)
1. **Controlled Oxygen Therapy:** Target SpO2 88-92% if hypercapnic respiratory failure risk is suspected (via 24% or 28% Venturi mask).
2. **Bronchodilators:** Nebulised salbutamol (2.5-5 mg) + ipratropium bromide (500 micrograms).
3. **Corticosteroids:** Oral prednisolone 30 mg once daily for 5 days.
4. **Antibiotics:** Amoxicillin, doxycycline, or clarithromycin if purulent sputum or increased volume and breathlessness.

## Acute Severe Asthma in Adults (BTS/NICE Criteria)
- **Moderate:** Increasing symptoms, PEF 50-75% best/predicted, no features of acute severe.
- **Acute Severe Asthma:**
  - PEF 33-50% best or predicted.
  - Respiratory rate ≥ 25 breaths/min.
  - Heart rate ≥ 110 beats/min.
  - Inability to complete sentences in one breath.
- **Life-Threatening Features:**
  - PEF < 33%, SpO2 < 92%, PaO2 < 8 kPa, "normal" PaCO2 (4.6-6.0 kPa indicates exhaustion).
  - Silent chest, cyanosis, feeble respiratory effort, bradycardia, confusion, exhaustion.
- **Immediate Treatment:** High-flow 100% oxygen via non-rebreathe mask, high-dose nebulised beta-2 agonists (salbutamol 5 mg driven by oxygen), oral prednisolone 40-50 mg or IV hydrocortisone 100 mg, IV magnesium sulfate (1.2-2 g over 20 mins) if severe or refractory.
""",
        "nice_diabetes_type2.md": """# NICE Guideline [NG28]: Type 2 Diabetes in Adults: Management
Updated: June 2023

## Glycemic Targets and Monitoring
- Individualize HbA1c target:
  - 48 mmol/mol (6.5%) with lifestyle or single drug not associated with hypoglycemia.
  - 53 mmol/mol (7.0%) if drug therapy includes sulfonylurea or insulin.
  - Relax targets in frail older adults.

## First-Line Pharmacotherapy
- **Standard First-Line:** Metformin (titrate gradually to reduce GI side effects).
- **If chronic heart failure or established atherosclerotic cardiovascular disease (ASCVD):**
  - Offer Metformin + SGLT2 inhibitor (e.g., Dapagliflozin, Empagliflozin) with proven CV benefit.
- **If Metformin is contraindicated or not tolerated:**
  - DPP-4 inhibitor (gliptin), Pioglitazone, Sulfonylurea, or SGLT2 inhibitor monotherapy.

## Acute Diabetic Emergencies
- **Diabetic Ketoacidosis (DKA):** Diagnostic triad = Ketones > 3.0 mmol/L, Blood Glucose > 11.0 mmol/L (or known diabetes), Venous pH < 7.3 or Bicarbonate < 15 mmol/L. Management: IV fluids (0.9% Normal Saline), fixed-rate IV insulin infusion (0.1 units/kg/h), potassium replacement once K+ < 5.5 mmol/L.
- **Hyperosmolar Hyperglycemic State (HHS):** Severe hyperglycemia (> 30 mmol/L), high serum osmolality (> 320 mOsm/kg), hypovolemia, absence of significant ketoacidosis. Management: Gradual IV 0.9% NaCl rehydration over 48h, normalize osmolality gradually to prevent cerebral edema.
""",
        "nice_hypertension.md": """# NICE Guideline [NG136]: Hypertension in Adults: Diagnosis & Management
Published: August 2019 | Updated: November 2023

## Diagnosis Criteria
- Clinic blood pressure ≥ 140/90 mmHg: Offer Ambulatory Blood Pressure Monitoring (ABPM) or Home BPM (HBPM) to confirm diagnosis.
- **Stage 1 Hypertension:** Clinic BP ≥ 140/90 mmHg AND daytime ABPM/HBPM ≥ 135/85 mmHg.
- **Stage 2 Hypertension:** Clinic BP ≥ 160/100 mmHg AND daytime ABPM/HBPM ≥ 150/95 mmHg.
- **Stage 3 (Severe) Hypertension:** Clinic systolic BP ≥ 180 mmHg OR diastolic BP ≥ 120 mmHg.

## Treatment Thresholds
- Treat Stage 1 if < 80 years old with target organ damage, established CVD, renal disease, diabetes, or 10-year QRISK score ≥ 10%.
- Treat Stage 2 at any age.

## Pharmacological Stepwise Pathway
- **Step 1:**
  - Age < 55 and not of Black African or African-Caribbean origin: ACE inhibitor (e.g., Ramipril) or Angiotensin Receptor Blocker (ARB, e.g., Losartan).
  - Age ≥ 55 or of Black African or African-Caribbean origin: Calcium Channel Blocker (CCB, e.g., Amlodipine).
- **Step 2:** Combine ACEi/ARB + CCB (or Thiazide-like diuretic, e.g., Indapamide).
- **Step 3:** Triple therapy: ACEi/ARB + CCB + Thiazide-like diuretic.
- **Step 4 (Resistant):** Add low-dose Spironolactone if serum K+ ≤ 4.5 mmol/L; or Alpha/Beta-blocker if K+ > 4.5 mmol/L.
""",
        "nice_acute_emergencies.md": """# NICE Guidelines: Acute Neurological & Sepsis Emergencies

## Acute Stroke & TIA [NG128]
- Exclude hypoglycemia immediately (finger-prick glucose).
- Use ROSIER tool to identify acute stroke.
- **Immediate non-contrast Brain CT:** within 1 hour of arrival for patients eligible for thrombolysis/thrombectomy.
- **Thrombolysis (Alteplase):** Administer within 4.5 hours of symptom onset if hemorrhage is excluded and no contraindications (recent surgery, active bleeding, INR > 1.7).
- **Mechanical Thrombectomy:** within 6 hours of symptom onset for confirmed anterior circulation large vessel occlusion.
- **Aspirin 300 mg:** Start 24 hours after thrombolysis or immediately if thrombolysis not indicated once hemorrhage excluded.

## Sepsis in Adults [NG51 - Sepsis Six Pathway]
- Give within 1 hour of recognition:
  1. Give oxygen to maintain SpO2 94-98% (88-92% in COPD).
  2. Take blood cultures before antibiotics.
  3. Give empiric broad-spectrum IV antibiotics.
  4. Give IV fluid bolus (500 ml Hartmann's or Normal Saline over <15 mins if lactate > 2 or hypotensive).
  5. Check serial lactate and blood gas.
  6. Measure accurate hourly urine output (catheterisation).
"""
    }

    for filename, content in guidelines.items():
        path = os.path.join(guidelines_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
    print(f"Created {len(guidelines)} NICE guidelines in {guidelines_dir}")

    # -------------------------------------------------------------
    # 2. OSCE CLINICAL STATIONS (PLAB 2 Scenarios)
    # -------------------------------------------------------------
    osce_stations = [
        {
            "id": "osce-01",
            "title": "Station 1: Acute Chest Pain in Emergency (Arthur Pendelton)",
            "specialty": "Cardiology / Acute Medicine",
            "patient_name": "Arthur Pendelton",
            "patient_age": 58,
            "patient_gender": "Male",
            "vital_signs": "BP 155/92 mmHg, HR 98 bpm, RR 20/min, SpO2 96% on room air, Temp 36.8°C",
            "candidate_brief": "You are a Foundation Doctor in the Acute Medical Unit. Arthur Pendelton, a 58-year-old accountant, presents with central chest tightness that started 2 hours ago while walking upstairs. Please take a focused history, assess his risk factors, explain your differential diagnosis, and discuss immediate management.",
            "patient_brief": {
                "personality": "Anxious, clutching chest occasionally, worried he is having a fatal heart attack like his father.",
                "chief_complaint": "Heavy tightness in the center of my chest, like an elephant sitting on me.",
                "history_of_present_illness": "Started 2 hours ago after climbing stairs. Mildly improved when sitting down but still present as a dull ache. Radiates slightly to left inner arm and jaw.",
                "associated_symptoms": "Felt sweaty and nauseous when it started. No vomiting. Mild shortness of breath.",
                "past_medical_history": "Type 2 Diabetes for 8 years, High Blood Pressure for 12 years. Not had chest pain like this before.",
                "medications": "Metformin 1000mg BD, Ramipril 10mg OD. Often forgets to take his Ramipril.",
                "social_history": "Smokes 15 cigarettes a day for 35 years. Drinks 15-20 units of beer per week. High stress job.",
                "family_history": "Father died of myocardial infarction at age 52.",
                "key_concerns": "'Doctor, am I having a heart attack? Will I survive this?'"
            },
            "marking_scheme": {
                "communication_skills": [
                    "Introduces self clearly and establishes rapport",
                    "Acknowledges patient's anxiety and offers reassurance without false promises",
                    "Listens actively without interrupting patient's narrative"
                ],
                "history_taking": [
                    "Explores SOCRATES of chest pain (Site, Onset, Character, Radiation, Associated, Timing, Exacerbating, Severity)",
                    "Checks cardiovascular risk factors (Diabetes, HTN, Smoking, Family History)",
                    "Screens for red flags: hemodynamic instability, severe dyspnea, syncope"
                ],
                "clinical_judgment": [
                    "Identifies Acute Coronary Syndrome (STEMI vs NSTEMI) as primary concern",
                    "Orders immediate 12-lead ECG and serial cardiac troponins",
                    "Explains immediate treatment clearly: Aspirin 300mg, second antiplatelet, pain relief"
                ],
                "patient_safety": [
                    "Does not leave patient unattended in unstable state",
                    "Ensures IV access and continuous cardiac monitoring"
                ]
            }
        },
        {
            "id": "osce-02",
            "title": "Station 2: Progressive Breathlessness & Cough (Brenda Higgins)",
            "specialty": "Respiratory Medicine",
            "patient_name": "Brenda Higgins",
            "patient_age": 64,
            "patient_gender": "Female",
            "vital_signs": "BP 138/84 mmHg, HR 88 bpm, RR 22/min, SpO2 91% on room air, Temp 37.1°C",
            "candidate_brief": "Brenda Higgins, a 64-year-old retired cleaner, attends the GP surgery complaining of worsening shortness of breath over the past 6 months and a morning cough. Take a focused history, discuss investigations, and propose an initial management plan.",
            "patient_brief": {
                "personality": "Slightly breathless when speaking long sentences, frustrated that she cannot play with her grandchildren.",
                "chief_complaint": "I get out of breath just walking to the local corner shop.",
                "history_of_present_illness": "Breathlessness has crept up over the last 2 years, but much worse in the last 6 months. Frequent morning cough with small amounts of white/clear sputum.",
                "associated_symptoms": "No chest pain, no hemoptysis, no ankle swelling, no unexplained weight loss.",
                "past_medical_history": "Frequent 'chest infections' in winter requiring antibiotics from the GP.",
                "medications": "Over-the-counter cough syrup (doesn't help).",
                "social_history": "Smoked 20 cigarettes a day since age 18 (approx 45 pack-years). Worked as a school cleaner for 25 years.",
                "family_history": "No known respiratory illnesses.",
                "key_concerns": "'Do I have lung cancer, doctor? My brother had it.'"
            },
            "marking_scheme": {
                "communication_skills": [
                    "Speaks at a calm pace and checks patient's understanding",
                    "Directly addresses her fear of lung cancer empathetically",
                    "Offers smoking cessation support non-judgmentally"
                ],
                "history_taking": [
                    "Assesses MRC Dyspnea scale / functional impairment",
                    "Takes thorough smoking and occupational exposure history",
                    "Screens for red flag symptoms of malignancy (hemoptysis, weight loss, night sweats)"
                ],
                "clinical_judgment": [
                    "Identifies COPD as most likely diagnosis; mentions Asthma and Heart failure as differentials",
                    "Orders post-bronchodilator spirometry (diagnostic test) and Chest X-ray",
                    "Discusses inhaler therapy (SABA/SAMA) and pulmonary rehabilitation"
                ],
                "patient_safety": [
                    "Recognizes SpO2 91% and explains target oxygen considerations in COPD"
                ]
            }
        },
        {
            "id": "osce-03",
            "title": "Station 3: Tremors, Heat Intolerance & Palpitations (Sophie Clark)",
            "specialty": "Endocrinology",
            "patient_name": "Sophie Clark",
            "patient_age": 31,
            "patient_gender": "Female",
            "vital_signs": "BP 142/78 mmHg, HR 112 bpm (regular), RR 16/min, SpO2 99%, Temp 37.4°C",
            "candidate_brief": "Sophie Clark, a 31-year-old graphic designer, presents with a 2-month history of nervousness, palpitations, and unintended weight loss. Take a focused history, conduct relevant queries, explain the likely diagnosis and discuss the next steps.",
            "patient_brief": {
                "personality": "Fidgety, speaks quickly, fans herself as she feels too warm in the room.",
                "chief_complaint": "My heart races randomly, and my hands won't stop shaking when I hold a pen.",
                "history_of_present_illness": "Over the past 8 weeks: lost 6 kg despite eating more than usual. Trouble sleeping, feeling constantly hot, increased bowel frequency (loose stools 3x/day).",
                "associated_symptoms": "Noticed her eyes feel gritty and dry. Irregular light menstrual periods.",
                "past_medical_history": "Vitiligo on hands since childhood. Otherwise well.",
                "medications": "Occasional ibuprofen.",
                "social_history": "Drinks 2 cups of coffee a day. Non-smoker. No illicit drugs.",
                "family_history": "Maternal aunt has Hashimoto's thyroiditis.",
                "key_concerns": "'My friends told me I might have an anxiety panic disorder, but it feels physical!'"
            },
            "marking_scheme": {
                "communication_skills": [
                    "Calms the patient and validates her symptoms as genuinely physical",
                    "Explains medical terms (e.g. hyperthyroidism) in simple language",
                    "Gives time for patient questions"
                ],
                "history_taking": [
                    "Elicits systemic thyrotoxic symptoms (weight loss, heat intolerance, tremor, diarrhea)",
                    "Asks specifically about eye symptoms (diplopia, grittiness, retro-orbital ache)",
                    "Identifies personal and family history of autoimmune disorders"
                ],
                "clinical_judgment": [
                    "Identifies Graves' Disease as primary diagnosis (thyrotoxicosis with possible eye involvement)",
                    "Orders Thyroid Function Tests (TSH, free T4, free T3) and TSH-receptor antibodies (TRAb)",
                    "Discusses symptomatic control with Beta-blockers (Propranolol) and definitive antithyroid medications (Carbimazole)"
                ],
                "patient_safety": [
                    "Warns about agranulocytosis risk with Carbimazole (report sore throat/fever immediately)"
                ]
            }
        },
        {
            "id": "osce-04",
            "title": "Station 4: Thunderclap Headache & Red Flags (Marcus Vance)",
            "specialty": "Neurology / Emergency Medicine",
            "patient_name": "Marcus Vance",
            "patient_age": 42,
            "patient_gender": "Male",
            "vital_signs": "BP 168/96 mmHg, HR 82 bpm, RR 18/min, SpO2 98%, Temp 37.0°C",
            "candidate_brief": "Marcus Vance, a 42-year-old solicitor, is brought to the Emergency Department with sudden-onset excruciating occipital headache reaching maximum intensity within 30 seconds. Take a focused history, identify red flags, and outline your immediate investigation plan.",
            "patient_brief": {
                "personality": "Keeps eyes shut because room lights hurt his eyes (photophobia). Holds back of his neck.",
                "chief_complaint": "I felt like someone struck me with a baseball bat across the back of my head.",
                "history_of_present_illness": "Started 4 hours ago while weightlifting at the gym. Instant agonizing pain (10/10 severity within seconds). Vomited twice in the car.",
                "associated_symptoms": "Neck stiffness, sensitive to bright lights. No focal limb weakness, no speech difficulty, no loss of consciousness.",
                "past_medical_history": "Mild migraine history in his twenties, but insists 'this is completely different'.",
                "medications": "None.",
                "social_history": "Smokes 10 cigarettes a day. Drinks socially. No recreational drugs.",
                "family_history": "Mother died of a 'ruptured brain aneurysm' at age 48.",
                "key_concerns": "'I think my brain is bleeding like my mother's did.'"
            },
            "marking_scheme": {
                "communication_skills": [
                    "Maintains a quiet, dimmed environment for photophobic patient",
                    "Communicates with urgency while remaining reassuring and composed",
                    "Involves patient/family in urgent decision-making"
                ],
                "history_taking": [
                    "Identifies thunderclap onset (< 1 minute to peak intensity)",
                    "Checks for meningism (photophobia, neck stiffness) and elevated ICP (vomiting)",
                    "Elicits crucial family history of intracranial aneurysms"
                ],
                "clinical_judgment": [
                    "Recognizes Subarachnoid Hemorrhage (SAH) as emergency working diagnosis",
                    "Orders immediate Non-contrast CT Head within 6 hours of onset (highest sensitivity)",
                    "Explains need for Lumbar Puncture (xanthochromia test) if CT is normal after 12 hours"
                ],
                "patient_safety": [
                    "Never discharges a thunderclap headache without ruling out SAH",
                    "Refers immediately to neurosurgery/stroke team upon confirmation"
                ]
            }
        },
        {
            "id": "osce-05",
            "title": "Station 5: Acute Lower Abdominal Pain (Liam Gallagher)",
            "specialty": "General Surgery",
            "patient_name": "Liam Gallagher",
            "patient_age": 19,
            "patient_gender": "Male",
            "vital_signs": "BP 122/76 mmHg, HR 104 bpm, RR 20/min, SpO2 99%, Temp 38.2°C",
            "candidate_brief": "Liam Gallagher, a 19-year-old student, presents with severe abdominal pain that started around his belly button yesterday and has now shifted to his right lower side. Take a focused history, propose differentials, and explain surgical management.",
            "patient_brief": {
                "personality": "Lying still with knees bent, groaning on movement or coughing.",
                "chief_complaint": "Every time the stretcher bumps or I cough, my right groin feels like it is tearing.",
                "history_of_present_illness": "Started 18 hours ago as a dull periumbilical ache. Over the last 6 hours, shifted to the right iliac fossa and became sharp and constant.",
                "associated_symptoms": "Anorexic (cannot look at food), vomited once, low-grade fever.",
                "past_medical_history": "Nil significant. No previous surgeries.",
                "medications": "Took 2 paracetamol tablets 4 hours ago with minimal relief.",
                "social_history": "First-year university student. Does not smoke, drinks occasionally at weekends.",
                "family_history": "No major bowel disease.",
                "key_concerns": "'Doctor, is my appendix going to burst? Do I need an operation today?'"
            },
            "marking_scheme": {
                "communication_skills": [
                    "Demonstrates empathy towards acute pain and orders prompt analgesia",
                    "Explains the nature of surgical consent and appendectomy simply",
                    "Answers student's concerns about surgery and university exams"
                ],
                "history_taking": [
                    "Characterizes pain migration (visceral periumbilical to somatic right iliac fossa)",
                    "Checks systemic signs: anorexia ('hamburger sign'), low grade fever, nausea",
                    "Excludes differentials: urinary tract symptoms, testicular pain, bowel habit changes"
                ],
                "clinical_judgment": [
                    "Diagnoses Acute Appendicitis as top differential",
                    "Plans pre-operative workup: FBC (neutrophilic leukocytosis), CRP, U&Es, Urinalysis, Ultrasound/CT",
                    "Keeps patient nil-by-mouth (NPO), starts IV fluids, analgesia, and surgical referral"
                ],
                "patient_safety": [
                    "Recognizes signs of peritonitis / perforation risk if untreated"
                ]
            }
        }
    ]

    osce_path = os.path.join(osce_dir, "stations.json")
    with open(osce_path, "w", encoding="utf-8") as f:
        json.dump(osce_stations, f, indent=4)
    print(f"Created {len(osce_stations)} OSCE clinical stations in {osce_path}")

    # -------------------------------------------------------------
    # 3. EXPANDED DATABASE: PLAB 1 & UNIVERSITY QUESTIONS
    # -------------------------------------------------------------
    db_path = os.path.join(db_dir, "merged.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS plabable_all")
    cursor.execute("DROP TABLE IF EXISTS uni")

    cursor.execute("""
    CREATE TABLE plabable_all (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        q INTEGER,
        question TEXT NOT NULL,
        choice_a TEXT,
        choice_b TEXT,
        choice_c TEXT,
        choice_d TEXT,
        choice_e TEXT,
        answer TEXT,
        explanation TEXT,
        topic TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE uni (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        choice_a TEXT,
        choice_b TEXT,
        choice_c TEXT,
        choice_d TEXT,
        answer TEXT,
        topic TEXT,
        level INTEGER
    )
    """)

    plab_questions = [
        (
            1,
            "A 62-year-old male with chronic hypertension presents to the ED with sudden-onset crushing retrosternal chest pain radiating to his left shoulder and jaw. His ECG shows 3 mm ST-segment elevation in leads V1 to V4. What is the most appropriate definitive reperfusion therapy according to current NICE guidelines?",
            "Primary Percutaneous Coronary Intervention (PPCI) within 120 minutes",
            "Immediate intravenous Thrombolysis with Streptokinase",
            "Oral Clopidogrel 75 mg monotherapy and discharge home",
            "Urgent Coronary Artery Bypass Grafting (CABG)",
            "Intravenous Heparin infusion for 48 hours without angiography",
            "Primary Percutaneous Coronary Intervention (PPCI) within 120 minutes",
            "This patient presents with an acute anterior STEMI (ST elevation in V1-V4). NICE [NG185] guidelines recommend immediate primary PCI as the gold standard reperfusion therapy if it can be delivered within 120 minutes of presentation.",
            "CARDIOLOGY"
        ),
        (
            2,
            "A 34-year-old female presents with palpitations, heat intolerance, and unintended weight loss of 5 kg over 2 months. Physical examination reveals a diffuse non-tender goiter with an audible vascular bruit, fine hand tremors, and bilateral exophthalmos. What is the most specific diagnostic test for this patient's condition?",
            "Anti-thyroid Peroxidase Antibodies (Anti-TPO)",
            "TSH-Receptor Antibodies (TRAb)",
            "Thyroid Ultrasound with Doppler",
            "Radioactive Iodine Uptake Scan",
            "Fine Needle Aspiration Cytology (FNAC)",
            "TSH-Receptor Antibodies (TRAb)",
            "The combination of thyrotoxicosis and exophthalmos is classic for Graves' disease. The most specific diagnostic marker is TSH-receptor autoantibodies (TRAb).",
            "ENDOCRINOLOGY"
        ),
        (
            3,
            "A 68-year-old male with a 50 pack-year smoking history presents with progressive dyspnea and productive morning cough for over 2 years. Post-bronchodilator spirometry reveals an FEV1 of 52% of predicted and an FEV1/FVC ratio of 0.58. Which parameter confirms the diagnosis of persistent airflow obstruction consistent with COPD?",
            "FEV1/FVC ratio less than 0.70",
            "FEV1 less than 80% predicted alone",
            "Reversibility of FEV1 by > 15% after Salbutamol",
            "Elevated residual volume on body plethysmography",
            "Normal diffusing capacity for carbon monoxide (DLCO)",
            "FEV1/FVC ratio less than 0.70",
            "According to NICE [NG115] and GOLD guidelines, a post-bronchodilator FEV1/FVC ratio of less than 0.70 confirms chronic airflow limitation in COPD.",
            "RESPIRATORY"
        ),
        (
            4,
            "A 23-year-old male presents to the ED with severe right iliac fossa pain that initially started around the umbilicus 18 hours ago. On examination, he has localized guarding and rebound tenderness at McBurney's point. His temperature is 38.1°C and WBC is 16.5 x 10^9/L. What is the initial pathophysiological event responsible for this condition?",
            "Bacterial invasion of the mucosal lining from Salmonella",
            "Obstruction of the appendiceal lumen by a fecalith or lymphoid hyperplasia",
            "Ischemia due to mesenteric arterial embolism",
            "Autoimmune destruction of the submucosal plexus",
            "Incarceration of an indirect inguinal hernia",
            "Obstruction of the appendiceal lumen by a fecalith or lymphoid hyperplasia",
            "Acute appendicitis is initiated by obstruction of the appendiceal lumen (by a fecalith or lymphoid hyperplasia), causing increased intraluminal pressure, ischemia, and secondary bacterial infection.",
            "SURGERY"
        ),
        (
            5,
            "A 45-year-old man presents with sudden-onset excruciating occipital headache described as 'being struck by a hammer.' The pain reached maximum 10/10 severity within 30 seconds. On exam, he has photophobia and neck stiffness. Brain CT performed 3 hours post-onset is completely normal. What is the next essential diagnostic investigation?",
            "MRI Brain with contrast",
            "Lumbar Puncture performed at least 12 hours after symptom onset",
            "CT Angiography of the head within 48 hours",
            "Immediate repeat non-contrast Brain CT",
            "Discharge with high-dose sumatriptan for migraine",
            "Lumbar Puncture performed at least 12 hours after symptom onset",
            "A thunderclap headache requires exclusion of subarachnoid hemorrhage (SAH). When early CT is negative, a lumbar puncture performed >= 12 hours after onset is required to look for CSF xanthochromia via spectrophotometry.",
            "NEUROLOGY"
        ),
        (
            6,
            "A 52-year-old woman with a history of breast cancer presents with confusion, constipation, polyuria, and severe lethargy. Blood tests show: Serum Calcium 3.45 mmol/L (Normal: 2.20 - 2.60 mmol/L), Phosphate 0.7 mmol/L. ECG reveals a shortened QT interval. What is the most appropriate initial therapy?",
            "Intravenous Furosemide bolus",
            "Aggressive IV 0.9% Normal Saline rehydration (3-4 L in 24 hours)",
            "Oral Bisphosphonates (Alendronate)",
            "Intravenous Calcitonin monotherapy",
            "Hemodialysis",
            "Aggressive IV 0.9% Normal Saline rehydration (3-4 L in 24 hours)",
            "Severe hypercalcemia (> 3.0 mmol/L) causes marked nephrogenic dehydration. The primary initial therapy is aggressive fluid rehydration with 0.9% Normal Saline (3-4 L/24h) before administering bisphosphonates.",
            "ENDOCRINOLOGY"
        ),
        (
            7,
            "A 28-year-old primigravida at 34 weeks gestation presents to the maternity unit with severe frontal headache, visual blurring, and epigastric discomfort. Her BP is 165/110 mmHg and urine dipstick reveals 3+ proteinuria. Deep tendon reflexes are brisk with 3 beats of clonus. What is the most appropriate drug to prevent maternal eclamptic seizures?",
            "Intravenous Diazepam",
            "Intravenous Magnesium Sulfate",
            "Intravenous Phenytoin",
            "Oral Labetalol monotherapy",
            "Intravenous Lorazepam",
            "Intravenous Magnesium Sulfate",
            "This patient has severe pre-eclampsia with impending eclampsia. IV Magnesium Sulfate (4g IV loading dose followed by 1g/h infusion) is the gold standard for seizure prophylaxis.",
            "OBSTETRICS"
        ),
        (
            8,
            "A 4-year-old boy is brought to the Emergency Department with sudden onset of barking cough, stridor at rest, hoarseness, and sternal indrawing. He is pyrexial at 38.3°C. He has no drooling and can swallow his saliva without difficulty. What is the most appropriate single pharmacological intervention?",
            "Inhaled Salbutamol nebuliser",
            "Oral Dexamethasone (0.15 mg/kg single dose)",
            "Intravenous Cefotaxime",
            "Inhaled Budesonide twice daily for 2 weeks",
            "Immediate endotracheal intubation",
            "Oral Dexamethasone (0.15 mg/kg single dose)",
            "The presentation is typical of moderate-to-severe Croup. A single oral dose of dexamethasone (0.15 mg/kg) is recommended by NICE for all children with croup to reduce airway inflammation.",
            "PEDIATRICS"
        ),
        (
            9,
            "A 22-year-old university student is admitted with fever, worsening confusion, and a non-blanching purpuric rash over his trunk and lower extremities. Blood pressure is 85/50 mmHg, heart rate is 125 bpm, and temperature is 39.2°C. Kernig's sign is positive. What is the immediate priority step?",
            "Perform immediate Lumbar Puncture before antibiotics",
            "Administer IV Ceftriaxone (2g) immediately along with fluid resuscitation",
            "Wait for blood culture results to tailor therapy",
            "Order urgent Brain MRI",
            "Administer IV Hydrocortisone alone",
            "Administer IV Ceftriaxone (2g) immediately along with fluid resuscitation",
            "Suspected meningococcal septicemia is an emergency requiring immediate parenteral broad-spectrum antibiotics (IV Ceftriaxone 2g) and fluid resuscitation without waiting for LP or imaging.",
            "INFECTIOUS_DISEASE"
        ),
        (
            10,
            "A 72-year-old female presents with persistent pain over her left temple, jaw claudication while chewing, and tender, pulseless temporal arteries. Her ESR is 98 mm/hr. She reports sudden transient loss of vision in her left eye ('amaurosis fugax') yesterday. What is the most critical immediate action to prevent irreversible blindness?",
            "Schedule temporal artery biopsy for next week and await results",
            "Initiate immediate high-dose oral Prednisolone (60 mg daily)",
            "Start oral Methotrexate monotherapy",
            "Order urgent Head CT scan",
            "Start topical steroid eye drops",
            "Initiate immediate high-dose oral Prednisolone (60 mg daily)",
            "Giant Cell Arteritis (GCA) with visual symptoms requires immediate systemic high-dose corticosteroids (Prednisolone 60 mg/day) to prevent permanent bilateral blindness. Biopsy can be done within 2 weeks of starting steroids.",
            "RHEUMATOLOGY"
        )
    ]

    for q in plab_questions:
        cursor.execute("""
        INSERT INTO plabable_all (q, question, choice_a, choice_b, choice_c, choice_d, choice_e, answer, explanation, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, q)

    uni_questions = [
        (
            "Which cellular organelle is primarily responsible for ATP synthesis through oxidative phosphorylation?",
            "Ribosome", "Mitochondria", "Endoplasmic Reticulum", "Golgi Apparatus",
            "B", "Physiology", 1
        ),
        (
            "Which cranial nerve supplies parasympathetic innervation to the thoracic and abdominal viscera up to the splenic flexure?",
            "Cranial Nerve VII (Facial)", "Cranial Nerve IX (Glossopharyngeal)", "Cranial Nerve X (Vagus)", "Cranial Nerve XII (Hypoglossal)",
            "C", "Anatomy", 1
        ),
        (
            "What is the mechanism of action of beta-lactam antibiotics such as penicillin and cephalosporins?",
            "Inhibition of bacterial 50S ribosomal subunit", "Inhibition of bacterial cell wall peptidoglycan cross-linking via transpeptidase", "Inhibition of DNA topoisomerase II (gyrase)", "Disruption of bacterial cell membrane permeability",
            "B", "Pharmacology", 2
        ),
        (
            "In cardiac electrophysiology, which ion movement is primarily responsible for the rapid depolarization (Phase 0) of the ventricular action potential?",
            "Inward flux of Sodium (Na+) via fast voltage-gated channels", "Inward flux of Calcium (Ca2+) via L-type channels", "Outward flux of Potassium (K+)", "Efflux of Chloride (Cl-)",
            "A", "Physiology", 1
        ),
        (
            "A patient with chronic kidney disease develops secondary hyperparathyroidism. What is the primary biochemical trigger?",
            "Hypercalcemia and elevated calcitriol", "Phosphate retention and decreased 1,25-dihydroxyvitamin D (calcitriol) production", "Direct stimulation of parathyroid cells by uremic toxins", "Decreased renal clearance of parathyroid hormone",
            "B", "Pathology", 2
        )
    ]

    for u in uni_questions:
        cursor.execute("""
        INSERT INTO uni (question, choice_a, choice_b, choice_c, choice_d, answer, topic, level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, u)

    conn.commit()
    conn.close()
    print(f"Database successfully populated with {len(plab_questions)} PLAB questions and {len(uni_questions)} Uni questions at {db_path}")

if __name__ == "__main__":
    populate_all()
