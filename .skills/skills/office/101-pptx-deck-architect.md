---
name: pptx-deck-architect
description: "Design presentation narrative arc and slide strategy before building. Use this when someone says 'make me a presentation' or 'build a deck'—this skill architects WHAT GOES ON the slides, not the visual design."
category: office
difficulty: beginner
model_boost: "Fixes weak models that create slide decks without narrative structure, missing the situation→complication→resolution arc."
---

# PPTX Deck Architect

## Purpose
Before touching PowerPoint, design the narrative arc, slide sequence, and content strategy. This skill maps the situation-complication-resolution story that makes presentations persuasive, selects appropriate slide types for each point, and structures the deck for audience comprehension. Strong architecture prevents rambling 50-slide decks and ensures every slide serves the argument.

## When to Use
- "I need to build a presentation" (no outline exists yet)
- "Make me a deck on [topic]" (needs strategic structure)
- "I have this data—turn it into slides" (needs narrative, not just charts)
- **Do NOT use when**: Slides already exist and you're just refining content; use 108-pptx-data-storyteller instead

## Instructions

### Step 1: Define the Situation-Complication-Resolution Arc
This is the narrative spine that makes presentations stick. Map three core questions:
- **Situation**: What does the audience know/believe NOW? (e.g., "we're spending 35% more on cloud than competitors")
- **Complication**: What problem/opportunity creates tension? (e.g., "but we lack visibility into which services waste money")
- **Resolution**: What do you want them TO DO/BELIEVE? (e.g., "implement a cloud cost governance framework")

The entire deck should carry the audience through this arc—never jump to resolution without establishing why they should care. Write this arc in one sentence before designing any slides.

### Step 2: Determine the Slide Type Sequence
Select slide types strategically. Each type serves a specific rhetorical purpose:

**Opening Sequence (3-5 slides)**
- Title slide: Deck name, presenter, date, single keyword visual
- Agenda slide: Numbered topics (3-5 max). Never more than one agenda slide.
- Optional Context slide: One fact/stat that sets up the situation (use sparingly)

**Argument Building (6-20 slides)**
- Content slides: One idea per slide. Header is the insight ("Quarterly Revenue Grew 23%"), body has 3-5 bullet points supporting it
- Data/Chart slides: One chart per slide with annotation. Title states the conclusion, not just "Revenue"
- Transition slides: Bridging statement ("We've shown the problem. Now the solution.") with minimal graphics
- Evidence slides: Customer quote, case study result, testimonial slide

**Call-to-Action Sequence (2-4 slides)**
- Solution/Recommendation slide: Clear statement of what they should do
- Impact/Benefit slide: Why doing this matters (quantified outcomes preferred)
- Next Steps slide: Specific actions, owners, timeline
- Q&A slide: "Questions?" with contact info

**Closing (optional, 1 slide)**
- Summary slide: 3 key takeaways (not a full repeat—distilled essence)
- Backup/Appendix: Detailed data, methodology, or extra charts after main presentation

### Step 3: Apply the 10-20-30 Rule
Guy Kawasaki's principle: minimum 10 slides, 20 minutes, 30-point font.
- **10 slides minimum**: Forces ruthless editing. If you can't make your argument in 10, you don't understand it.
- **20 minutes max**: Most business audiences have finite attention. This is your target length.
- **30 points minimum**: If your font is smaller than 30 points, you have too much text. Slides are SPEAKER NOTES in large print, not a document.
- **Corollary**: 1-5 lines of text per slide maximum. One idea per slide.

### Step 4: Populate Content Strategically
For each slide, write:
- **Headline** (6-word maximum): States the "so what?" not just the topic
  - Bad: "Sales Performance"
  - Good: "Enterprise Sales Grew 40% YoY"
- **Body bullets** (3-5 max, 1 line each): Support the headline with evidence
- **Visual**: Chart, image, or diagram (no bullet-point slides with 8 lines)
- **Speaker notes**: What you'll actually say (5-10 sentences per slide)

### Step 5: Data Visualization for Slides
One insight per chart. Chart type depends on the message:
- **Comparison**: Bar chart (horizontal for long labels)
- **Trend**: Line chart (shows change over time)
- **Part-to-whole**: Stacked bar or pie (show composition)
- **Waterfall**: Shows contribution (starting value → adds/subtracts → ending value)
- **Correlation**: Scatter plot (shows relationship strength)
- Never use 3D effects, dual axes without clear reason, or pie charts with more than 3 slices

Chart title = the insight ("Revenue grew 23% driven by enterprise"), not just "Revenue by Segment"

### Step 6: Speaker Notes Discipline
Your speaker notes are NOT a transcription of what's on screen.
- Slide shows: "Enterprise growth reached $12M, up from $8.6M last year"
- Speaker notes: "This 40% growth reflects three new enterprise contracts we signed in Q3. The biggest one was TechCorp at $4.2M annual contract value. Pause here for questions."
- Notes should guide your delivery, signal where to slow down, provide context the audience doesn't see, and prepare for likely questions

## Output Template
For each presentation deck, output this structure:

```
# {{PRESENTATION TITLE}}

## Situation-Complication-Resolution Arc
- **Situation**: {{What the audience knows now}}
- **Complication**: {{The tension/opportunity that matters}}
- **Resolution**: {{What you want them to believe/do}}

## Slide Sequence ({{X}} slides total, {{Y}} minutes)

| # | Slide Type | Headline | Key Points | Notes |
|---|---|---|---|---|
| 1 | Title | {{Title}} | — | Presenter name, date, one keyword |
| 2 | Agenda | Agenda | {{Topic 1}}; {{Topic 2}}; {{Topic 3}} | Never exceed 5 agenda items |
| {{N}} | {{Content/Data/Transition}} | {{Headline—the insight}} | • Point 1<br>• Point 2<br>• Point 3 | {{Why this slide matters}} |

## Speaker Notes by Slide
{{Slide #}}: {{5-sentence speaker script}}

## Appendix Slides (reference, not presented)
- {{Backup data slide titles}}
```

## Quality Gates
- [ ] Arc is clear: Can you summarize Situation-Complication-Resolution in 3 sentences?
- [ ] Slide count respects 10-20-30: 10+ slides, 20 min estimate, no text smaller than 30pt
- [ ] Every slide has ONE headline insight (not just a topic)
- [ ] Data slides have annotation (callout/arrow pointing to the key number)
- [ ] Speaker notes exist and explain WHAT TO SAY, not just what's visible
- [ ] No duplicate ideas (each slide advances the argument uniquely)
- [ ] Transitions signal a shift in topic (never jump abruptly between ideas)

## Examples

### Good Output (excerpt)
```
# Q3 Financial Review: Path to Profitability

Situation-Complication-Resolution:
- Situation: Company is growing but burning cash ($2.1M/month)
- Complication: Cost structure hasn't scaled with revenue (OpEx at 68% of revenue)
- Resolution: Three operational changes will reach break-even by Q1

Slide 2: Agenda
Headline: "Three operational levers to profitability"
Points: Cost of goods reduction | Efficiency improvements | Pricing optimization

Slide 4: Content
Headline: "COGS fell 18% through supplier consolidation"
Points: • Renegotiated 5 largest vendor contracts
        • Reduced warehouse footprint from 3 to 2 locations
        • Adopted just-in-time inventory

Speaker Notes: "We took a systematic approach to COGS. By consolidating to our top five vendors—which represent 72% of spend—we gained leverage. The warehouse consolidation saved $340k annually. And just-in-time reduced our working capital needs significantly. PAUSE FOR QUESTIONS."
```

### Bad Output (what to avoid)
```
Slide 1: "Financial Overview" (generic, no insight)
Slide 2: "Situation Analysis" (obvious label, not a headline)
Slide 5: "Data" with a complex chart titled "Revenue by Product by Quarter by Region" (too much info, no annotation)
Speaker notes: "This chart shows revenue data across multiple dimensions" (says what's visible, doesn't guide delivery)
Slides 8-15: All text bullets, each with 7+ lines (violates 10-20-30)
```

## Common Mistakes

1. **Mistake**: Building slides without a narrative arc—just data pages.
   → **Fix**: Write the Situation-Complication-Resolution arc FIRST. Every slide must carry the story forward.

2. **Mistake**: Mixing topics on one slide ("Sales AND Marketing AND Product Updates").
   → **Fix**: One idea per slide. If it takes multiple bullets to explain one concept, it's one slide. If it's a separate concept, it's a separate slide.

3. **Mistake**: Assuming your data speaks for itself—no interpretation.
   → **Fix**: Interpret the chart in the headline. "Revenue grew 23%" is better than "Q1 vs Q4 Revenue Comparison."

4. **Mistake**: Creating 35 slides thinking "more is better."
   → **Fix**: Respect 10-20-30. If you need 35 slides, you've confused a presentation with a document. Split it up or create a separate reference deck.

5. **Mistake**: Speaker notes that just repeat what's on the slide.
   → **Fix**: Speaker notes should explain CONTEXT and WHAT TO SAY. Assume the audience can already read the slide.

## Anti-Patterns
- Never start with slides—start with the story. (Build the arc, then design)
- Never use more than one agenda slide. (Agenda is a contract; honor it)
- Never put full sentences on slides. (Headers are insights, bullets are proof)
- Never use generic slide titles like "Overview," "Details," "Analysis." (Tell the audience what you want them to believe)
- Never include a slide "just in case" someone asks. (That's what backup/appendix slides are for)
- Never design around the slide count. (Design for clarity, count what you get)
