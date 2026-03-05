---
name: word-report-builder
description: "Build professional reports in Word with auto-generated TOC, executive summary, proper heading hierarchy, and consistent formatting. Use when asked to 'write a report' or 'create a formal document'."
category: office
difficulty: beginner
model_boost: "Fixes weak reports: missing TOC, broken heading hierarchy, inconsistent styles, executive summary that's too long or too detailed."
---

# Word Report Builder

## Purpose
Structure formal reports in Word so they're readable, scannable, and professional. This skill sets up heading hierarchy (H1/H2/H3), auto-generates a table of contents, enforces consistent styles, and writes executive summaries that actually summarize. A well-structured report lets busy readers find what matters in 60 seconds.

## When to Use
- "Write a report on [topic]"
- "Create a formal business document"
- "I need an executive summary" (as part of a larger report)
- **Do NOT use when**: Writing a proposal (use 105-word-proposal-template); writing a policy doc (use 112-word-policy-document); or just writing an email

## Instructions

### Step 1: Document Setup and Styles
Start every report with proper styles before writing content.

**Set Default Font and Margins**
1. Home → Styles (Styles pane on right)
2. Right-click Normal → Modify
3. Font: Calibri or Arial, 11pt, color black
4. Paragraph: Line spacing 1.15, spacing after paragraph 6pt
5. OK

Set margins: Layout → Margins → Normal (1" all sides)

**Establish Heading Styles (Never Skip)**
Custom styles ensure TOC works and document stays scannable.

In Styles pane:
- **Heading 1** (Main sections): Calibri Bold 14pt, color [primary brand color or dark blue]
- **Heading 2** (Subsections): Calibri Bold 12pt, color [darker shade]
- **Heading 3** (Sub-subsections): Calibri Bold 11pt, color black

Mark each as "Apply formatting to paragraphs with this style" (not character style).

**Title Style**
- Font: Calibri Bold 18pt
- Spacing before: 0pt, after: 12pt
- Center alignment
- Apply only to title on page 1

### Step 2: Front Matter (Title Page)
Create a professional first impression.

**Title Page Structure** (Page 1)
```
[Blank line]
[Blank line]
[REPORT TITLE in Title style, center]
[Blank line]
[Subtitle if applicable, center, italics, 12pt]
[Blank line]
[Blank line]
[Blank line]
[Prepared by: Author Name]
[Date: Month DD, YYYY]
[Organization/Department]
```

**Optional Elements** (for formal reports)
- Client/Stakeholder name
- Project code
- Version number (v1.0, v2.1, etc.)
- Confidentiality stamp (CONFIDENTIAL, INTERNAL USE ONLY)

**Page Break**
After title page, insert Page Break: Ctrl+Enter (starts TOC on new page)

### Step 3: Table of Contents (Auto-Generated)
Never type TOC manually; Word generates it from headings.

**Insert TOC**
1. Cursor on page after title (page 2)
2. References → Table of Contents → Automatic Table
3. Choose style (typically "Automatic Table 2" looks professional)
4. Word generates TOC based on Heading 1, 2, 3 styles

**Update TOC Before Finalizing**
After writing content:
1. Right-click TOC
2. Update Field
3. Word recalculates page numbers and entries

**TOC Best Practice**
- Show Heading 1 and 2 only (omit Heading 3 to avoid clutter)
- Right-click TOC → Properties → select "Show levels: 2" (or customize)

### Step 4: Executive Summary (250 words max)
The executive summary is often the only thing busy leaders read.

**Structure Formula** (Problem → Finding → Recommendation)
1. **Problem** (1-2 sentences): What situation prompted this report?
   - Example: "Annual customer churn increased 12% year-over-year, from 8% to 9%, driven primarily by enterprise segment defection."

2. **Finding** (2-3 sentences): What data/analysis did you do? What did you discover?
   - Example: "Analysis of 247 churned customers revealed three primary reasons: (1) Product feature gaps (31%), (2) Customer support quality (28%), (3) Pricing competitiveness (24%). Enterprise customers cited feature gaps 2x more often than SMB."

3. **Recommendation** (1-2 sentences): What action should the audience take?
   - Example: "We recommend a three-month product roadmap update addressing the top 5 missing features, combined with a customer success program review to improve support quality."

**Format**
- 150–250 words (one page maximum)
- Bullet points optional (keep prose paragraphs for flow)
- Include key metrics/numbers (not vague language)
- Do NOT deep-dive or explain methodology (that's in the body)

**Bad vs Good Examples**
- Bad: "This report examines many aspects of the customer situation and provides analysis." (Vague, no insight)
- Good: "3 of 5 churned enterprise customers cited missing API capabilities; rebuilding the integration roadmap is the highest-ROI fix." (Specific, actionable)

### Step 5: Body Structure (Section Hierarchy)
Use Heading 1 → Heading 2 → Heading 3. Never skip levels.

**Main Sections** (Heading 1)
Organize by logical flow, not chronology:
1. **Executive Summary** (H1) — already written
2. **Introduction/Background** (H1) — context and scope
3. **Methodology** (H1) — how you gathered/analyzed data (if needed)
4. **Findings** (H1) — your analysis results
5. **Recommendations** (H1) — what to do next
6. **Conclusion** (H1) — final thoughts
7. **Appendix** (H1) — supporting data

**Subsections** (Heading 2 under each H1)
Example under **Findings**:
- Market Size and Growth
- Competitive Landscape
- Customer Preferences

Example under **Recommendations**:
- Short-Term Actions (0–3 months)
- Medium-Term Actions (3–12 months)
- Long-Term Strategic Initiatives

**Sub-subsections** (Heading 3, use sparingly)
Reserve for detailed breakdowns, 3–4 levels deep max.

**Content Rules**
- Each section: 0.5–2 pages (readers skim; too long loses attention)
- Introduce section with 1–2 sentences before diving into subsections
- End section with a summary or transition (e.g., "These findings point to three key recommendations, outlined below.")

### Step 6: Numbering, Figures, and Tables
Professional documents auto-number and reference figures/tables.

**Figure and Table Numbering**
Never hardcode "Figure 1" or "Table 2". Use captions and auto-numbering.

For charts/images:
1. Insert chart/image in document
2. Right-click image → Insert Caption
3. Caption dialog: Label "Figure", Position "Below selected item"
4. Word generates "Figure 1: Description of Figure"
5. Word auto-increments as you add more figures

For tables:
1. Insert → Table
2. After table, right-click → Insert Caption
3. Label "Table", Position "Above selected item"
4. Word generates "Table 1: Description"

**Cross-References**
Instead of typing "See Figure 3", use auto-link:
1. Insert → Cross-reference → Reference type "Figure"
2. Select "Figure 3: Growth Trend"
3. Word inserts linked reference; if you move figures, links update

**In-Text References**
- First mention: "Figure 1 shows quarterly revenue growth."
- Subsequent mentions: "As shown in the figure above..."

### Step 7: Page Numbering (Formatting Matters)
Formal reports use different numbering for front matter (i, ii, iii) and body (1, 2, 3).

**Front Matter (i, ii, iii...)**
Pages 1–2 (title and TOC) typically don't show numbers, but if they do, use Roman numerals.

**Body Pages (1, 2, 3...)**
After TOC, reset numbering to Arabic.

**Implementation**
1. On the page after TOC (start of body content), Insert → Page Break
2. On that new page, Insert → Header & Footer → Page Number
3. Choose position (bottom center is standard)
4. Right-click page number → Format Page Numbers → Start at 1
5. Check "Different first page" if title page shouldn't show a number

### Step 8: Header and Footer Design
Consistent headers/footers reinforce document branding.

**Header Content** (appears at top of every page)
- Left: Organization name or document title
- Center: blank (or current section title using field codes)
- Right: blank (or date)

Example header: "Acme Corp | Product Strategy Report | March 2024"

**Footer Content** (appears at bottom of every page)
- Left: Department/author name
- Center: Page number
- Right: Date or confidentiality status

**How to Insert**
1. Insert → Header & Footer → Header
2. Type your header (or use fields: Insert → Quick Parts → Fields)
3. Tab to move between left/center/right sections
4. Repeat for Footer
5. Check "Different first page" to hide header/footer on title page

**Field Codes** (dynamic information)
- Page number: Insert → Quick Parts → Field → Page
- Date: Insert → Quick Parts → Field → Date
- These update automatically

### Step 9: Appendix Organization
Appendices contain supporting data, not required for understanding.

**Structure**
- Each appendix = one topic
- Number them: Appendix A, Appendix B, etc.
- Start each on a new page

**Common Appendix Types**
- Appendix A: Detailed Methodology (surveys, sampling, statistical tests)
- Appendix B: Raw Data Tables (too detailed for main body)
- Appendix C: Interview Transcripts or Case Studies
- Appendix D: Technical Documentation
- Appendix E: Glossary of Terms

**Reference Them**
In body: "See Appendix A for detailed methodology."

**Table of Contents for Appendices**
TOC should include appendix headings if you want readers to jump directly to them.

### Step 10: Citations and Bibliography
If you reference external sources, cite them consistently.

**Footnote vs Endnote**
- **Footnote**: Appears at bottom of page (easier to read in context)
- **Endnote**: Appears at end of document (cleaner layout, harder to find)

**Insert Citation**
1. References → Manage Sources
2. Add new source: title, author, URL, publication date
3. In document, place cursor after statement
4. References → Insert Citation → choose source
5. Word adds footnote/endnote with citation

**Bibliography Page**
1. After appendices, insert new page: Ctrl+Enter
2. Heading: "Bibliography" or "References" (H1)
3. References → Bibliography → choose style (APA, MLA, Chicago)
4. Word auto-generates alphabetical list

## Output Template
```
# {{REPORT TITLE}}

## Document Metadata
- **Prepared by**: {{Author Name}}
- **Date**: {{Month DD, YYYY}}
- **Version**: {{v1.0}}
- **Audience**: {{Target readers: e.g., "Executive leadership", "Board of directors"}}
- **Confidentiality**: {{CONFIDENTIAL | INTERNAL | PUBLIC}}

## Table of Contents
(Auto-generated; update before finalizing)

---

## Executive Summary
{{Problem (1–2 sentences)}}
{{Finding (2–3 sentences)}}
{{Recommendation (1–2 sentences)}}
{{~250 words max}}

## Introduction
{{Scope, background, why this report matters}}

## Findings
### Key Finding 1: {{Insight}}
{{Supporting data and analysis}}

### Key Finding 2: {{Insight}}
{{Supporting data and analysis}}

## Recommendations
### Short-Term (0–3 months)
- {{Action}} ({{owner}}, {{timeline}})
- {{Action}} ({{owner}}, {{timeline}})

### Long-Term (6–12 months)
- {{Action}} ({{owner}}, {{timeline}})

## Conclusion
{{Final synthesis; connection back to opening problem}}

## Appendix A: Methodology
(Technical details, survey samples, statistical notes)

## Appendix B: Raw Data
(Supporting tables, detailed results)
```

## Quality Gates
- [ ] Heading hierarchy is correct: H1 → H2 → H3 (never skip a level)
- [ ] Table of Contents auto-generates from headings (test: update TOC, verify page numbers)
- [ ] Executive summary is ≤250 words and follows Problem → Finding → Recommendation structure
- [ ] Page numbering is correct: Front matter (Roman) and body (Arabic 1, 2, 3...)
- [ ] Header/footer consistent on all pages (no title page, different formatting on body)
- [ ] Figures and tables are auto-captioned and referenced (no hardcoded "Table 1")
- [ ] All sections advance the argument (no tangential content)
- [ ] No single section exceeds 2 pages (readers lose focus)

## Examples

### Good Output (excerpt)
```
[Title Page]
CUSTOMER CHURN ANALYSIS: 2024 FINDINGS AND ROADMAP
Prepared by: Jane Doe, Product Strategy
March 15, 2024
Version 1.0

[Page 2: TOC auto-generated]
1. Executive Summary .......................... 1
2. Introduction ............................... 2
3. Findings ................................... 3
4. Recommendations ............................ 5
5. Appendix A: Methodology ................... 7

[Page 3: Executive Summary]
In 2024, customer churn increased 12% year-over-year (8% → 9%),
affecting enterprise customers disproportionately (+18%). Analysis
of 247 churned accounts revealed feature gaps (31%), support quality
(28%), and pricing (24%) as primary drivers. We recommend prioritizing
a 3-month product roadmap to address top 5 missing features, yielding
estimated $2.1M annual revenue recovery.

[Page 5: Findings → Key Finding 1]
Enterprise Customers Drive Churn Increase
Figure 1 shows churn by segment. Enterprise churn grew from 6% to 7.1%
(18% increase), while SMB churn remained stable at 9.5%. This suggests
a product-market fit issue specific to enterprise requirements...

[Page 7: Appendix A: Methodology]
This analysis surveyed 247 randomly selected churned customers across
customer segments. Interviews averaged 15 minutes; response rate was 68%.
Survey questions (attached) covered product, support, and pricing satisfaction...
```

### Bad Output (what to avoid)
```
[No title page; report starts with generic "Report"]
[No TOC, or manual TOC with wrong page numbers]
[Executive summary is 3 paragraphs, vague: "We analyzed data and found insights"]
[Sections titled "Details 1", "Details 2", "Section 4" (no narrative structure)]
[Heading hierarchy: H1 → H3 (skipped H2), confusing outline]
[Figures hardcoded as "Figure 1:" with manual numbering; if you move figures, numbering breaks]
[Page numbers: Title page shows "1", then jumps to "1" again on body (numbering error)]
[All content 10+ pages of dense text, no subsections (unreadable)]
[Appendix has no structure; just "Raw Data" with 50 tables, no labels]
```

## Common Mistakes

1. **Mistake**: Heading hierarchy is broken (H1 → H3, skipping H2).
   → **Fix**: Always H1 → H2 → H3 in order. This is how auto-TOC works. Skipping breaks the outline.

2. **Mistake**: Executive summary is 2 pages long and includes detailed methodology.
   → **Fix**: Executive summary is ≤250 words and covers ONLY Problem-Finding-Recommendation. Methodology goes in appendix.

3. **Mistake**: Page numbering shows on title page; or numbering resets mid-document.
   → **Fix**: Use "Different first page" to hide number on title, then Insert → Page Number → Format → Start at 1 after TOC.

4. **Mistake**: Table of Contents is typed manually ("1. Intro... page 3").
   → **Fix**: Use References → Table of Contents. Word auto-generates from heading styles and updates when you edit.

5. **Mistake**: Figures are numbered manually ("Figure 1", "Figure 2"). When you move figures, numbering breaks.
   → **Fix**: Use captions: right-click image → Insert Caption → Word auto-numbers.

## Anti-Patterns
- Never skip heading levels. (H1 → H2 → H4 confuses the outline and breaks auto-TOC.)
- Never write the TOC manually. (Auto-generation is the whole point; manual breaks on first edit.)
- Never put "everything" in the body and nothing in appendices. (Appendices are for support; body is for argument.)
- Never exceed 2 pages per section. (Readers skim; long sections lose them.)
- Never write an executive summary that's vague or too long. (It's a summary, not a deep dive.)
- Never use different fonts/styles for each section. (Consistency signals professionalism.)
