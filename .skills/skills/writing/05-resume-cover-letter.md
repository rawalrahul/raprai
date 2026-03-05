---
name: resume-cover-letter
description: "Generate ATS-optimized resumes and tailored cover letters. Extracts job-description keywords, transforms achievements with STAR→CAR method, uses ATS-safe formatting, and aligns every claim to job requirements."
category: writing
difficulty: intermediate
model_boost: "Weak models produce generic resumes that don't match job descriptions, overuse vague achievement language, include non-ATS-friendly formatting, miss keyword alignment, and write cover letters that sound generic or desperate."
---

# Resume & Cover Letter Writer

## Purpose
Get interviews by aligning resume and cover letter to job requirements at both human and machine level. ATS (Applicant Tracking System) filters 75% of applications before humans read them; passing the ATS filter requires keyword matching, clean formatting, and section structure that parsers expect. For humans, cover letters must prove understanding of the specific role and company, not generic interest.

## When to Use
- Creating or updating resumes for job applications (ATS optimization critical)
- Tailoring resume and cover letter to specific job postings (keyword matching)
- Transitioning to a new industry or role (reframing experience into relevant language)
- Rebuilding resume after employment gap (addressing with context, not hiding)
- Developing cover letters that move past the opening filter
- **Do NOT use when**: Writing LinkedIn profiles (use separate skill), academic CVs, or government forms with specific formatting requirements

## Instructions

### Step 1: Extract Job Requirements & Build Keyword Map
Copy full job description and identify: (a) hard skills (languages, tools, frameworks), (b) soft skills (leadership, communication), (c) domain knowledge (industry, process), (d) certifications or education, (e) experience (years, levels). Create a keyword map: for each requirement, note: exact phrase from job posting, how you've done it, how you'll phrase it in resume. Example: Job says "Led cross-functional teams" → you say "Managed 12-person product team across engineering, design, marketing" (more specific, answers implied "how many" and "which functions").

### Step 2: Audit Current Resume Against Job Posting
Compare resume bullets to job posting, section by section. Score each bullet 1-5: 5 = directly matches job requirement, 1 = irrelevant. Rewrite all 1-3 bullets to map to job posting language. Do not add fake experience. Do reframe existing experience: "Improved process efficiency" (generic) → "Reduced on-boarding time by 6 weeks (35% improvement) for 150+ new hires" (maps to job's "scalable systems" requirement). Replace any bullet that doesn't serve this job posting.

### Step 3: Transform Achievements with STAR→CAR Framework
STAR (Situation-Task-Action-Result) is interview language. CAR (Challenge-Action-Result) is resume language (shorter, punchier). Convert: "Led the development of a new customer segmentation system that improved campaign accuracy" becomes "Designed customer segmentation algorithm, improving campaign targeting accuracy by 31% and reducing wasted ad spend by $200K/year." Include specific metric (31%, $200K) and business impact (wasted spend), not just activity. Each bullet = one achievement with impact. Avoid: "Responsible for", "Helped with", "Worked on" (passive language). Use: "Led", "Built", "Designed", "Launched" (active).

### Step 4: Optimize Resume for ATS Parsing
ATS parsers read text linearly; they miss graphics, fancy formatting, and columns. Use: single column layout, standard fonts (Arial, Calibri, sans-serif), clear section headers in order (Contact → Summary/Profile → Experience → Education → Skills), no tables or images, no PDF if posting system is outdated (submit .docx unless required otherwise). For section order: put most relevant section first (if you're career-changing, education before experience if it's more relevant). Keywords should appear in: Experience bullets (5-7 total), Skills section (organized by category), Summary (if included). Avoid: stylized headers, color, icons, graphics.

### Step 5: Write Skills Section with Category-Based Organization
Instead of one long list, organize by category (matching job posting language): "Frontend: React, Vue, CSS3, JavaScript" | "Backend: Node.js, Python, PostgreSQL" | "Tools: Docker, Kubernetes, Git". This signals expertise depth and helps ATS parsing. Include certifications as separate bullet. Order categories by importance to job posting (Frontend first if Frontend-heavy role). Keep skills section to 12-15 skills maximum; prioritize role-critical skills.

### Step 6: Create Tailored Cover Letter with Proof, Not Pleading
Cover letter template: (1) Open with specific detail about the company or role (not "I'm excited about..."). Example: "Your launch of the B2B marketplace last month sparked three ideas..." (2) Name one specific requirement from the job posting and prove you've done it with a metric. "You need someone who's led teams through scale-ups; I grew my team from 3 to 12 people while keeping velocity steady (2-week sprint cycles maintained)." (3) Reference company mission/culture if genuine, with one sentence max. (4) Close with low-friction CTA: "I'd welcome a conversation about how my background can help. You can reach me at [email/phone]." Keep to 250-300 words (1 page, 3-4 short paragraphs).

## Output Template

### Resume
```
{{FIRST NAME}} {{LAST NAME}}
{{CITY, STATE}} | {{PHONE}} | {{EMAIL}} | linkedin.com/in/{{profile}}

PROFESSIONAL SUMMARY (Optional, only if relevant to target role)
{{1-2 sentences connecting your experience to the job you're applying for. Example: "Product manager with 7 years scaling SaaS from $0 to $20M ARR. Expertise in onboarding, retention, and team building."}}

EXPERIENCE

{{COMPANY NAME}} | {{LOCATION}} | {{START}} – {{END}}
{{JOB TITLE}}

- {{CAR bullet with metric: Challenge, Action, Result. Lead with impact, not task.}}
- {{CAR bullet with metric}}
- {{CAR bullet with metric}} (5-7 bullets per role, tailored to job posting)

{{PREVIOUS COMPANY}} | {{LOCATION}} | {{START}} – {{END}}
{{JOB TITLE}}

- {{CAR bullets}}

EDUCATION

{{DEGREE}}, {{MAJOR}}
{{University}}, {{Graduation Year}}

SKILLS

{{Category 1}}: {{Skill 1}}, {{Skill 2}}, {{Skill 3}}
{{Category 2}}: {{Skill 1}}, {{Skill 2}}, {{Skill 3}}

CERTIFICATIONS
{{Certification Name}}, {{Issuer}}, {{Year}}
```

### Cover Letter
```
{{Date}}

Dear {{Hiring Manager Name}} (if unknown: "Hiring Team"),

{{Specific detail about company or role}} I'm writing because {{specific reason this role aligns with your experience}}.

In your job posting, you noted the need for someone who {{one specific requirement}}. In my current role at {{Company}}, I {{proof of doing this with metric}}. {{One sentence on how this achievement matches their need}}.

What drew me to {{Company}} is {{genuine company mission/culture point, max 1 sentence}}. I'd welcome a conversation about how my background in {{key relevant skill}} can help {{specific business outcome}}.

You can reach me at {{phone}} or {{email}}.

Best regards,
{{Your Name}}
```

## Quality Gates

- [ ] Resume is single-column layout with standard fonts (Arial/Calibri); no graphics, colors, or tables
- [ ] Job description analyzed: keywords extracted and matched to resume bullets (5+ keyword matches visible)
- [ ] Every bullet uses CAR format (Challenge-Action-Result) with specific metric; no passive language ("Responsible for", "Helped")
- [ ] First achievement bullet in current role directly matches primary job requirement
- [ ] Skills section organized by category (not one long list); role-critical skills listed first
- [ ] Experience section bullets reframed to match job posting language and priority (not generic achievement language)
- [ ] Cover letter opens with specific detail about company/role (not generic "I'm excited")
- [ ] Cover letter includes one specific requirement from job posting + proof with metric
- [ ] Cover letter under 300 words; 3-4 short paragraphs; ends with low-friction CTA
- [ ] No achievements included that don't serve the target role; every section calibrated to this posting

## Examples

### Good Resume Output (Excerpt - Software Engineer Role)

**EMMA CHEN**
Seattle, WA | (206) 555-0123 | emma.chen@email.com | linkedin.com/in/emmachen

**PROFESSIONAL SUMMARY**
Full-stack engineer with 6 years building scalable SaaS products. Proven expertise in leading backend migrations, optimizing database query performance, and mentoring junior engineers.

**EXPERIENCE**

**Stripe** | San Francisco, CA | 2021 – Present
**Senior Backend Engineer**

- Architected microservices migration for payment processing pipeline, reducing deployment time from 45 min to 8 min (82% improvement) and enabling daily releases vs. weekly; supported $150M+ in new payment volume
- Mentored 4 junior engineers, 2 promoted to mid-level; established peer code review process improving defect detection by 40%
- Optimized PostgreSQL queries for customer dashboard, reducing p95 latency from 1.2s to 240ms (80% improvement); impacted 50K+ daily active users
- Led on-call rotation for critical payment systems, maintaining 99.99% uptime SLA across 8M+ daily transactions

**TechStartup** | Seattle, WA | 2018 – 2021
**Backend Engineer**

- Built real-time analytics pipeline processing 500K+ events/day using Node.js and Redis; enabled product team to ship personalization features, increasing user retention by 15%
- Designed and implemented API authentication system securing 2M+ user accounts; zero breaches, SOC 2 compliance achieved
- Reduced database costs by 35% through query optimization and connection pooling; saved company $80K annually

**EDUCATION**

**B.S. Computer Science**
University of Washington, 2018

**SKILLS**

Backend: Node.js, Python, PostgreSQL, Redis, Microservices Architecture
DevOps: Docker, Kubernetes, AWS (RDS, Lambda, EC2)
Databases: SQL optimization, database migration, replication

**CERTIFICATIONS**
AWS Certified Solutions Architect - Associate, 2022

---

**Analysis (for a Senior Backend Engineer role at a Scale-up):**
- Opens with summary clearly positioning candidate for senior backend role
- CAR format throughout: "Architected microservices migration" (challenge implicit: slow deploys) + "reducing deployment time from 45 min to 8 min" (action, metric) + "enabled daily releases" (result, business impact)
- Keywords from job posting (microservices, optimization, mentoring) appear in bullets
- Metrics throughout: 82%, 80%, 40%, 15%, 99.99%, $80K
- Skills organized by category (Backend, DevOps, Databases)
- Most recent role listed first with most relevant company (Stripe)
- Specific impact: "50K+ daily active users", "$150M+ payment volume" (shows scale)

### Bad Resume Output (What to Avoid)

**JOHN SMITH**
john@email.com | (555) 555-1234

**OBJECTIVE**
Seeking a challenging position in software engineering where I can use my skills and contribute to a dynamic team.

**EXPERIENCE**

**Tech Company Inc.** | 2020 – Present
**Software Engineer**

- Responsible for backend development and maintenance
- Worked on various projects related to database optimization
- Helped improve system performance
- Collaborated with product team
- Used Node.js and Python in daily work

**Previous Job** | 2018 – 2020
**Junior Developer**

- Developed features for web applications
- Fixed bugs in existing code
- Participated in code reviews
- Worked with SQL databases

**EDUCATION**
BS in Computer Science, State University, 2018

**SKILLS**
Programming Languages: JavaScript, Python, Java, C++, Ruby
Databases: MySQL, PostgreSQL
Other: Git, AWS, Docker

---

**Issues Identified:**
- Objective is generic and self-focused (not about the employer or role)
- Passive language throughout: "Responsible for", "Worked on", "Helped", "Participated in" (weak verbs)
- No metrics or specific impact: "improved system performance" (how much? what was the business impact?)
- No CAR format; bullets are vague activity descriptions, not achievements
- Irrelevant skills listed (Java, C++, Ruby) if role is Node/Python focused
- No detail on scale: how many users? how much data? how much time saved?
- Dates but no specific timeframe ("Present" is unclear)
- Company name generic ("Tech Company Inc.")
- No keyword matching to target job posting

### Good Cover Letter Output (Excerpt)

Dear Sarah,

I was excited to see Stripe's engineering blog post last month on reducing API latency at scale—your approach to connection pooling was exactly what I implemented at my current role, cutting response times by 80% for our 50K+ daily users.

You're looking for a Senior Backend Engineer who's led platform migrations and mentored engineers. At Stripe's payment team, I architected our microservices migration, reducing deployment time from 45 min to 8 min and enabling the team to ship daily. I've also mentored 4 engineers, two of whom were promoted to mid-level, by establishing a peer code review process that improved defect detection by 40%.

What excites me about Stripe is your commitment to making payments infrastructure invisible to developers—I've lived that problem firsthand and want to help solve it at scale.

I'd welcome a conversation about how my background in microservices and team leadership can help your platform team. You can reach me at (206) 555-0123 or emma.chen@email.com.

Best,
Emma Chen

---

**Analysis:**
- Opens with specific detail (Stripe's engineering blog post on latency) → proves homework, not generic interest
- Second paragraph: names specific job requirement ("led platform migrations and mentored engineers") + proof with metrics (45→8 min, 40% improvement, 4 engineers mentored)
- Mentions company mission naturally (not forced)
- CTA is low-friction ("I'd welcome a conversation") and provides contact info
- ~250 words, 3 short paragraphs, conversational tone

### Bad Cover Letter Output (What to Avoid)

Dear Hiring Manager,

I am writing to express my strong interest in the Software Engineer position at your company. I have always been passionate about technology and solving problems through code. I believe I would be a great fit for your team.

I have several years of experience in software development and have worked on many projects. I am skilled in various programming languages and databases. I am a quick learner and work well in team environments. I am very excited about the opportunity to join your company and contribute my skills.

I think your company does great work and I would love to be part of it. I look forward to hearing from you and discussing how I can be valuable to your organization.

Sincerely,
John Smith

---

**Issues Identified:**
- Generic opening with no specific detail about company or role
- Vague language: "always been passionate", "great fit", "skilled in various"
- No connection between their needs and candidate's experience
- No metrics or specific achievements
- No understanding of what the company does (just says "great work")
- Weak CTA ("I look forward to hearing from you")
- Sounds like template sent to dozens of companies
- 200+ words but no substance

## Common Mistakes

1. **Mistake**: Listing responsibilities instead of achievements ("Responsible for database management")
   → **Fix**: CAR format with impact metric. "Optimized database queries, reducing p95 latency by 65% and supporting 2M+ daily users" (challenge + action + result + scope).

2. **Mistake**: Skills list is one long, unsorted list that ATS can't parse well
   → **Fix**: Organize by category (Backend, Frontend, DevOps, etc.). Candidates with category-organized skills rank higher in ATS systems.

3. **Mistake**: Cover letter doesn't reference the actual company or role (could be sent to anyone)
   → **Fix**: Open with specific detail about their company, product, or recent news. "Your launch of X feature..." or "Your blog post on Y...".

4. **Mistake**: Resume uses fancy formatting (columns, icons, colors) that ATS can't parse
   → **Fix**: Single column, standard fonts, clear headers. Formatting disappears in ATS parsing; content and keywords are all that matter.

5. **Mistake**: Achievements don't connect to job posting requirements
   → **Fix**: Before writing bullet, check if it matches a job requirement. If not, replace it with an achievement that does.

## Anti-Patterns

- **Never** use passive language ("responsible for", "helped with", "worked on"). Every bullet should start with a strong active verb (Led, Built, Designed, Optimized, Reduced, Increased, Migrated).
- **Never** list skills irrelevant to the target role. If applying for a Python backend role, omit C++, Ruby, and Java even if you know them. Focus is better than breadth.
- **Never** write cover letters without referencing the specific company. Generic letters get deleted. Prove you did 10 minutes of homework.
- **Never** include achievements that don't have metrics. "Improved performance" is weak; "reduced latency by 65%" is strong. Numbers prove impact.
- **Never** use percentages or big numbers without context. "Increased by 200%" → for what scale? To how many people? Context matters.
