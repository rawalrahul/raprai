---
name: explainer
description: "Explain complex concepts at any target comprehension level using layered analogies, progressive complexity, visual scaffolding, and preemptive misconception correction. Suitable for peer teaching, parent communication, and multi-level audiences."
category: education
difficulty: beginner
model_boost: "Fixes jargon-heavy explanations and one-level-fits-all descriptions"
---

# Explainer

## Purpose
This skill generates clear, engaging explanations of complex topics calibrated to a specific audience's prior knowledge and readiness level. It uses research-backed techniques: analogies to concrete experiences, progressive scaffolding from simple to complex, visual descriptions, strategic repetition, and preemptive misconception addressing. The same concept can be explained at 3+ different levels.

## When to Use
- Explaining a concept a student didn't understand in initial instruction
- Creating content for mixed-ability audiences (parents, students, peers at different levels)
- Addressing persistent misconceptions
- Making abstract concepts concrete
- Preparing explanations for discussions or presentations
- **Do NOT use when**: You need a complete lesson plan (use lesson-planner), comprehensive course design (use curriculum-designer), or assessment rubrics (use rubric-builder)

## Instructions

### Step 1: Identify Your Concept and Audience
Name the concept precisely. Then specify your audience: grade level, prior knowledge level (complete novice, some background, advanced), language proficiency (native English speaker vs. ELL), learning preference (visual, kinesthetic, abstract, concrete thinker). Different audiences need completely different explanations. A 5-year-old learning "gravity" needs something different than a 16-year-old; a native speaker needs different pacing than an ELL student.

### Step 2: Map Prerequisite Knowledge
Identify 3-5 prerequisite concepts the audience likely knows. These will be your analogical anchors. For example, to explain photosynthesis to 5th graders, prerequisites might be: "plants need food," "sun provides energy," "chemical reactions happen." To explain to advanced students, prerequisites might be: "energy conservation," "redox reactions," "electron transport chains." Explicitly surface what you're assuming they know; this prevents talking past the audience.

### Step 3: Generate Core Analogy or Mental Model
Create an extended analogy that maps the unknown (new concept) to the known (familiar prior knowledge). The analogy should work at multiple levels of detail. Example for photosynthesis: "A plant is like a solar panel factory. The sun (light) powers tiny factories inside the plant leaf (chloroplasts). Those factories take raw materials (water and air) and make food (sugar/energy) the plant can use or store." The analogy breaks down if pressed too far—acknowledge the limits later.

### Step 4: Build Progressive Complexity Layers
Create 3-4 versions of your explanation, each adding detail:
- **Layer 1 (Intuitive)**: Single sentence + analogy. No jargon.
- **Layer 2 (Basic)**: 2-3 sentences; introduce 1-2 key terms; explain what happens
- **Layer 3 (Intermediate)**: Add mechanism/process; connect to everyday examples; introduce 3-4 technical terms; answer "why" and "how"
- **Layer 4 (Advanced)**: Full mechanism; molecular/systemic details; exceptions and edge cases; quantitative relationships

The explanation should "onion-peel"—audience should never jump to Layer 4 without understanding Layers 1-3.

### Step 5: Preemptively Address Misconceptions
Anticipate the wrong ideas students commonly hold about this concept. Research shows specific misconceptions cluster by age/background. For each misconception, do NOT just say "this is wrong." Instead: (a) validate why it seems logical, (b) provide a counterexample or evidence that breaks the misconception, (c) show what's true instead. Example—misconception: "Plants get their food from soil." Response: "I know that seems true because we fertilize soil, but the proof is: if you grow a plant in pure water with no soil, it still grows. The soil doesn't contain the plant's food; it contains nutrients the roots need."

### Step 6: Add Strategic Repetition and Recall Opportunities
Identify the 1-2 most critical ideas. Circle back to them 2-3 times using different words or contexts. Include a brief check: "Does that make sense? Can you think of an example?" This isn't filler—spaced repetition encodes memory better than single exposure. For written explanations, use formatting (bold, bullets) to highlight key ideas.

### Step 7: Create Visual/Spatial Description
If explaining something with visual or spatial components, paint a picture with words. Use directional language (left, inside, above), size comparisons (smaller than a pinhead), color/texture, motion/sequence. For abstract concepts, create a "mental model" diagram in words: "Imagine a staircase where each step is a level of organization—atoms (bottom step) → molecules → cells → tissues → organs (top step). The higher you climb, the more organized and complex the structures."

### Step 8: Conclude with Application and Connection
End with a concrete application or connection to the audience's world. This cements understanding and shows why it matters. For young students: "That's why plants always bend toward the window—they're trying to use sunlight to make food." For older students: "This is why photosynthesis efficiency is a bottleneck for renewable energy and food production." Invite them to notice the concept in their environment.

## Output Template

```
EXPLAINING: [Concept Name]
TARGET AUDIENCE: [Grade/Role, Prior Knowledge, Language Proficiency]
PREREQUISITES ASSUMED: [List 3-5 concepts audience should know]

CORE ANALOGY:
[Analogy explaining unknown via known; 2-3 sentences]

MISCONCEPTIONS TO ADDRESS:
1. [Misconception] → [Why it seems logical] → [Counterexample] → [What's true]
2. [Misconception] → [Why it seems logical] → [Counterexample] → [What's true]

LAYER 1 — Intuitive (1-2 sentences, no jargon)
[Single sentence + simple analogy]

LAYER 2 — Basic (2-3 minutes to explain)
[What it is, how it works; 1-2 new terms; everyday example]

LAYER 3 — Intermediate (5-7 minutes to explain)
[Mechanism/process; why it happens that way; 3-4 technical terms; 2+ examples at different contexts]

LAYER 4 — Advanced (10+ minutes to explain)
[Full mechanism with detail; molecular/systemic explanation; exceptions and edge cases; quantitative relationships if relevant]

VISUAL/SPATIAL DESCRIPTION:
[Paint-a-picture description of the concept; directional language; size comparisons; motion/sequence]

STRATEGIC REPETITION POINTS:
[Return to this key idea here (Layer 2)] → [Return to this key idea here (Layer 3)] → [Return to this key idea here (Layer 4)]

CHECK-FOR-UNDERSTANDING PROMPTS:
- [Question that reveals if they understand Layer 1]
- [Question that reveals if they understand Layer 2]
- [Question that reveals if they understand Layer 3]

APPLICATION & CONNECTION:
[Concrete use in audience's world; why it matters; invitation to notice it]
```

## Quality Gates
1. **Audience Match**: Explanation uses vocabulary and examples appropriate to the stated audience; no jargon in Layer 1
2. **Analogical Integrity**: Analogy works at multiple levels; limits of analogy are acknowledged or become clear in Layer 3+
3. **Misconception Specificity**: At least 2 misconceptions with evidence, not generic "students sometimes struggle"
4. **Progressive Onion-Peel**: Each layer is genuinely more complex; cannot understand Layer 3 without Layer 1-2
5. **Repetition Purposeful**: Key ideas return in different contexts; not just repeating the same words
6. **Concrete Ground**: Even abstract concepts connect to something the audience has experienced or can visualize
7. **Bidirectional Check**: Includes prompts where audience can signal understanding or ask for clarification

## Examples

### Good: Explaining Fractions to 3rd Grade
**Target Audience**: 8-9-year-olds, basic division knowledge, concrete/visual learners

**Core Analogy**: "A fraction is like dividing a pizza. If you cut the pizza into 4 equal pieces and eat 1 piece, you ate 1/4 of the pizza."

**Misconception**: "5/8 is smaller than 1/2 because 5 is smaller than 8."
- Why it seems logical: Bigger numerator, bigger denominator, so smaller value (wrong logic)
- Counterexample: "Draw two identical circles. Divide one into 2 equal parts and shade 1 (that's 1/2). Divide the other into 8 equal parts and shade 5 (that's 5/8). Look—5/8 is actually bigger! More pieces shaded."
- What's true: "The numerator and denominator work together. 5/8 means you have 5 out of 8 pieces. Since each piece in the 8-part circle is smaller, 5 pieces add up to more."

**Layer 1**: "A fraction is a part of a whole. Like if you cut a pizza into 4 pieces and take 1, that's 1/4 of the pizza."

**Layer 2**: "The bottom number (denominator) tells you how many equal pieces the whole is cut into. The top number (numerator) tells you how many of those pieces you have. So 3/4 means the whole is cut into 4 pieces and you have 3 of them."

**Layer 3**: "Fractions show a relationship: a part compared to a whole. The denominator tells the size of each piece—smaller denominator means bigger pieces. So 1/2 has 2 big pieces; 1/8 has 8 tiny pieces. But 4/8 actually equals 1/2 because four of those tiny pieces adds up to the same amount as one big piece. That's called equivalent fractions."

**Layer 4**: "Fractions are numbers representing the quotient of two integers. The denominator (divisor) partitions the whole into equal intervals; the numerator (dividend) indicates how many intervals are selected. Equivalent fractions represent the same rational number through different partitions—1/2 = 2/4 = 4/8—because they represent the same position on the number line. This multiplicative relationship is foundational to proportional reasoning."

**Visual Description**: "Imagine a candy bar. Now imagine drawing lines to divide it into 8 equal pieces. Shade in 3 pieces with your pencil. The shaded part is 3/8 of the candy bar. Now imagine a different candy bar divided into only 4 pieces, with 2 pieces shaded. That's 2/4—and it's the same amount shaded as the first one even though the numbers are different. The pieces are just bigger."

**Check-for-Understanding**:
- Can you show me 1/2 of a circle using a picture?
- If a chocolate bar is cut into 3 pieces and I eat 2, what fraction did I eat?
- Are 2/3 and 4/6 the same amount? How do you know?

### Bad: Explaining Photosynthesis to Middle School
**Explanation**: "Photosynthesis is the biochemical process by which plants synthesize organic compounds from carbon dioxide and water using chlorophyll to absorb light energy. It involves light-dependent reactions in the thylakoid and light-independent reactions in the stroma, producing glucose and oxygen through electron transport chains."

**Problems**:
- No prerequisite check (do students know "chlorophyll"? "thylakoid"? "electron transport"?)
- No analogy to concrete experience
- No misconception addressing
- Jargon-dense; jumps straight to "Layer 4"
- No visual description or mental model
- No check-for-understanding
- No application to student's world

## Common Mistakes

1. **Jargon Overload in Layer 1**: Introducing 5+ technical terms before establishing the basic concept. Layer 1 should use only words a 5th grader (or non-expert) would know. Jargon belongs in Layers 3-4, introduced gradually with clear definition.

2. **Analogies That Mislead**: Using an analogy that works for part of the concept but breaks down in ways you don't acknowledge. Students then build a model that's partially wrong. Solution: In Layer 3, explicitly state where the analogy breaks down and why the actual mechanism differs.

3. **False Misconceptions**: Listing misconceptions that sound plausible but aren't actually common (often things YOU think are misconceptions but students rarely believe). Instead: Research or ask students what they actually think. Use realistic misconceptions backed by cognitive science research.

4. **No Onion-Peel Progression**: Writing three versions at similar complexity levels, just with different examples. Instead: Layer 1 should be so simple it seems almost too easy to an educated adult. Layer 3 should introduce genuine mechanism and complexity. The audience should feel themselves climbing.

5. **Skipping the "Why"**: Explaining HOW photosynthesis happens (the mechanism) but not WHY plants need it (the purpose/function). For maximum clarity, students need both. "Plants need energy to grow and move water. Photosynthesis captures sunlight and stores it as chemical energy (sugar) the plant can use later."

## Anti-Patterns

1. **Lecture-as-Explanation**: Explanation that's one-directional, passive, with no built-in check-for-understanding. Instead: Create interactive moments—a question, a task ("sketch this"), a prediction ("what do you think happens if..."), an invitation to raise a hand if confused. Even written explanations benefit from checkpoint questions.

2. **Over-Simplification That's Wrong**: Saying something is "just" simple when it isn't. "Gravity is just things falling down" is simpler but misleading—gravity is mutual attraction. Instead: Simple AND truthful. Start with the simplified version, then in Layer 3, show how it's more nuanced.

3. **Ignoring Individual Differences**: Assuming all students in a grade level have the same prior knowledge and learning preference. Instead: Know your audience specifically. Are they 3rd graders who love sports or art? Are they struggling readers? Are they visual or kinesthetic learners? Tailor examples and analogies accordingly.

