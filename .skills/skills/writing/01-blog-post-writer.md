---
name: blog-post-writer
description: "Generate SEO-optimized blog posts (1500-2500 words) with compelling hooks, keyword-rich structure, internal linking strategy, and readability targets (Flesch 60-70). Includes meta descriptions and engagement metrics."
category: writing
difficulty: intermediate
model_boost: "Weak models produce fluffy generic content without strategic keyword placement, internal linking architecture, or readability optimization."
---

# Blog Post Writer

## Purpose
Create authoritative, search-engine-optimized blog posts that drive organic traffic by combining data-backed arguments, strategic keyword placement, reader engagement hooks, and clear information architecture. The output balances SEO requirements with human readability (Flesch score 60-70 = accessible to high school educated readers).

## When to Use
- Writing blog posts for content marketing that need organic search visibility
- Creating thought leadership content on industry trends or technical topics
- Developing pillar content with supporting internal linking clusters
- Converting one-off articles into conversion-focused pieces with CTAs
- Refreshing outdated blog content with new data and ranking opportunities
- **Do NOT use when**: Writing editorial opinion pieces, fiction, or brand storytelling that prioritizes voice over searchability

## Instructions

### Step 1: Keyword Research & Strategic Placement
Research primary keyword (target: 10-100 search volume/month) and 4-6 secondary keywords. Place primary keyword in: title (position 1-3), H1, first 100 words, first H2, and 1-2 additional H2s. Secondary keywords should appear in different H2s (never keyword-stuff). Use long-tail modifiers: "how to", "best", "vs", "[year]" (e.g., "best CRM tools 2025" not just "CRM tools").

### Step 2: Create Magnetic Hook (First 100 Words)
Open with pattern-interrupt: bold statistic, counterintuitive claim, or specific failure point (not generic question). Example: "73% of sales teams use CRMs they don't understand. By week 3 of onboarding, most abandon advanced features entirely." Then position your post as the remedy. Include primary keyword in first 80 words. Target readability: 8th-grade level. Avoid passive voice ("is used" → "use").

### Step 3: Build Scannable Information Architecture
Outline 5-7 main sections with descriptive H2 headings (12-15 words max). Each H2 should telegraph value: "Why [benefit] Matters for [audience]" or "[Number] Proven [Outcome] Methods." Use H3s to break H2 sections into 200-300 word chunks. Include bulleted lists (3-5 items) with bolded first 3-4 words. No paragraph should exceed 5 sentences.

### Step 4: Embed Real Data & Credibility Signals
Anchor each major claim with data: cite studies, surveys, tooling benchmarks (attribute source inline: "According to HubSpot's 2025 Sales Benchmark..."). Dedicate 1-2 sections to case study or worked example showing before/after metrics. Use specific numbers (not "many" or "some"). Include expert quote (80-120 words) with attribution and title/company.

### Step 5: Strategic Internal Linking & Keyword Clustering
Link to 3-5 internal pages using anchor text that matches target keywords for those pages (not generic "click here"). Distribute links across the post, not clustered in one section. Each link should feel contextually earned. Example: "Learn more about [topic] in our [keyword-rich anchor] guide" — the anchor text should be your target keyword for that destination page.

### Step 6: Closing CTA with Email Signup or Next Step
End with 1-sentence summary + specific CTA. Pattern: "[Your post] shows that [main insight]. **[Action verb]: [benefit]. [Friction remover: time/ease].** [Micro-commitment first] or [larger ask]." Example: "Download the CRM Setup Checklist (2 min read) or schedule a 15-min implementation call." Include resource offer (gated or ungated) with clear next step.

## Output Template

```markdown
# {{SEO-Keyword-Rich Title (50-60 Characters with Primary Keyword)}}

**Meta Description:** {{55-160 characters including primary keyword, benefit-driven, includes call-to-action}}

## {{Magnetic Hook Section - No H2 Label, Just Content}}

{{Statistics or counterintuitive claim (1-2 sentences)}}

{{Problem statement with specificity (2-3 sentences)}}

{{How this post solves it (1 sentence)}}

## {{H2: Secondary Keyword or Benefit-Driven Heading}}

{{Introduction paragraph}}

### {{H3: Specific Sub-Topic}}

{{200-300 word section with bulleted takeaways}}

- **First takeaway**: {{detail}}
- **Second takeaway**: {{detail}}

{{Continue with 4-6 more H2/H3 sections following this pattern}}

## {{H2: Case Study or Worked Example Section}}

{{Before: {{metric}}, pain point}}
{{After: {{metric}}, improvement}}
{{How they did it: {{3-4 sentences of methodology}}}}

## {{H2: Common Mistakes to Avoid}}

- **Mistake**: {{specific error}} → **Fix**: {{correction}}
- **Mistake**: {{specific error}} → **Fix**: {{correction}}

## {{H2: Quick Summary + CTA}}

{{1-sentence recap of main insight}}

**{{Action verb}}**: {{specific offer}} ({{time commitment]})

{{Link to next resource with internal anchor text using target keyword}}
```

## Quality Gates

- [ ] Primary keyword appears in title (position 1-3), H1 equivalent, first 80 words, and at least 2 H2s
- [ ] Post length: 1500-2500 words; average paragraph: 40-80 words; average sentence: 12-16 words
- [ ] Flesch Reading Ease score: 60-70 (check via tools like Hemingway Editor or Yoast)
- [ ] Includes 3+ cited data points, statistics, or expert quotes with attribution
- [ ] Contains 4-6 internal links with keyword-rich anchor text, contextually placed
- [ ] H2 headings are benefit-driven, descriptive, not keyword-cramped (12-15 words max)
- [ ] First 100 words contain hook (statistic/counterintuitive claim), problem, and primary keyword
- [ ] Post ends with specific CTA (not vague "learn more") with resource offer
- [ ] Bulleted lists present with bolded keyword phrases
- [ ] No paragraph exceeds 5 sentences; scannability tested with visual hierarchy

## Examples

### Good Output (Excerpt)

**Title:** "How to Build a CRM Strategy That Actually Sticks (2025 Guide)"

**Meta Description:** "73% of CRM implementations fail. Learn the 5-step strategy framework that 12,000+ sales teams used to reduce setup time by 60%."

---

According to HubSpot's 2025 Sales Benchmark, 73% of CRM implementations are abandoned by month 3. The problem isn't the technology—it's that teams confuse implementation with strategy.

This guide walks through the exact 5-step framework that turned 12,000+ sales teams from frustrated users into power users, reducing typical setup time from 16 weeks to 6 weeks.

## Why CRM Strategy Matters (Before You Pick a Tool)

Most teams choose a CRM first, then try to fit their process around it. That's backwards.

### The Real Cost of Poor CRM Strategy

- **Wasted training time**: 40+ hours per team member relearning workarounds
- **Adoption collapse**: Salespeople using spreadsheets instead of the $50K system
- **Data quality death spiral**: Incomplete records, no trust in reporting

A strategy-first approach prevents this. Here's how [internal link using "CRM implementation checklist"].

### Good Output Analysis
- Hook uses specific statistic + attribution (HubSpot 2025 Benchmark)
- Counterintuitive claim: "It's not the technology, it's the strategy"
- Bullet list with bolded keywords for scannability
- Next section has internal link with keyword-rich anchor
- Paragraph length: 2-4 sentences
- Active voice throughout

### Bad Output (What to Avoid)

**Title:** "CRM Tools and How to Use Them"

Many companies use CRMs. A CRM is a customer relationship management system. It helps you manage customer relationships. There are many CRMs available. Salesforce is one. HubSpot is another. Microsoft Dynamics is also available. You can also use Pipedrive or Zoho. Each one is different. Some are better than others.

**Issues Identified:**
- Title: generic, no primary keyword, no benefit signal
- No hook or statistic in opening
- Repetitive sentence structure ("X is..." pattern)
- No data, no specificity
- Meta description: doesn't exist
- Passive voice overused
- No internal linking
- No clear CTA
- Flesch score: 90+ (too simplistic)

## Common Mistakes

1. **Mistake**: Keyword-stuffing secondary keywords into every H2 instead of naturally distributing them
   → **Fix**: Use secondary keywords once per section in different H2s; let topical relevance guide structure, not keyword density quotas

2. **Mistake**: Opening with generic question ("Have you ever wondered...?") instead of pattern-interrupt
   → **Fix**: Lead with specific statistic, counterintuitive claim, or named problem (not rhetorical question)

3. **Mistake**: Writing for search engines (awkward phrasing, jargon) instead of humans
   → **Fix**: Write in active voice, conversational tone, then layer keywords naturally during editing. Readability comes first.

4. **Mistake**: Including only external links or no internal links
   → **Fix**: Minimum 4-6 internal links using anchor text that matches target keywords of destination pages

5. **Mistake**: Paragraphs of 8+ sentences with no white space
   → **Fix**: Split long paragraphs into 2-4 sentence chunks; use H3 subheadings to break dense sections

## Anti-Patterns

- **Never** bury the CTA in the middle or make it vague ("Learn more here"). Prominent, specific CTA at the end only.
- **Never** cite studies or statistics without attribution. Attribution adds credibility AND improves Flesch score by breaking up dense text.
- **Never** use passive constructions like "It is recommended that..." when "You should..." is clearer and shorter.
- **Never** write H2 headings that read like keyword salad ("CRM Tools Best Practices Features Benefits 2025"). Headings must make a claim or promise value.
- **Never** exceed 300 words per H3 section without a bulleted list or visual break. Scannability dies in dense paragraphs.
