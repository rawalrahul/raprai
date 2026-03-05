---
name: office-template-system
description: "Build cross-Office template and style guide system: brand colors, fonts, logos, consistent headers/footers, chart styles. Use to standardize all Word/PowerPoint/Excel documents."
category: office
difficulty: intermediate
model_boost: "Fixes inconsistent Office documents: different colors per file, misaligned logos, no style standards, look amateurish."
---

# Office Template System

## Purpose
Create a unified design system for all Office documents (Word, PowerPoint, Excel) so every presentation, report, and dashboard looks professionally consistent. This skill defines brand colors, typography hierarchy, logo placement rules, header/footer standards, chart color schemes, table styling, file naming conventions, and template distribution. Consistency signals professionalism and builds brand trust.

## When to Use
- "Create company style guide" for Office documents
- "Standardize PowerPoint" across presentations
- "Build templates" that all teams use
- "Establish brand guidelines" for internal communications
- **Do NOT use when**: Designing entire brand identity (use designer/brand agency); or creating web style guide (different medium)

## Instructions

### Step 1: Brand Color Palette Definition
Define primary, secondary, and accent colors.

**Color Palette Structure**

**Primary Colors** (main brand colors; use most often)
```
Primary Blue: #0066CC (Hex) | RGB(0, 102, 204) | Pantone 292 C
  Use for: Main headings, primary buttons, emphasis
  When: Titles (PowerPoint), important headers (Word)
  Don't overuse in charts (can overwhelm)

Primary Gray: #333333 (Hex) | RGB(51, 51, 51) | Pantone 426 C
  Use for: Body text, neutral backgrounds
  When: Standard paragraph text, default font color
  Ensures: Readability and professionalism
```

**Secondary Colors** (supporting; use for variety)
```
Secondary Orange: #FF9900 (Hex) | RGB(255, 153, 0) | Pantone 1245 C
  Use for: Secondary headings, accent elements
  When: H2/H3 headings in reports; supporting elements
  Caution: Don't use for body text (hard to read)

Secondary Green: #00AA00 (Hex) | RGB(0, 170, 0)
  Use for: Positive indicators (✓, "on track")
  When: Status indicators, success states
```

**Accent Colors** (data encoding in charts; use sparingly)
```
Error Red: #DD0000 (Hex) | RGB(221, 0, 0)
  Use: Negative indicators (✗, "off track", problems)
  When: Risk flagging, underperformance

Warning Orange: #FFAA00 (Hex) | RGB(255, 170, 0)
  Use: Caution states (at risk, watch)
  When: Amber status, caution flags

Light Gray: #F5F5F5 (Hex) | RGB(245, 245, 245)
  Use: Background fills for alternating rows, subtle sections
  When: Table backgrounds, section dividers
```

**Color Accessibility**
- Test all colors for color-blind readiness (red-green combos are problematic)
- Ensure sufficient contrast (WCAG AA standard: 4.5:1 for text)
- Don't use color alone to encode meaning (pair with icons/labels: "✓ On Track" not just green)

**Color Palette Document** (create in Word or PowerPoint)
```
[Page 1: Swatches + hex codes]
[Page 2: Usage guidelines per color]
[Page 3: Color-blind simulation examples]
[Page 4: Don't-Do examples (wrong color combos)]
```

### Step 2: Typography Hierarchy
Define fonts and sizes for all text levels.

**Font Family Selection**
```
Heading Font: Calibri or Segoe UI (sans-serif)
  Why: Clean, professional, works well on screens
  Avoid: Decorative fonts (Comic Sans, Impact)

Body Font: Calibri or Segoe UI (same, ensures consistency)
  Same font throughout = cohesive look
  Variation via size and weight, not font family

Data/Table Font: Courier New or Monospace (numbers line up)
  Use only for: Numerical tables, code
  Why: Monospace aligns columns precisely
```

**Size and Weight Hierarchy** (Define for Word/PowerPoint)
```
Heading 1 (H1): 28pt, Bold, Primary Blue
  Example: "Q3 Financial Results"
  Usage: Report/presentation titles, major section headers

Heading 2 (H2): 18pt, Bold, Primary Blue
  Example: "Revenue Performance"
  Usage: Section headers, subsection titles

Heading 3 (H3): 14pt, Bold, Secondary Orange
  Example: "Enterprise Segment Growth"
  Usage: Sub-subsection headers, subsection detail

Body Text: 11pt, Regular (not bold), Primary Gray (#333333)
  Example: "Enterprise revenue grew 40% YoY due to..."
  Usage: Paragraph text, descriptions

Caption/Label: 9pt, Regular, Light Gray
  Example: "Source: Salesforce CRM, March 5, 2024"
  Usage: Chart labels, source citations, small text

Tip: Never go smaller than 9pt in printed/PDF documents (readability).
```

**Font Pairing Rules**
- Don't mix more than 2 fonts per document (chaos)
- Headings: Bold version of body font (Calibri Bold for headings, Calibri Regular for body)
- Never use more than 3 font sizes on one slide (too many hierarchies)

### Step 3: Logo and Brand Element Placement
Consistent logo placement signals professionalism.

**Logo Usage**

**Logo Versions to Create**
```
Version 1: Full Logo + Tagline (use in documents, presentations)
  Dimensions: 2" wide × 1" tall (minimum)
  File: logo_full_color.png (transparent background)

Version 2: Logo Icon Only (use in headers, footers, small spaces)
  Dimensions: 0.5" × 0.5" (minimal)
  File: logo_icon_color.png

Version 3: Logo Monochrome (for black-and-white printing)
  Dimensions: Same as Version 1
  File: logo_full_bw.png

Version 4: Logo Reversed (white on dark background)
  For: Dark-colored header/footer backgrounds
  File: logo_full_white.png
```

**Placement Rules**

**In PowerPoint**
```
Title Slide: Logo bottom-right corner, 1" × 0.5"
  Effect: Professional without overwhelming slide

Content Slides: Logo in top-right corner, 0.5" × 0.25"
  Effect: Visible but minimal; doesn't distract

Final Slide: Logo centered, larger (1" × 0.5")
  Effect: Closing statement; brand presence

Never: Logo on every single slide unless it's a brand-heavy deck
       Logo larger than content (content comes first)
```

**In Word**
```
Header: Logo top-left, 0.5" × 0.25"
  Text next to logo: Company name, document title

Cover Page: Logo bottom-center or top-right, 1" × 0.5"
  Balanced visually

Body Pages: Logo in footer (very small, 0.3" × 0.15")
  Subtle; doesn't interfere with content
```

**In Excel**
```
Dashboard Tab: Logo top-left, 0.5" × 0.25"
  Identifies company; signals professionalism

Data Tabs: No logo needed (internal use)

Printed Sheets: Logo in header or footer (0.3")
```

**Clear Space Rule** (whitespace around logo)
```
Minimum clear space = logo height
If logo is 1" tall, leave 1" empty space around all sides
Prevents other elements from crowding the logo
Applies in PowerPoint and Word
```

### Step 4: Header and Footer Standards
Consistent headers/footers across all documents.

**Header Design** (appears at top of every page)

**Standard Header** (for reports, proposals)
```
Left side: Company Logo (0.5" wide) + "Company Name"
Center: Document Title
Right side: Page number (or date, or both)

Example:
[Logo] Acme Corp     |     Q3 Financial Report     |     Page 1
───────────────────────────────────────────────────────────────
```

**Header Setup in Word**
1. Insert → Header & Footer → Header
2. Tab to move between left, center, right sections
3. Left: Insert logo (Insert → Picture) + type company name
4. Center: Insert document title field (Insert → Quick Parts → Fields → Title)
5. Right: Insert page number (Insert → Page Number)

**Footer Design** (appears at bottom of every page)

**Standard Footer** (for internal documents)
```
Left side: Department/Team
Center: [Blank or document ID]
Right side: Date (auto-updated) + Confidentiality stamp

Example:
Finance Team     |                    |     Updated: Mar 5, 2024 | CONFIDENTIAL
───────────────────────────────────────────────────────────────
```

**Different First Page** (title page may have different header/footer)
```
Check: "Different First Page" in Header & Footer options
Title page: No header/footer (optional)
Body pages: Standard header/footer shown
```

### Step 5: Chart Color Scheme
Unified colors for all data visualizations.

**Chart Color Palette** (for Excel, PowerPoint)
```
Color Sequence (use in order for multiple series):
  1. Primary Blue (#0066CC)
  2. Secondary Orange (#FF9900)
  3. Secondary Green (#00AA00)
  4. Primary Gray (#333333)
  5. Light Gray (#F5F5F5) [use sparingly]

Never use: Jet colormap, rainbow gradients, 3D effects
Better use: Consistent palette that matches brand
```

**Chart Design Rules**
```
Bar Charts: Single color for all bars (unless comparing segments)
  Example: All product revenue bars = Primary Blue
  Exception: If comparing "Plan vs. Actual", use Blue (Actual), Light Gray (Plan)

Line Charts: Max 2–3 lines; distinct colors from palette
  Example: Revenue (Blue), Margin % (Orange)
  Color-blind safe: Use distinct colors + different line styles (solid vs. dashed)

Pie/Donut Charts: Multi-color OK, but use palette
  Slices: Primary Blue, Secondary Orange, Secondary Green, Primary Gray
  Limit: ≤4 slices (more = hard to read)

Scatter Plot: One color for all points (can add color coding by category if needed)
  Default: Primary Blue
  If encoding by category: Use palette colors (one per category)

Heatmap/Matrix: Use gradient (light to dark)
  Example: Light (low value) → Primary Blue (high value)
  Avoid: Red-green (color-blind unfriendly); use blue gradient instead
```

**Chart Labels and Annotations**
```
Font: Body text font (Calibri), 10pt, Primary Gray
Callout boxes: Primary Blue box, white text; 10pt bold
Data labels: 9pt, Primary Gray or white (if on dark background)
Legend: Positioned outside chart (not overlapping data)
Source/Citation: 8pt, Light Gray, bottom-right
```

**Excel Chart Template**
```
Create a template workbook with charts pre-formatted:
1. Create sample bar, line, pie charts
2. Apply brand color palette
3. Format axes, legends, labels per standards
4. Save as: ChartTemplate.xlsx
5. Users copy this workbook and replace data (formulas/styles preserved)
```

### Step 6: Table Styling Standards
Consistent table design across Word and PowerPoint.

**Table Design** (Header Row + Data Rows)

**Header Row Formatting**
```
Background: Primary Blue (#0066CC)
Text: White (or light gray), Bold, 11pt
Alignment: Center for numeric columns, Left for text
Example:
┌────────────────┬──────────┬──────────┐
│ Product        │ Q1 Sales │ Q1 Plan  │  ← Blue header, white text
├────────────────┼──────────┼──────────┤
```

**Data Rows**
```
Background: Alternating white (#FFFFFF) and light gray (#F5F5F5)
Text: Primary Gray (#333333), 10pt, regular weight
Alignment: Left for text, Right for numbers (easier to scan)
Borders: Light gray (subtle, not heavy)

Example:
│ Widget A       │  $450K   │ $420K    │  ← Row 1 (white)
│ Widget B       │  $380K   │ $400K    │  ← Row 2 (light gray)
│ Widget C       │  $290K   │ $310K    │  ← Row 3 (white)
```

**Table Design in Word**
1. Insert → Table
2. Design tab → Choose template ("Light List Accent 1" or similar)
3. Customize: Right-click → Borders and Shading
   - Header: Primary Blue fill, white text
   - Data rows: Alternating white/light gray
4. Save as Table Style (so you can reuse)

**Table Design in PowerPoint**
1. Insert → Table
2. Table Design tab → Choose template
3. Right-click → Format Table
4. Customize colors to match brand palette

### Step 7: File Naming Conventions
Consistency in file organization.

**File Naming Pattern**
```
[DocumentType]_[Topic]_[Date]_[Version].extension

Examples:
Report_Q3FinancialResults_20240305_v1.docx
Proposal_TechCorp_20240305_v2.docx
Presentation_CompanyAnnual_20240320_v1.pptx
Budget_Engineering_2024_v3.xlsx
```

**Breaking Down the Pattern**
```
[DocumentType]: Report, Proposal, Presentation, Budget, Invoice, etc.
                Makes file type obvious; easy to filter by type

[Topic]:        Specific, descriptive title (not "Document1" or "Final")
                Makes content obvious; searchable

[Date]:         YYYY-MM-DD format (sorts chronologically)
                20240305 = March 5, 2024 (ISO 8601 standard)

[Version]:      v1, v2, v3 (incremented each significant revision)
                v1 = first draft
                v2 = incorporated feedback, ready for review
                v3 = final, approved
                Don't use: "v1 final" or "final final" (confusing)

Extension:      .docx (Word), .pptx (PowerPoint), .xlsx (Excel)
                Not: .doc, .xls (outdated formats)
```

**Folder Structure** (for team/company storage)
```
Company Shared Drive
├── 2024 (year folder)
│   ├── Q1
│   │   ├── Reports
│   │   │   ├── Report_Q1Financials_20240315_v1.docx
│   │   │   ├── Report_Q1Financials_20240320_v2.docx (updated)
│   │   ├── Presentations
│   │   │   ├── Presentation_Q1Review_20240320_v1.pptx
│   │   ├── Budgets
│   │   │   ├── Budget_Engineering_2024_v1.xlsx
│   ├── Q2
│   ├── Q3
│   ├── Q4
├── Templates
│   ├── Report_Template.docx
│   ├── Presentation_Template.pptx
│   ├── Budget_Template.xlsx
├── Archives
│   ├── 2023
│   ├── 2022
```

### Step 8: Template Distribution and Version Control
How to create and maintain templates.

**Master Templates** (create once, use many times)

**Template for Reports** (Report_Template.docx)
```
Includes:
- Title page with logo, title, date placeholders
- Standard header/footer pre-formatted
- H1, H2, H3 styles defined (brand colors, fonts)
- Table styles configured (alternating rows, brand colors)
- Executive summary section example
- Body section examples
- Footer with page numbers

Instructions:
1. Download Report_Template.docx
2. Save As → Name your report (using naming convention)
3. Update: Title, date, content
4. Styles are already applied; formatting is automatic
```

**Template for Presentations** (Presentation_Template.pptx)
```
Includes:
- Title slide with logo placement, theme colors
- Blank content slides (H1, body text styled)
- Chart placeholder slide (chart colors pre-applied)
- Table placeholder slide (table styles pre-applied)
- Conclusion/Q&A slide
- Master slides: All brand colors, fonts, logo placement defined

Instructions:
1. Download Presentation_Template.pptx
2. Save As → Name your presentation
3. Edit placeholders; use Slide Layouts from template
4. Insert charts/tables; they auto-apply brand colors
```

**Template for Budgets** (Budget_Template.xlsx)
```
Includes:
- Budget data entry sheet (rows, columns configured)
- Conditional formatting rules (variance highlighting)
- Formulas for calculations (YTD, quarterly, variance %)
- Dashboard sheet (KPI cards, summary metrics)
- Charts with brand color scheme

Instructions:
1. Download Budget_Template.xlsx
2. Save As → Name your budget
3. Edit data: Income, COGS, OpEx categories
4. Formulas auto-calculate; no manual math needed
5. Charts auto-update from your data
```

**Template Distribution**
```
Host Location: Shared drive or intranet (accessible to all teams)
  Path: [Shared Drive]/Templates/

How to access:
1. Open File → New (from template)
2. Navigate to Shared drive → Templates folder
3. Choose template
4. Opens as copy (original template never edited)

Version Updates:
- When template changes, all new documents use new version
- Old documents keep their version (no retroactive changes)
- Communicate changes in email (what changed, when effective)

Version Control:
  Template_Report_v1.docx (launched 2024-01-01)
  Template_Report_v2.docx (updated 2024-06-01; new color scheme)
  Keep old versions for 1 year (in case team refers to old version)
```

### Step 9: Brand Guidelines Document
Central reference for all style standards.

**Brand Guidelines Outline** (create in Word)
```
PART 1: BRAND OVERVIEW
1.1 Mission Statement
1.2 Brand Values
1.3 Brand Voice & Tone

PART 2: VISUAL IDENTITY
2.1 Logo
    - Logo usage (full, icon, monochrome, reversed)
    - Clear space and minimum size
    - Don't-Do examples (wrong sizes, placements, modifications)

2.2 Color Palette
    - Primary colors with hex codes
    - Secondary colors with hex codes
    - Accent colors (data encoding)
    - Color accessibility guidelines

2.3 Typography
    - Font families (headings, body, data)
    - Font sizes and weights (H1–H3, body, captions)
    - Letter spacing, line height rules
    - Font pairings

PART 3: OFFICE DOCUMENT STANDARDS
3.1 PowerPoint Guidelines
    - Slide layout standards
    - Header/footer placement
    - Chart color schemes
    - Title/content formatting
    - Animation guidelines (if any)

3.2 Word Document Guidelines
    - Page setup (margins, header/footer)
    - Heading styles and hierarchy
    - Table standards
    - Figure/table numbering
    - Footer placement

3.3 Excel Spreadsheet Guidelines
    - Color usage in data (conditional formatting)
    - Chart standards
    - Table styling
    - Logo placement

PART 4: FILE MANAGEMENT
4.1 File Naming Conventions
4.2 Folder Structure
4.3 Version Control

PART 5: TEMPLATES
5.1 Available Templates
    - Report_Template.docx
    - Presentation_Template.pptx
    - Budget_Template.xlsx
    - Proposal_Template.docx
5.2 How to Use Templates
5.3 Where to Find Templates

PART 6: DON'T-DO EXAMPLES
6.1 Common Mistakes (visual examples)
    - Wrong logo size
    - Misaligned colors
    - Inconsistent fonts
    - Poor table formatting
    - Cluttered slides

PART 7: FREQUENTLY ASKED QUESTIONS
7.1 Q: Can I use a different font?
    A: No. Stick to Calibri/Segoe UI for consistency.

7.2 Q: Can I add our own colors?
    A: No. Use the approved palette. Contact [Brand Owner] if you need new colors.

7.3 Q: How do I update a template?
    A: Contact [Brand Owner]. Only approved changes are made.

APPENDIX A: Color Swatches (visual palette)
APPENDIX B: Font Samples
APPENDIX C: Template Download Links
APPENDIX D: Contact Information for Questions
```

**Document Creation**
```
Format: PDF (read-only, prevents editing) + Word version (for updates)
Length: 10–15 pages
Distribution: Intranet homepage + onboarding materials
Updates: Review quarterly; update annually or when standards change
Owner: Marketing or Brand Manager
```

### Step 10: Rollout and Training
How to get teams using the system.

**Rollout Plan**
```
Week 1: Announce
- Email to all teams explaining new standards
- Link to Brand Guidelines document
- Templates available for download

Week 2: Training (optional webinar)
- 30-min webinar: "How to use templates"
- Demo: Creating a report, presentation, budget using templates
- Q&A session
- Recording available for those who miss it

Week 3: Spot-checks (optional)
- Review first few documents created with templates
- Provide feedback: "Looks great!" or "Please adjust X"
- Positive reinforcement

Ongoing:
- Support: [email for questions]
- Quarterly: Share great examples (celebrate teams doing it right)
- Updates: Announce any changes to standards
```

**Success Metrics**
```
Measure adoption:
- % of new documents using templates (goal: 90%+)
- % of new documents following style guide (goal: 95%+)
- Time to create document (should decrease; templates save time)
- Feedback from teams (satisfaction with templates)

Survey (after 3 months):
- "Templates saved me time" (rate 1–5)
- "Standards make our documents look professional" (rate 1–5)
- "I know which template to use" (rate 1–5)
- Open-ended: "What could we improve?"
```

## Output Template
```
# {{COMPANY}} Office Document Style Guide

## 1. Brand Colors
### Primary
- Primary Blue: #0066CC | RGB(0,102,204)
  Use: Main headings, primary emphasis

### Secondary
- Secondary Orange: #FF9900
  Use: Supporting headings, accents

### Data Encoding
- Success (Green): #00AA00 → ✓ On track
- Warning (Orange): #FFAA00 → ⚠ At risk
- Error (Red): #DD0000 → ✗ Off track

## 2. Typography
### Font Family
- Headings: Calibri Bold
- Body: Calibri Regular (11pt)
- Data: Courier New (monospace)

### Sizes
- H1: 28pt Bold, Primary Blue
- H2: 18pt Bold, Primary Blue
- H3: 14pt Bold, Secondary Orange
- Body: 11pt Regular, Primary Gray
- Caption: 9pt Regular, Light Gray

## 3. Logo & Brand Elements
### Logo Placement
- PowerPoint: Top-right (0.5"×0.25") or bottom-right title slide (1"×0.5")
- Word: Header top-left (0.5"×0.25") or footer (0.3")
- Excel: Top-left dashboard (0.5"×0.25")

## 4. Headers & Footers
### Header
Left: [Logo] Company Name | Center: Document Title | Right: Page #

### Footer
Left: Department | Center: [ID] | Right: Date | Confidentiality

## 5. Chart Color Scheme
| Sequence | Color | Hex Code |
|---|---|---|
| 1 | Primary Blue | #0066CC |
| 2 | Secondary Orange | #FF9900 |
| 3 | Secondary Green | #00AA00 |
| 4 | Primary Gray | #333333 |
| 5 | Light Gray | #F5F5F5 |

## 6. File Naming
Pattern: [Type]_[Topic]_[Date]_[Version].ext

Examples:
- Report_Q3Financials_20240305_v1.docx
- Presentation_Annual_20240320_v2.pptx

## 7. Templates Available
- Report_Template.docx
- Presentation_Template.pptx
- Budget_Template.xlsx
- Proposal_Template.docx

[Links to templates]

## 8. Common Mistakes (Don't-Do)
[Visual examples of wrong formatting]

## 9. Support & Questions
Contact: [Brand Manager Email]
Office Hours: [When available]
FAQ: [Link to Q&A doc]
```

## Quality Gates
- [ ] Color palette is defined with hex codes and usage rules
- [ ] Typography hierarchy is clear (H1, H2, H3, body sizes specified)
- [ ] Logo placement rules are specific (exact sizes, distances)
- [ ] Header/footer templates exist and are documented
- [ ] Chart color scheme is defined and accessible (color-blind safe)
- [ ] File naming convention is clear with examples
- [ ] Master templates exist for Report, Presentation, Budget
- [ ] Brand Guidelines document is comprehensive and accessible
- [ ] Rollout plan includes training and adoption tracking
- [ ] Support/contact information is provided for questions

## Examples

### Good Output (excerpt)
```
BRAND COLOR PALETTE

Primary Blue: #0066CC
├─ Use: Main headings (H1, H2)
├─ In PowerPoint: Title text, primary emphasis
├─ In Word: Report titles, section headers
├─ In Excel: Chart bars (primary series)
└─ Don't: Use for body text (too much blue = overpowering)

Secondary Orange: #FF9900
├─ Use: Supporting headings (H3), secondary information
├─ In PowerPoint: Subheading text
├─ In Word: Sub-subsection headers
├─ In Excel: Secondary chart series
└─ Don't: Use for body text (hard to read)

Data Encoding:
  ✓ Success (Green #00AA00): "On track" status
  ⚠ Warning (Orange #FFAA00): "At risk" status
  ✗ Error (Red #DD0000): "Off track" status
  All indicators use icon + text (not color alone for color-blind readers)

---

LOGO PLACEMENT RULES

In PowerPoint:
[Example image: Logo top-right at 0.5" × 0.25"]
Effect: Professional, visible but minimal
Never: Logo on every single slide (distracting)
       Logo larger than content

In Word:
[Example image: Logo in header top-left at 0.5" × 0.25"]
Effect: Marks document as official; consistent across pages
Never: Logo floating in middle of text
       Logo without adequate clear space

In Excel:
[Example image: Logo top-left at 0.5" × 0.25"]
Effect: Identifies company on dashboards
Never: Logo in data cells (interferes with analysis)

---

TEMPLATE USAGE

Report_Template.docx:
├─ Pre-formatted styles (H1, H2, H3)
├─ Logo and header/footer configured
├─ Table styles applied
├─ Example sections (Executive Summary, Body, Appendix)
└─ How to use: Save As → Edit title, date, content → Styles applied automatically

Presentation_Template.pptx:
├─ Slide layouts with brand fonts, colors
├─ Chart placeholder (auto-applies brand colors)
├─ Logo placement on title and content slides
└─ How to use: Save As → Use layouts → Content auto-formatted
```

### Bad Output (what to avoid)
```
Colors mentioned but no hex codes (how do you implement?)
Logo placement vague ("Put it somewhere visible")
Typography with no sizes specified ("Make headings bigger")
No actual templates; just guidelines (teams have to build from scratch)
File naming suggestions but not enforced (people ignore)
No examples of right/wrong (unclear what standards actually mean)
No support mechanism (teams have questions but nowhere to ask)
```

## Common Mistakes

1. **Mistake**: Color palette defined but not hex codes; teams can't match colors exactly.
   → **Fix**: Provide hex codes, RGB values, and Pantone numbers for designers.

2. **Mistake**: Typography rules exist but not applied to actual templates.
   → **Fix**: Create working templates where styles are already configured.

3. **Mistake**: Logo placement rules vague ("Put logo somewhere professional").
   → **Fix**: Specify exact sizes (1" × 0.5") and positions (top-right, 0.5" from edge).

4. **Mistake**: Style guide created but never distributed or trained.
   → **Fix**: Rollout includes email announcement, training webinar, and support contact.

5. **Mistake**: Standards apply to new documents, but no one updates old documents.
   → **Fix**: Old documents stay as-is; only new documents must follow standards (no retroactive requirements).

## Anti-Patterns
- Never define colors without hex codes; teams can't match. (Provide hex, RGB, Pantone.)
- Never skip templates; design guidelines alone don't help. (Create working templates.)
- Never use more than 2–3 fonts. (More = chaotic; stick to one font family, vary by weight/size.)
- Never apply brand colors to body text (hard to read); reserve color for headings/emphasis.
- Never enforce standards without providing templates/tools. (Make it easy to follow rules.)
- Never update standards without notifying teams. (Announce changes; update templates; give grace period.)
