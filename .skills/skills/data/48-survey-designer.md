---
name: survey-designer
description: "Design rigorous surveys with bias avoidance, appropriate question types, skip logic, Likert scales, and sample size guidance. Produces survey and analysis plan."
category: data
difficulty: intermediate
model_boost: "Weak model designs biased surveys or misinterprets Likert/rating data"
---

# Survey Designer

## Purpose
Surveys gather subjective data directly from users/customers about experiences, opinions, and needs. This skill systematizes survey design to minimize bias, ensure questions are clear and unambiguous, and collect data suitable for rigorous analysis. The output is a tested survey instrument with predefined analysis plan.

## When to Use
- Measuring customer satisfaction, NPS, or loyalty
- Gathering user feedback on features or product
- Understanding decision drivers and purchase criteria
- Demographic or behavioral segmentation
- **Do NOT use when**: Behavioral data available, or response bias concerns outweigh benefits

## Instructions

### Step 1: Define Survey Purpose and Population
Clarify what you're measuring and who should answer:

**Survey purpose definition:**
```
EXAMPLE 1: NPS Survey

Purpose: Measure customer satisfaction and likelihood to recommend
Business question: Are customers promoters or detractors?
Who answers: All active customers (n = 10,000)
When: Quarterly (track trend)
How used: Segment into promoters/passives/detractors for outreach

Action triggers:
- NPS >50: Celebrate, maintain product strategy
- NPS 40-50: Monitor, investigate detractors
- NPS <40: Crisis; full root cause analysis required

EXAMPLE 2: Feature Feedback Survey

Purpose: Prioritize feature improvements based on user input
Business question: Which feature gaps matter most to users?
Who answers: Current users who actively use product (n = 1,000)
Exclude: Free trial users (untested), disengaged users (no usage in 30 days)
When: After major release (gather feedback on new features)
How used: Rank feature requests by vote count to inform roadmap

Action triggers:
- Feature >40% want: High priority
- Feature 20-40% want: Medium priority
- Feature <20% want: Low priority

EXAMPLE 3: Enterprise Segmentation Survey

Purpose: Understand customer needs and buying criteria
Business question: What business segments should we target?
Who answers: Prospective and current enterprise customers (n = 200)
Timing: During sales discovery or quarterly business reviews
How used: Build buyer personas, segment messaging

Action triggers:
- Segment with >$100M market = core target
- Segment with 80%+ "feature X matters" = must-have
- Segment with <15% using competitive product = new market
```

**Population sampling:**
```
CENSUS (survey entire population):
- Feasible when: Population < 2,000 (low response burden)
- Example: 500 power users, want feedback on new interface
- Pro: Complete data, no sampling error
- Con: Takes longer, higher cost

RANDOM SAMPLE:
- Feasible when: Population > 2,000
- Sample size formula (continuous outcomes, e.g., likelihood to recommend 0-10):
  n = (1.96 * σ / E)²
  where E = desired margin of error (e.g., ±0.5 points on 10-point scale)
          σ = estimated standard deviation (assume 2-3 for NPS)

  Example: To estimate NPS within ±1 point with 95% confidence, need ~35 responses

- Stratified sample:
  Divide population into strata (e.g., customer segment, tenure)
  Sample from each stratum proportionally
  Pro: Ensures representative sample of all segments
  Con: Requires knowing population structure

EXAMPLE CALCULATION:
Population: 50,000 customers
Desired confidence: 95% (z=1.96)
Desired margin of error: ±2 points on NPS scale
Estimated SD: 2.5

Sample size = (1.96 * 2.5 / 2)² = 6.1² ≈ 37 surveys minimum
Add 20% buffer for non-response: 37 / 0.8 ≈ 50 responses target

Stratified by plan type (known distribution):
- Enterprise (5%): 50 * 0.05 = 2.5 → 3 surveys
- Mid-market (20%): 50 * 0.20 = 10 surveys
- SMB (75%): 50 * 0.75 = 37.5 → 37 surveys
Total: 50 surveys
```

### Step 2: Avoid Common Question Biases
Design questions that elicit honest, unambiguous responses:

**Bias types and prevention:**

```
LEADING BIAS (Question implies desired answer)

BIASED: "Our new feature is great. How much do you like it?"
        (Suggests feature is good, primes positive response)

UNBIASED: "What is your opinion of the new feature?"
         (Neutral, lets respondent form own view)

BIASED: "Don't you think customer support is excellent?"
        (Rhetoric suggests 'yes', social pressure to agree)

UNBIASED: "How satisfied are you with customer support?"
         (Neutral, allows full range of responses)

RULE: Question should not hint at desired answer


DOUBLE-BARRELED BIAS (One question asks multiple things)

BIASED: "Is the product easy to use and affordable?"
        (Can't answer 'easy to use but too expensive')

UNBIASED: Ask separately
         "How easy is the product to use?" (1-5 scale)
         "How affordable is the product?" (1-5 scale)

BIASED: "How satisfied are you with the product and support?"
UNBIASED: Ask separately
         "How satisfied are you with the product?"
         "How satisfied are you with the support?"


VAGUE/AMBIGUOUS BIAS (Question meaning unclear)

BIASED: "How often do you use the product?"
        (Does 'use' mean open app, or actually complete task?)

UNBIASED: "In the past 30 days, how many days did you use the product?"
         (Specific timeframe, specific action)

BIASED: "Do you find the product useful?"
        (Useful for what? In what context?)

UNBIASED: "How helpful is [specific feature] for [specific task]?"
         (Clear scope and purpose)


RESPONSE OPTION BIAS (Answer choices suggest direction)

BIASED: Scale: "Excellent | Good | Acceptable | Poor | Terrible"
        (Skewed toward negative; most say "Acceptable" by default)

UNBIASED: Scale: "Very Satisfied | Satisfied | Neutral | Dissatisfied | Very Dissatisfied"
         (Balanced, symmetrical)

BIASED: "How strongly do you agree? Strongly Agree | Agree | Neutral | Somewhat Disagree"
        (Omits "Strongly Disagree"; pushes toward agreement)

UNBIASED: "Strongly Agree | Agree | Neutral | Disagree | Strongly Disagree"
         (Complete, symmetrical)


SOCIAL DESIRABILITY BIAS (Respondents give socially acceptable answer)

BIASED: "How important is diversity in hiring to you?"
        (Most say "Very important" regardless of true beliefs)

UNBIASED: Use behavioral questions: "In the past 12 months, how much
          did you personally contribute to diversity initiatives?"
         (Harder to fake; honest admission of effort)

MITIGATION:
- Assure anonymity: "Your responses are confidential"
- Remove judgment: Don't use morally loaded language
- Ask behavior, not beliefs: "What did you do?" not "What do you believe?"
```

### Step 3: Choose Appropriate Question Types
Match question type to information need and analysis capability:

**Question types and use cases:**

```
MULTIPLE CHOICE (Single answer)
"Which feature would you most want us to build next?"
○ Feature A
○ Feature B
○ Feature C
○ Not sure

Usage: Feature prioritization, segment identification
Analysis: Count votes per option, calculate %, chi-square test for significance
Pros: Easy to answer, quantifiable
Cons: Forced choice may omit important options

TIP: Always include "Other (please specify)" for unexpected answers


MULTIPLE SELECT (Multiple answers allowed)
"Which of these features do you currently use? (Select all that apply)"
☐ Feature A
☐ Feature B
☐ Feature C

Usage: Understanding feature adoption, capability needs
Analysis: Calculate adoption % per feature, correlation between features
Pros: Captures complexity (users use multiple features)
Cons: Can't rank (don't know relative importance)

TIP: Limit to 5-7 options (cognitive overload > 7)


LIKERT SCALE (Ordinal rating)
"How satisfied are you with the product?"
Scale: 1 = Very Dissatisfied ... 5 = Very Satisfied

Usage: Satisfaction, agreement, likelihood
Analysis: Mean, median, % in each category, correlations
Common mistake: Treating as numeric (averaging 1-5 scale) when ordinal
                Data isn't equally spaced (gap between 1-2 ≠ 4-5)
Better: Report % in each category, or convert to binary (4-5 = satisfied)

LABELING:
Unipolar (0 = none, 5 = lots):      None | A little | Some | Quite a bit | A lot
Bipolar (-2 to +2): Disagree | Disagree | Neutral | Agree | Strongly Agree


NUMERIC SCALE (Continuous rating)
"On a scale of 0-10, how likely are you to recommend us to a colleague?"

Usage: NPS, likelihood, probability
Analysis: Mean, SD, distribution, segment by promoter/passive/detractor
NPS scoring: Promoters (9-10) - Detractors (0-6) = NPS score
Example: 60% Promoters, 20% Detractors = NPS of 40

TIP: Use 0-10, not 1-5 (0-10 is familiar for "likelihood")


OPEN-ENDED TEXT
"What is the single biggest improvement we could make?"

Usage: Qualitative feedback, understanding decision drivers
Analysis: Coding (group responses into themes), word frequency
Pros: Unfiltered feedback, discover unexpected insights
Cons: Labor-intensive to analyze, respondent effort higher

TIP: Ask at end of survey (higher abandonment if too many)
     Use when you genuinely want open feedback, not just as catch-all


MATRIX (Multiple items, same scale)
"For each feature, rate your satisfaction (1-5 scale):"

Feature A: ○1 ○2 ○3 ○4 ○5
Feature B: ○1 ○2 ○3 ○4 ○5
Feature C: ○1 ○2 ○3 ○4 ○5

Usage: Comparing multiple items efficiently
Pro: Compact, shows trade-offs clearly
Con: Respondent fatigue, question inflation (each item × scale = many response options)

TIP: Limit to 5-7 rows (more = fatigue + lower data quality)


RANKING
"Rank these features by importance (1=most important, 5=least important):"
___ Feature A
___ Feature B
___ Feature C

Usage: Feature prioritization when relative importance matters
Pro: Reveals true preferences (forced to choose)
Con: Cognitively harder, higher effort, more abandonment
     Analysis complex (ranking data isn't easily averaged)

TIP: Use only if relative ranking essential; otherwise use "select top 3"
```

### Step 4: Implement Skip Logic and Conditional Flows
Design survey that adapts based on responses:

**Skip logic patterns:**

```
BASIC SKIP:
Q1: "Do you currently use our product?"
  → If YES: Go to Q2 (usage questions)
  → If NO: Skip to Q5 (why don't you use)

EXAMPLE (NPS SURVEY):

Q1: "How satisfied are you? (1-5 scale)"
  → If 4-5 (Satisfied): Go to Q2
    Q2: "What do you like most?"
    Q3: "Any improvements?"
    Skip Q4, Q5, Q6 (detailed dissatisfaction questions)

  → If 1-3 (Dissatisfied): Go to Q4
    Q4: "What's your biggest frustration?"
    Q5: "Have you considered switching?"
    Q6: "What would make you stay?"
    Skip Q2, Q3 (satisfaction questions)

Q7: Demographics (all respondents)

BENEFIT: Shorter survey for satisfied customers (3 min vs. 10 min)
         More depth for dissatisfied (understand problems)
         Higher completion rate

IMPLEMENTATION (Online survey tool):
Most tools (Qualtrics, SurveyMonkey) support skip logic visually
Set rules: If Q1 response = [4, 5] → Show Q2, Q3; Hide Q4, Q5, Q6

BRANCHING:
Advanced: Show entirely different survey versions based on segment
  Customer segment = Enterprise: Ask about integrations, scalability
  Customer segment = SMB: Ask about ease of use, price
Result: More relevant, higher completion rate, better data
```

### Step 5: Design Analysis Plan
Predetermine how you'll analyze results before survey launches:

**Analysis plan template:**

```
SURVEY: NPS Measurement
DATE: Quarterly, March 2026

POPULATION: All active customers (used product in last 30 days)
SAMPLE: Stratified random sample (n = 150)
  - Enterprise: 30 customers
  - Mid-market: 50 customers
  - SMB: 70 customers

PRIMARY METRIC: Net Promoter Score (NPS)
Calculation: % Promoters (9-10) - % Detractors (0-6)
Baseline: NPS = 35 (from Q4 2025)
Target: NPS ≥ 45 (10-point improvement)
Success threshold: NPS ≥ 40 (shows improvement trajectory)

SEGMENTATION ANALYSIS:
Compare NPS by:
  - Customer segment (Enterprise, Mid-market, SMB)
  - Tenure (0-1 year, 1-3 years, 3+ years)
  - Product usage (high, medium, low)

Hypothesis: Enterprise and long-tenured customers have higher NPS
Expected pattern: NPS should increase with tenure

FOLLOW-UP ANALYSIS:
- Verbatim analysis: Themes from open-ended feedback
- Correlation: Does feature adoption correlate with NPS?
- Trend: How does Q1 NPS compare to Q4 2025?

SAMPLE SIZE JUSTIFICATION:
Need n = 150 to detect ±5 point NPS change with 95% confidence
(Calculation based on baseline SD = 15, margin of error ±5)

REPORTING:
- Overall NPS score with 95% CI
- NPS by segment (chart)
- Theme analysis (verbatims grouped)
- Comparison to baseline (Q4 2025)
- Recommendations based on themes
```

### Step 6: Pilot Test and Refine
Validate survey before full launch:

```
PILOT TEST CHECKLIST:

With 10-20 respondents, test:

□ Question clarity: Do respondents understand each question?
  → Ask: "What did you understand this question to be asking?"
  → If confusion, reword

□ Answer option completeness: Can respondents express their view?
  → Look for: "Other" selections (suggests missing option)
  → Review: Open-ended responses map to existing options?
  → Fix: Add missing options or regroup

□ Response time: How long does survey take?
  → Target: 5 min (90% completion), 10 min (70% completion)
  → If >10 min: Cut questions or move lower priority to later

□ Engagement: Do respondents drop out?
  → High dropout on question X? That question is confusing
  → Fix: Reword or move lower (fatigued respondents skip)

□ Data quality: Are responses thoughtful or rushed?
  → Read open-ended responses: coherent or vague?
  → If vague: Question needed clarification

□ Skip logic: Do conditional flows work correctly?
  → Test: Pick "Yes" path and "No" path, verify right questions shown
  → Test: Mobile and desktop (flows may differ)

PILOT RESULTS:
- Average time: 6 minutes ✓
- Completion rate: 85% ✓
- Unclear question: Q3 (reword before launch)
- Missing option: Add "Other: ____" to feature ranking
- Ready for launch: Yes (after revisions)
```

## Output Template

**Survey Specification:**
```
Survey name: Q1 2026 NPS Measurement
Purpose: Track satisfaction and identify detractors for outreach
Population: Active customers (n = 50,000)
Sample: n = 150 (stratified by segment)
Timing: March 1-15, 2026
Expected duration: 5 minutes
Analysis: NPS by segment, verbatim themes, correlation with tenure

Questions: [Full survey with skip logic documented]
```

**Analysis Plan:**
```
Primary metric: NPS (target ≥45)
Secondary metrics: % Promoters, % Detractors, feature satisfaction
Segmentation: By customer segment, tenure, product usage
Reporting timeline: Results ready March 20, 2026
Decision triggers: If NPS <40, escalate to product team
```

## Quality Gates

1. **Questions unbiased**: No leading language, double-barreling, or vague terms
2. **Appropriate measurement**: Question type matches data needs
3. **Sample size justified**: Power analysis or margin of error calculated
4. **Analysis plan predetermined**: How you'll use data specified before launch
5. **Pilot tested**: With 10+ respondents, refinements made
6. **Skip logic valid**: Conditional flows avoid logic errors

## Examples

**Good: Clear, unbiased, complete**
```
NPS question: "How likely are you to recommend us to a colleague (0-10)?"
Follow-up (if <9): "What's the biggest reason you wouldn't recommend us?"
Unbiased open-ended, allows full range, drives actionable feedback
Sample: n=200, stratified by segment, power for ±2 point NPS change
Pilot: Tested with 15 respondents, adjusted 2 questions, ready to launch
Analysis: NPS calculated, segmented, compared to prior quarter, themes extracted
```

**Bad: Biased, incomplete, vague**
```
Question: "Don't you think we provide excellent service?" (leading)
Question: "How satisfied are you with our product and price?" (double-barreled)
Question: "How often do you use us?" (vague timeframe, definition)
No analysis plan, no sample size rationale, no pilot test
Results reported: "Most people said satisfied" (no actual %s, no segments)
```

## Common Mistakes

1. **Leading questions**: Priming responses by suggesting answer
2. **Vague timeframes**: "How often?" without specifying period
3. **Too many questions**: 20-question survey → 50% abandonment
4. **No skip logic**: All respondents answer questions irrelevant to them
5. **Analysis without plan**: Looking for patterns post-hoc (multiple testing bias)
6. **Misinterpreting Likert**: Averaging 1-5 scale when data is ordinal

## Anti-Patterns

1. **Surveys for everything**: Using survey to gather data you could measure behaviorally
2. **No action after feedback**: Launch survey, collect data, do nothing (erodes trust)
3. **Missing "Other" option**: Forced choice omits important feedback
4. **Too many open-ended**: Labor-intensive to analyze, lower completion
5. **Survey design by committee**: 50 people add pet questions, survey becomes unwieldy