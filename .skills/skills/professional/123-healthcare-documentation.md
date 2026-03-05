---
name: healthcare-documentation
description: "Write clinical documentation including SOAP notes, discharge summaries, care plans, medication reconciliation, patient education materials, informed consent templates, and referral letters. Includes ICD-10 coding references and HIPAA compliance."
category: professional
difficulty: advanced
model_boost: "Weak models lack clinical specificity, miss HIPAA requirements, or produce non-defensible documentation"
---

# Healthcare Documentation

## Purpose
Clinical documentation serves four critical functions: patient care (enabling continuity), legal defense (malpractice protection), billing (supporting coding and reimbursement), and research. Poor documentation creates patient safety risks, billing denials, and legal liability. This skill ensures clarity, completeness, defensibility, and compliance. Documentation must be timely (written during or immediately after the encounter), accurate (objective findings, not assumptions), and specific (not vague or copy-pasted from prior visits).

## When to Use
- **Patient encounters** (office visits, hospital admissions, emergency care)
- **Discharge planning** (when patient leaves inpatient setting)
- **Care transitions** (referrals, follow-up coordination)
- **Patient education** (explaining diagnosis and treatment to patient)
- **Informed consent** (before procedures or significant treatment changes)
- **Do NOT use when**: Creating policies (use policy templates), writing marketing materials, or documenting incidents for legal defense (consult legal counsel first)

## Important HIPAA & Legal Note
This skill is educational framework for documentation structure. It does NOT provide legal or medical advice. All healthcare documentation must comply with HIPAA, state medical boards, and organizational policies. Consult your healthcare provider organization's compliance and legal teams before implementing templates.

## Instructions

### Step 1: Master SOAP Note Structure
SOAP (Subjective, Objective, Assessment, Plan) is the standard format for clinical notes. Each section has distinct purpose and content.

**Subjective (S)**: What the patient reports. Include:
- Chief complaint: Why did they come today?
- History of present illness (HPI): Timeline, severity, impact on function
- Relevant medical/surgical history
- Medications (with doses and frequency)
- Allergies
- Social history (smoking, alcohol, living situation) if relevant to visit
- Patient's goals or concerns

Example (Poor): "Patient complains of headache."
Example (Good): "Patient reports bifrontal headache x 5 days, worse in mornings and with bright light. Rates pain 7/10. Associated with nausea but denies vomiting or vision changes. Resolved with acetaminophen 500mg. States 'I need to return to work by Monday'—this is affecting her ability to manage her business. Denies recent illness or head trauma. No prior similar headaches. Currently taking lisinopril for hypertension, no other medications."

**Objective (O)**: Measurable findings from exam and tests. Include:
- Vital signs (BP, HR, temp, RR, O2 sat)
- Physical exam findings (organized by body system or area of complaint)
- Lab/imaging results (if available)
- Avoid impressions; state what you observe

Example (Poor): "Exam normal."
Example (Good): "Vitals: BP 138/82, HR 72, RR 14, temp 98.6F, O2 98% RA. HEENT: Normocephalic, no sinus tenderness to percussion, pupils equal and reactive, no papilledema. Neurologic: Alert and oriented x3, cranial nerves II-XII intact, motor 5/5 throughout, sensory intact to light touch, reflexes 2+ symmetrical, no focal deficits. Labs: CBC normal, CMP normal, TSH 1.2 (normal). CT head: No acute findings."

**Assessment (A)**: Your clinical impression. Include:
- Primary diagnosis (use ICD-10 code)
- Differential diagnoses considered (if relevant to decision-making)
- Severity/stage (if applicable)
- Justification for diagnosis based on S + O

Example (Poor): "Migraine."
Example (Good): "Primary diagnosis: Migraine without aura (G43.909). Patient presents with bifrontal headache, photophobia, and nausea for 5 days. Exam is reassuring (no papilledema, normal neuro exam). Recent labs and imaging rule out secondary causes (infection, stroke, mass). This presentation is consistent with migraine. Differential included tension headache (less likely given severity and photophobia) and sinusitis (but no sinus tenderness)."

**Plan (P)**: What you're doing next. Include:
- Treatments prescribed (with dose, frequency, duration)
- Patient education (what you explained)
- Follow-up timeline and trigger for earlier return
- Referrals or specialist involvement

Example (Poor): "Continue current meds. Follow up as needed."
Example (Good): "Plan:
1. Pharmacotherapy: Start sumatriptan 50mg PO as needed for acute migraine (max 2x/week to prevent medication overuse headache). Discussed side effects (flushing, dizziness) and when to seek ER care (symptoms not improving in 2 hours).
2. Preventive: Consider propranolol 40mg daily if frequency increases >2 headaches/month. Will reassess at follow-up.
3. Education: Discussed migraine triggers (stress, sleep, skipped meals), advised keeping headache diary, hydration and sleep hygiene.
4. Follow-up: Return in 2 weeks to review diary and response to treatment. Return sooner if headaches worsen or new neurologic symptoms develop (vision loss, focal weakness, speech changes).
5. Referral: If migraines continue despite treatment, will refer to neurology for further evaluation."

### Step 2: Write Hospital Admission / Discharge Summaries
Discharge summaries are critical for continuity. They're often the only document the next provider reads.

**Hospital Admission Note** (First note of stay):

```
HOSPITAL ADMISSION NOTE

PATIENT: [Name] | MRN: [#] | DOB: [Date] | Age: [Age]
DATE OF ADMISSION: [Date/Time]
ADMITTING PHYSICIAN: [Name]
ATTENDING PHYSICIAN: [Name]

CHIEF COMPLAINT:
[One sentence reason for admission]

HISTORY OF PRESENT ILLNESS:
[Detailed timeline of symptoms leading to hospitalization]

PAST MEDICAL HISTORY:
[List with dates and status]

MEDICATIONS ON ADMISSION:
[Name, dose, frequency, route for each]

ALLERGIES:
[Drug/food allergies and reaction type]

SOCIAL HISTORY:
[Smoking, alcohol, living situation, support system, occupation if relevant]

FAMILY HISTORY:
[Relevant conditions in first-degree relatives]

PHYSICAL EXAMINATION:
[Vital signs, complete exam findings by system]

ASSESSMENT & PLAN:
[Primary diagnosis with ICD-10 code and clinical reasoning]
[Secondary diagnoses if applicable]
[Initial treatment plan: medications, tests, monitoring]
[Specialist consultations ordered]

ADMISSION ORDERS:
[NPO status, activity level, monitoring level (ICU vs. floor)]

SIGNED: [Physician name and credentials] | [Time/Date]
```

**Discharge Summary** (At end of hospital stay):

The discharge summary should be complete enough that the patient can return to their primary care physician with full context.

```
HOSPITAL DISCHARGE SUMMARY

PATIENT: [Name] | MRN: [#] | DOB: [Date]
ADMISSION DATE: [Date] | DISCHARGE DATE: [Date]
LENGTH OF STAY: [# days]
ATTENDING PHYSICIAN: [Name]

DISCHARGE DIAGNOSIS:
1. [Primary diagnosis with ICD-10]
2. [Secondary diagnoses with ICD-10 codes]

PROCEDURE(S) PERFORMED:
[If applicable, with CPT codes if billing-relevant]

BRIEF HOSPITAL COURSE:
[Narrative of what happened during stay, major events/changes]
Example: "Patient admitted with acute chest pain and elevated troponin. EKG showed ST elevation in anterior leads consistent with STEMI. Underwent emergent cardiac catheterization with stent placement to LAD. Course complicated by acute heart failure; treated with diuretics and ACE inhibitor. Troponin peaked at 4.2 then trended down. Echocardiogram showed EF 35% with anterior wall akinesis. Discharged stable, chest pain resolved."

MEDICATIONS ON DISCHARGE:
- [Name, dose, frequency, route, duration if limited]
- [Continue existing medications]
- [Note: "NEW" for medications started during admission]

DISCHARGE INSTRUCTIONS:
1. Activity: [What's allowed]
2. Diet: [Any restrictions]
3. Wound care: [If applicable]
4. Medications: [Emphasis on any new/changed meds]
5. Warning signs: [Specific symptoms requiring ER evaluation]

FOLLOW-UP CARE:
- Primary care physician: Within [timeframe]; appointment [made / should be scheduled]
- Cardiology: Within [timeframe]
- [Any other specialists]

OUTSTANDING TESTS/RESULTS:
[Tests pending, when results expected]

RESTRICTIONS:
[Work, driving, other activities]

PATIENT/FAMILY EDUCATION:
[What was discussed; patient understanding]

SIGNED: [Physician name] | [Date/Time]
```

### Step 3: Create Medication Reconciliation
Every transition (admission, discharge, specialist visit) requires medication reconciliation. This prevents errors like drug interactions or duplicate therapies.

**Medication Reconciliation Format**:

```
MEDICATION RECONCILIATION

Date: [Date] | Reconciled by: [Name] | Verified with: [Patient/Family/Prior records]

PATIENT'S REPORTED MEDICATIONS (from patient interview):
1. Lisinopril 10mg PO daily (HTN)
2. Metformin 500mg PO BID (DM2)
3. Aspirin 81mg PO daily (CAD prevention)
4. Atorvastatin 20mg PO nightly (cholesterol)
5. [Patient states] "I think I'm also taking something for my nerves but I don't remember the name"

PRIOR MEDICATION LIST (from EHR/prior records):
1. Lisinopril 10mg PO daily
2. Metformin 500mg PO BID
3. Aspirin 81mg PO daily
4. Atorvastatin 20mg PO nightly
5. Alprazolam 0.5mg PO TID PRN (anxiety)

MEDICATIONS FROM CURRENT ADMISSION/PRESCRIPTION:
1. Lisinopril 10mg PO daily → CONTINUE
2. Metformin 500mg PO BID → CONTINUE
3. Aspirin 81mg PO daily → CONTINUE
4. Atorvastatin 20mg PO nightly → CONTINUE
5. Alprazolam 0.5mg PO TID PRN → CONTINUE [Patient was not aware of this; counseled on name and use]
6. Sertraline 50mg PO daily → NEW (started during admission for post-MI depression)

DISCREPANCIES IDENTIFIED:
- Patient was unaware of Alprazolam; counseled on purpose and use
- Sertraline is new; patient counseled on indication (mood support after MI), side effects, and need to contact provider if worsening mood or suicidal thoughts

PATIENT EDUCATION:
- Reviewed all medications and purposes
- Addressed questions about interactions (none significant)
- Advised to fill prescriptions before discharge
- Provided written medication list

ACKNOWLEDGED BY PATIENT: [Signature/Initial]
```

### Step 4: Design Care Plans & Treatment Plans
Care plans document goals, interventions, and expected outcomes.

**Example Care Plan** (for chronic disease):

```
CARE PLAN: Type 2 Diabetes Mellitus

PATIENT: [Name] | MRN: [#] | Date created: [Date]

GOALS (Patient's stated goals & clinical targets):
1. Achieve HbA1c <7% (currently 8.1%)
2. Maintain BP <140/90 (currently 145/92)
3. "Return to exercising 3x/week" (patient goal; currently sedentary due to work stress)
4. Avoid hospitalization for hypoglycemia or hyperglycemic crisis

CLINICAL PROBLEMS:
1. Hyperglycemia (HbA1c 8.1%; goal <7%)
2. Hypertension (BP 145/92; goal <140/90)
3. Sedentary lifestyle (barrier to glycemic control)
4. Medication non-adherence (patient admits missing doses 2-3x/week)

INTERVENTIONS (What we'll do):

**Medication management:**
- Continue Metformin 500mg BID (review adherence barriers)
- Add Lisinopril 10mg daily (addresses HTN + diabetes protector for kidneys)
- Continue Atorvastatin 20mg nightly

**Education & self-management:**
- Diabetes education class (referral to certified diabetes educator; 3-4 sessions)
- Discuss barriers to medication adherence; consider pill organizer or phone reminders
- Nutrition referral to dietitian for low-glycemic diet counseling
- Home glucose monitoring: Advise BID checks (before breakfast, before dinner)

**Activity:**
- Exercise prescription: Start with 10 min daily walking, build to 30 min 5x/week over 3 months
- Occupational barriers: Discussed job stress; referred to employee assistance program for stress management

**Monitoring:**
- HbA1c in 3 months (goal: reduce to <7%)
- BP monitoring at home or pharmacy; monthly clinic checks
- Kidney function (annual)
- Eye exam referral (annual dilated eye exam for retinopathy screening)

**Follow-up:**
- Clinic visit in 3 months to review HbA1c, adjust meds if needed
- Diabetes educator visits (3-4 sessions over 2 months)
- Dietitian visit within 2 weeks
- Sooner return if: blood glucose >300, symptoms of DKA (nausea, fruity breath, altered mental status), or hypoglycemic episodes

EXPECTED OUTCOMES (3-6 months):
- HbA1c <7%
- BP <140/90 (likely achieved with Lisinopril)
- Adherence to meds improved with support strategies
- Patient exercising 3x/week

PATIENT SIGNATURE: [Date] [Indicates understanding and agreement]
```

### Step 5: Create Patient Education Materials
Patient education must be understandable, culturally appropriate, and actionable.

**Patient Education Example** (Hypertension):

```
YOUR BLOOD PRESSURE HEALTH

What is hypertension (high blood pressure)?
Your heart pumps blood through arteries to your body. Blood pressure is the force of blood against your artery walls.
- Normal: Less than 120/80
- High: 140/90 or higher
- Yours: [Patient's latest reading]

High blood pressure damages your arteries and heart over time. You can't feel it, so regular checking is important.

WHY THIS MATTERS FOR YOU:
[Personalized: "Your father had a heart attack at age 55. Your high blood pressure increases your risk. We want to prevent that for you."]

WHAT YOU CAN DO:

1. **Medications** (Your doctor prescribed these to help)
   - Lisinopril 10mg: Take by mouth once daily (morning or evening; pick a time you'll remember)
   - Atorvastatin 20mg: Take by mouth at bedtime

   IMPORTANT: Take these even if you feel fine. You can't feel high blood pressure, so symptoms aren't a guide.

2. **Diet** (Eat less salt, more vegetables)
   - Aim for <2300mg sodium daily (about 1 teaspoon of salt)
   - Read food labels; frozen/processed foods are high in salt
   - Eat more vegetables, fruits, whole grains
   - Limit caffeine (more than 2 cups coffee/day can raise BP)

3. **Activity**
   - Aim for 30 minutes of moderate activity (brisk walking, cycling) at least 5 days/week
   - Start with 10 minutes if you're not exercising now; build up slowly
   - Any activity is better than none

4. **Stress & Sleep**
   - Aim for 7-9 hours sleep per night
   - Practice stress relief: deep breathing, meditation, hobbies
   - [Resource: Employee assistance program offers free counseling]

5. **Monitor at home**
   - Check BP at same time daily (morning is best)
   - Record readings in a log or app
   - Bring log to your appointments

WARNING SIGNS—Call 911 or go to ER if:
- Chest pain or pressure
- Shortness of breath
- Severe headache with vision changes
- Weakness on one side of body

QUESTIONS?
Call our office at [number]. Your provider is happy to answer questions.

[Visual: BP categories chart | Recipe ideas for low-salt meals | Links to walking routes near patient's home]
```

### Step 6: Write Informed Consent Documents
Informed consent must be specific to the procedure, understandable, and document that risks were discussed.

**Informed Consent Template** (Example: Cardiac Catheterization):

```
INFORMED CONSENT FORM
Cardiac Catheterization with Possible Stent Placement

PATIENT: [Name] | MRN: [#] | DATE: [Date]
PROCEDURE: Cardiac catheterization (heart catheter) with possible angioplasty and stent

INDICATION FOR PROCEDURE:
[Your diagnosis and why the procedure is necessary; e.g., "You have a blockage in your heart artery that limits blood flow. This procedure will allow us to see the blockage clearly and place a stent to reopen it."]

PROCEDURE EXPLANATION:
We will insert a thin tube (catheter) through an artery in your arm or leg. Using X-ray guidance, we'll thread the catheter to your heart arteries. We'll inject dye to see the vessels clearly. If we find a blockage, we may place a stent (small metal mesh tube) to hold the artery open.

BENEFITS:
- Diagnosis: Clear picture of which arteries are blocked
- Treatment: Stent reopens the artery and improves blood flow
- Symptom relief: Reduced chest pain, better exercise tolerance
- Reduced heart attack risk

RISKS & POSSIBLE COMPLICATIONS:
Serious risks (rare but serious):
- Heart attack: <1%
- Stroke: <1%
- Death: <0.5% (higher if already very ill)
- Bleeding at catheter site: 1-2%
- Allergic reaction to dye: <1%
- Kidney injury from dye: 2-5% (higher if kidney disease)

Less serious risks:
- Bruising at catheter site: 10-20%
- Artery damage requiring surgery: <1%
- Irregular heartbeat: transient, usually self-resolving

ALTERNATIVE TREATMENTS:
- Medical management alone (medication without procedure)
- Bypass surgery (if multiple severe blockages)

I UNDERSTAND THAT:
- No treatment is completely risk-free
- The procedure may not fully relieve symptoms
- I may need additional procedures in the future
- I may stay overnight if complications occur
- I will receive anesthesia/sedation, and the risks of sedation were explained

QUESTIONS I HAVE ASKED AND HAD ANSWERED:
[Checklist for provider]
☐ When can I return to normal activity?
☐ Will my symptoms go away?
☐ What happens if the stent blocks again?
☐ What medications will I need afterward?

PATIENT SIGNATURE: _________________ DATE: _______
[Indicates patient understood and agrees to proceed]

PHYSICIAN SIGNATURE: _________________ DATE: _______
[Indicates physician explained procedure and assessed understanding]

WITNESS: _________________ DATE: _______
[Independent person present; for vulnerable patients or if consent capacity is borderline]
```

### Step 7: Compose Referral Letters
Clear referral letters enable specialist care and ensure follow-up.

**Referral Letter Template**:

```
REFERRAL LETTER

TO: [Specialist name and contact] | SPECIALTY: [Cardiology, Neurology, etc.]
FROM: [Your name and practice]
DATE: [Date]
RE: [Patient name] | DOB: [Date] | MRN: [#]

REASON FOR REFERRAL:
[Clear, concise statement of why you're referring]
Example: "I'm referring [patient] for evaluation of new-onset atrial fibrillation. She has a history of hypertension and is now experiencing palpitations and dyspnea on exertion."

CLINICAL SUMMARY:
[Brief HPI, relevant PMH, current medications, exam findings]

KEY LABS/IMAGING:
- EKG: [Date] - Atrial fibrillation with RVR (rate 110-130)
- Troponin: [Date] - Normal
- Chest X-ray: [Date] - No acute findings
- Echocardiogram: [Date] - Pending (will forward when available)

CURRENT MEDICATIONS:
[List all current meds]

ALLERGIES:
[Drug and reaction]

SPECIFIC QUESTIONS/CONCERNS:
- Is this paroxysmal or persistent AFib?
- What is her risk for stroke? (Calculate CHADS2-VASc)
- Does she need anticoagulation?
- Would rate control or rhythm control be more appropriate?

URGENCY: [Routine / Soon (within 1-2 weeks) / Urgent (within 3-5 days)]

[Patient contact info and insurance info]

SIGNED: [Your name, credentials] | [Date]

---
PATIENT COPY:
[Keep appointment confirmation and contact info with referral office]
```

### Step 8: Ensure ICD-10 Coding Accuracy
Accurate coding ensures billing and creates proper medical record. Use valid ICD-10 codes.

**Common ICD-10 Examples** (Examples; not exhaustive):

| Condition | ICD-10 Code | Notes |
|-----------|------------|-------|
| Type 2 Diabetes Mellitus | E11.9 | Unspecified; refine if complications present |
| Essential Hypertension | I10 | Most common primary HTN code |
| STEMI - Anterior wall | I21.01 | First episode, anterior; specify if ongoing |
| Heart failure - Systolic | I50.21 | EF <40%; systolic dysfunction |
| Atrial Fibrillation | I48.91 | Unspecified type; specify paroxysmal/persistent if known |
| Migraine without aura | G43.909 | Unspecified intractability/status; refine based on specifics |
| Pneumonia - bacterial | J15.9 | Unspecified bacterial; refine if organism known |

**Coding Best Practices**:
- Use ICD-10 codes (not ICD-9) for 2024+ documentation
- Use the most specific code available (5-7 characters, not shortened codes)
- Code all documented conditions that affect patient care or resource use
- Distinguish between active problems and historical diagnoses
- Add modifiers if needed (laterality, severity, episode of care)

### Step 9: Apply HIPAA & Privacy Compliance
Healthcare documentation must protect patient privacy.

**HIPAA Compliance Checklist**:

- [ ] **Access**: Only necessary personnel access records (need-to-know basis)
- [ ] **Encryption**: Records transmitted securely (HTTPS, encrypted email, secure fax)
- [ ] **Authentication**: Only authorized users can log in and view records (password-protected)
- [ ] **Audit trails**: System logs who accesses records and when
- [ ] **Data minimization**: Document only what's clinically necessary; avoid unnecessary sensitive info
- [ ] **Patient rights**: Patient has right to access their record within 30 days
- [ ] **Breach notification**: If records are accidentally disclosed, notify patient within 60 days
- [ ] **Business associates**: Any third parties processing data (EHR vendors, billing) have Business Associate Agreements (BAAs)

**What NOT to document**:
- Substance use disorders (unless clinical necessity; those records have additional protections under 42 CFR Part 2)
- HIV/AIDS status (separate protections)
- Mental health records (sensitive; limit access)
- Genetic information (sensitive; limit access)
- Assumptions or speculative notes ("Patient probably uses drugs", "Likely psychiatric problem")

### Step 10: Quality & Legibility Checklist
Before finalizing documentation:

- [ ] **Timeliness**: Written during or immediately after encounter (not hours or days later)
- [ ] **Legibility**: Typed or clearly handwritten; no corrections by scribbling over (use cross-through or note "error, see addendum")
- [ ] **Completeness**: All sections of required format are addressed (S, O, A, P for office visits)
- [ ] **Accuracy**: Facts match clinical findings; no copy-paste from prior visits unless still accurate
- [ ] **Specificity**: Not vague ("patient better", "follow-up as needed"). Specific outcomes and next steps.
- [ ] **Relevance**: Includes clinically pertinent info; doesn't include irrelevant social gossip
- [ ] **Objectivity**: Findings are objective, not judgmental ("patient was pleasant" vs. "alert and oriented x3")
- [ ] **Authentication**: Signed and dated by provider; note if dictated by provider and signed by another
- [ ] **Coding accuracy**: ICD-10 codes and CPT codes (if billing-relevant) are correct and specific

## Output Template

```
---
CLINICAL DOCUMENTATION
Patient: [Name] | MRN: [#] | DOB: [Date]
Visit Date: [Date/Time]
Provider: [Name, credentials]
---

# [SOAP NOTE / DISCHARGE SUMMARY / CARE PLAN]

## SUBJECTIVE

Chief complaint: [Patient's stated reason for visit]

History of present illness:
[Detailed timeline of current illness]

Relevant PMH: [Medical/surgical history relevant to chief complaint]

Medications: [List with doses and frequency]

Allergies: [Drug and reaction type]

Social: [Smoking, alcohol, living situation, occupational exposure if relevant]

## OBJECTIVE

Vital signs: [All four plus O2 saturation]

Physical exam:
[By body system or area of complaint; specific findings]

Labs/imaging:
[Results with dates]

## ASSESSMENT

[Primary diagnosis with ICD-10 code]
[Justification based on S + O]
[Differential diagnoses if relevant]

## PLAN

[Treatment/medication plan]
[Patient education provided]
[Follow-up timeline]
[Referrals if applicable]
[Red flags for return]

---

SIGNED: [Provider name, credentials]
DATE/TIME: [Timestamp]
```

## Quality Gates

1. **Specificity Test**: Could this note apply to 10 different patients with the same diagnosis? If yes, it's too generic. Rewrite with patient-specific details.

2. **Legality Check**: Could this note defend against a malpractice claim? Does it show you did a thorough evaluation and had sound reasoning for your plan? If sparse or unclear, strengthen it.

3. **ICD-10 Accuracy**: Are codes specific and correct? Test by reading the code description aloud; does it match what you documented?

4. **Timeliness Verification**: Is the note written during or immediately after the encounter? Delayed documentation (days later) is less defensible and may compromise accuracy.

5. **Completeness**: Does the note address all four SOAP sections? If any section is missing, note why (e.g., "No surgery history offered").

## Examples

### Good Clinical Documentation

**S**: "Patient presents with 3-day history of productive cough, fever up to 101.5F, and dyspnea. Cough productive of yellow-green sputum. No hemoptysis. Denies recent illness or travel. Lives with 2 young children; attends community gym. Smokes 1 pack/week. Goals: get better quickly; needs to return to work in 2 days."

**O**: "Vitals: BP 128/74, HR 88, RR 18, T 99.2F, O2 97% RA. Lungs: Dullness to percussion and egophony over right lower lobe; crackles in RLL. Heart: RRR, no murmurs. Labs: CXR shows right lower lobe infiltrate; WBC 13.2 (elevated)."

**A**: "Community-acquired bacterial pneumonia, right lower lobe (J15.9). Patient presents with classic signs (fever, productive cough, dyspnea) and confirms with infiltrate on CXR and elevated WBC. No sepsis (BP and HR stable)."

**P**: "Start Amoxicillin 500mg PO TID x 7 days. Discussed side effects (GI upset, rash). Advised to rest, hydrate, avoid strenuous exercise until symptoms resolve. If fever persists >48 hours on antibiotics or worsens, return to clinic or go to ER. Follow-up in 1 week to recheck lungs and confirm resolution."

**Why it works**: Specific findings; clinical reasoning clear; plan is actionable with follow-up.

### Bad Clinical Documentation

**S**: "Patient has a cough."
**O**: "Lungs: Some crackles."
**A**: "Pneumonia."
**P**: "Antibiotics. Follow up as needed."

**Why it fails**: Not specific enough. Doesn't note severity, duration, or patient context. Doesn't explain why you think it's pneumonia (no CXR mentioned). Plan is vague ("as needed").

## Common Mistakes

1. **Copy-paste from prior visits**: Easy to do; dangerous if prior documentation was wrong or situation changed. Review prior note and update; don't just repeat.

2. **Vague objective findings**: "Lungs clear" may not be accurate. Better: "Lungs: Clear to auscultation bilaterally, no wheezes, rhonchi, or crackles."

3. **Assumptions in assessment**: "Patient is drug-seeking" without evidence. Instead, document what you observe: "Patient requesting opioids despite adequate non-opioid pain control; discussed addiction risk; offered alternative management."

4. **Missing plan specifics**: "Reduce stress" is not actionable. Better: "Referred to stress management class at [location]; provided resources for meditation app; advised 30-min daily walk."

5. **Documenting in retrospect**: Waiting until end of shift to write visit notes hours later. Recollection fades; accuracy suffers. Document during or immediately after encounter.

6. **Wrong ICD-10 codes**: Using codes that don't match documentation. Leads to billing denials and creates record inaccuracy. Double-check code descriptions.

## Anti-Patterns

1. **The dissertation approach**: 2-page note for a routine follow-up. Efficiency matters. Document sufficiently; don't over-document.

2. **Medico-legal paranoia**: Over-defensive documentation ("Patient denies every possible symptom...") that reads unnatural and may itself create liability (looks like you're hiding something).

3. **Ignoring patient context**: Documentation focuses on disease, ignores patient's life (job stress, childcare, financial constraints) that affect adherence and outcomes. Include relevant social context.

4. **Coding to the dollar**: Choosing codes or documentation to maximize billing rather than to reflect truth. This is fraud. Code what you documented; document what you found.

5. **Inconsistency between notes**: Vitals in nursing note don't match physician note. Inconsistencies create doubts and liability. Verify data before signing.
