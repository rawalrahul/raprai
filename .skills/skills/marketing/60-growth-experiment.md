---
name: growth-experiment
description: "Design and execute lean growth experiments with clear hypotheses, measurable metrics, structured implementation, success criteria, and documented learnings to systematically optimize marketing performance."
category: marketing
difficulty: intermediate
model_boost: "Fixes weak models that treat experimentation as guesswork rather than scientific hypothesis-driven process"
---

# Growth Experiment

## Purpose
Growth experiments transform gut feelings into data-backed decisions. Rather than "hoping" something works, experiments state a hypothesis, run a controlled test, measure results, and document learnings regardless of outcome. This disciplined approach compounds over time—a series of 10% improvements across different tactics adds up to 100%+ growth. It shifts team culture from "best guess" to "what does data show?" and creates institutional knowledge about what works for your specific audience, not generic best practices.

## When to Use
- Testing new marketing channels, messages, or tactics before scaling spend
- Optimizing existing performance—landing page CTR, email open rate, content engagement
- Validating assumptions about customer behavior or preferences
- Choosing between two strategic directions (should we do X or Y?)
- Debugging poor performance ("Why is our email CTR low?")
- Unblocking team decisions ("We keep debating this—let's test it")
- Building a data-driven culture where decisions are evidence-based
- **Do NOT use when**: Results must be immediate and you lack time/audience for test execution, testing would violate privacy or compliance requirements, or when there's only one sensible course of action with no real alternative to test

## Instructions

### Step 1: Formulate a Testable Hypothesis
Start with a clear hypothesis, not a vague question:

**Hypothesis framework**: "If [we change X], then [specific outcome] will improve by [Y%], because [reason/mechanism]."

**Example hypotheses**:
- "If we change email subject line from 'New feature' to 'Save your team 5 hours per week,' then CTR will increase by 25%, because specific benefit is more compelling than generic announcement."
- "If we move CTA button from bottom of page to middle of page, then conversion rate will increase by 15%, because visitors don't scroll to bottom."
- "If we target LinkedIn ads to managers instead of IC engineers, then lead quality will increase by 30%, because managers have budget and decision-making authority."
- "If we run webinar on Wednesdays instead of Tuesdays, then attendance will increase by 20%, because Wednesday is better mid-week attendance day."

**Hypothesis quality checklist**:
- Specific (not vague—"better" or "more engaging" is not specific)
- Testable (can you actually measure the outcome?)
- Based on logic (why do you think this will work? What evidence or pattern led to this hypothesis?)
- Quantified (what % improvement are you expecting? Helps define sample size needed)
- Time-bound (when will you measure results? Hours, days, weeks?)

**Bad hypotheses** (avoid these):
- "Our ads should perform better" (no specific change or metric)
- "Landing pages convert more when they're better" (circular logic)
- "People like our product more" (too vague to measure)
- "We need to test different colors" (no hypothesis about which color or why)

**Hypothesis sources** (where do good hypotheses come from?):
- **Customer feedback**: "Customers said they don't understand our pricing" → Hypothesis: Clearer pricing page increases demo requests
- **Competitive intelligence**: "Competitor's ads mention ROI calculator" → Hypothesis: ROI calculator in our CTAs increases lead quality
- **Data analysis**: "Email open rate is down 15% YoY" → Hypothesis: Subject line fatigue (we use same patterns); new subject line format increases opens
- **Team intuition** (grounded in experience): "Sales says prospects want proof of security" → Hypothesis: Security/compliance callout in hero copy increases qualified leads
- **User behavior**: "Analytics shows visitors scroll past feature section" → Hypothesis: Feature section is too far down; moving it above fold increases feature adoption

### Step 2: Identify Success Metric & Baseline
Define exactly what you're measuring and what counts as success:

**Metric selection**:
- **Primary metric**: The one thing you're directly testing. Must be:
  - Measurable (can you count it or calculate it?)
  - Attributable (can you tie it to your test, not other variables?)
  - Relevant to business goal (not vanity metric like "impressions")
  - Leading indicator (shows success before revenue impact—CTR, open rate, conversion rate, not just revenue)

**Primary metric examples**:
- Email test: Open rate or click rate (not read time; can't measure)
- Landing page test: Conversion rate or demo request rate (not bounce rate; too broad)
- Ad test: Cost per qualified lead (not impressions or clicks; need quality)
- Content test: Time on page, scroll depth, CTA click rate (not just page views)
- Channel test: Cost per acquisition, conversion rate, LTV (not just reach)

- **Secondary metrics** (watch for negative impacts):
  - If you improve CTR but decrease quality, overall conversion might go down
  - If you improve email open rate via spammy subject line, unsubscribe rate goes up
  - Examples: unsubscribe rate, bounce rate, refund rate, churn rate, support tickets

- **Baseline measurement**:
  - Before running test, measure current performance (control group or historical baseline)
  - Email subject line test: Baseline CTR is 5.2%
  - Landing page test: Baseline conversion rate is 8.3%
  - Ad test: Baseline cost per lead is $85
  - Without baseline, can't measure improvement

- **Success threshold** (what's a win?):
  - Statistical significance: 2+ weeks or 100+ conversions minimum (not just 1 week or 10 conversions)
  - Minimum improvement: What's the smallest improvement worth the effort to implement?
    - Email test: 2% CTR improvement might not justify change
    - Landing page: 5% conversion improvement might be worth it
    - Ad test: 10% cost per lead improvement worth it
  - Business impact: Does improvement actually matter to bottom line?
    - "CTR improved 2% but sample was 50 people" = Not significant
    - "CTR improved 2% across 50,000 emails" = Significant business impact

### Step 3: Design Test Structure
Plan how you'll run the test:

**Test methodology** (pick one based on situation):

1. **A/B test** (split traffic; change one variable):
   - 50% audience sees Control (current version)
   - 50% audience sees Variation (new version)
   - Everything else held constant
   - Best for: Email subject lines, ad copy, button text, one landing page element
   - Duration: Until statistical significance (typically 1-2 weeks for meaningful sample)

2. **Multivariate test** (change multiple variables simultaneously):
   - Version A: Current version
   - Version B: Change subject line only
   - Version C: Change CTA button only
   - Version D: Change both
   - More complex; requires larger sample size
   - Best for: When multiple elements feel related and you want to test interaction effects

3. **Cohort test** (time-based, not random split):
   - Week 1: All users experience Control
   - Week 2: All users experience Variation
   - Simpler; requires clear understanding that timing won't confound results
   - Risk: Outside variables could influence results
   - Best for: When random splitting isn't possible (e.g., enterprise sales calls)

4. **Geographic or segment test** (different groups experience different versions):
   - East coast sees Variation A; West coast sees Control
   - Premium customers see Variation; free customers see Control
   - Allows testing with existing traffic but requires careful analysis
   - Risk: Segments might behave differently for reasons unrelated to test
   - Best for: When you know segments respond differently and want segment-specific learning

**Sample size calculation** (rule of thumb; use online calculator for precise):
- Smaller baseline conversion rate = larger sample needed
- 5% baseline conversion rate: Need ~5,000 total visitors for statistical significance
- 20% baseline conversion rate: Need ~1,000 total visitors
- If you can't reach sample size in reasonable time, wait and batch tests

**Test duration**:
- Run long enough to reach sample size (if needed 5,000 visitors and get 200/day, run 25 days)
- But not so long that external variables confound results (seasonal, news event, product change)
- Minimum 1 week (capture day-of-week variation); typically 2-4 weeks for email/ad tests

**Test setup checklist**:
- [ ] Control and variation are identical except for one variable
- [ ] Randomization is actually random (not "first 50% get A, second 50% get B")
- [ ] Both variations are live simultaneously (not sequential)
- [ ] Tracking is set up correctly (can you measure metric accurately?)
- [ ] Sample size threshold defined before test starts (avoid moving goalposts)
- [ ] Secondary metrics defined and tracked

**Example test setup**:

Email subject line test:
- Sample: Next 10,000 email sends
- Control: "Subject line: 'New feature announcement'" (historical performance: 4.2% CTR)
- Variation: "Subject line: 'Save your team 5 hours per week'" (hypothesis: specific benefit drives higher CTR)
- Primary metric: CTR (click rate)
- Secondary metric: Unsubscribe rate (make sure we don't anger audience)
- Success threshold: Variation reaches 5.2%+ CTR (23% improvement) OR reaches statistical significance at any improvement
- Duration: 2 weeks (time for distribution of all 10,000 emails)
- Measurement: Email platform reports CTR for each subject line after 72 hours

### Step 4: Execute Test with Discipline
Run test as designed; avoid midstream changes:

**Pre-launch checklist**:
- [ ] Creative assets final and approved
- [ ] Tracking and measurement verified with analytics team
- [ ] Team notified of test (prevent accidents like sending both versions)
- [ ] Success criteria communicated (everyone knows what we're measuring)
- [ ] Expected outcome documented (what do we think will happen?)

**During test execution**:
- **Daily monitoring**: Check for technical issues (is tracking working? is variation live?)
- **Don't peek too early**: Resist urge to call winner on day 2 or 3 (premature conclusions lead to wrong decisions)
- **Track external variables**: Note if major news or company announcement could confound results
- **Watch secondary metrics**: If CTR improves but unsubscribe rate triples, variation may not be worth it
- **Don't change variables mid-test**: If you tweak subject line after day 5, you've invalidated the test

**Common execution mistakes** (avoid these):
- Running test with unequal split (40/60 instead of 50/50; makes analysis harder)
- Pausing test mid-way to "reallocate budget" to winning version (reduces sample size; introduces selection bias)
- Changing variation after test starts (invalidates results)
- Running test with external variables not controlled (campaign runs simultaneously; product changes; competitor announcement; confounds results)

### Step 5: Measure Results & Statistical Significance
Analyze data with care; not all improvements are real:

**Statistical significance** (is the improvement real or just random variation?):
- Even if Variation wins, could be chance
- Statistical significance tests whether winner is reliable or just luck
- **Rule of thumb**: Need 80-100+ conversions per variation minimum for reliability
- Use online calculator (e.g., "A/B test significance calculator") to confirm
  - Input: Conversion rate for Control, conversion rate for Variation, sample size
  - Output: Confidence level (95% confidence = results reliable; <95% = too much uncertainty)

**Example analysis**:
- Control (original subject line): 420 clicks out of 10,000 sends = 4.2% CTR
- Variation (benefit-focused subject line): 512 clicks out of 10,000 sends = 5.12% CTR
- Improvement: 0.92 percentage points (22% relative improvement)
- Statistical significance: 98.5% confidence this isn't random variation
- Conclusion: Variation is statistically significant; improvement is real

**When variation doesn't win** (results flat or Control wins):
- Don't dismiss learning; still gather insights
- Why didn't variation win? Bad hypothesis? Execution issue? Segment mismatch?
- Document learning; move to next test

**Avoid these analysis mistakes**:
- "Let me run it 2 more weeks to see if winner changes" (moving goalposts; introduces selection bias)
- "The improvement is small (1%) but I'll implement anyway" (small improvements compound, but also small variations can be random)
- "We had 50 conversions per variation" (too small; need 100+)
- "We ran test for 1 week" (too short; might miss day-of-week effects)

### Step 6: Document Learnings & Implement Winner
Record what you learned; build institutional knowledge:

**Experiment documentation** (save in shared place; build knowledge base):
```
Experiment ID: EXP-2026-001
Date: March 2026
Channel: Email
Test Type: A/B test (subject line)

Hypothesis:
"If we change email subject line from generic announcement
to specific benefit, then CTR will increase by 20%, because
specific benefits are more compelling than generic announcements."

Control:
Subject line: "New feature announcement"
Historical CTR: 4.2%

Variation:
Subject line: "Save your team 5 hours per week"

Results:
Control CTR: 4.2% (420 clicks / 10,000 sends)
Variation CTR: 5.12% (512 clicks / 10,000 sends)
Improvement: 0.92 pp (22% relative improvement)
Statistical significance: 98% confidence

Decision: Implement variation

Learnings:
1. Specific benefits outperform generic announcements
2. This pattern held across all audience segments tested
3. Unsubscribe rate was flat (no negative impact)

Next test:
Test which specific benefit (time saved vs. money saved vs.
quality improvement) performs best in follow-up email series

Implementation:
- Update email template for all future sends
- Expected monthly impact: ~4,600 additional clicks (from 5K additional emails/month)
```

**Implementation guidance**:
- If test won, implement variation immediately (don't wait for next campaign cycle)
- Scale the implementation: If email subject line won, apply to all future sends of same type
- Update documentation and training if it affects team workflows
- Create follow-up test (if benefit was compelling, what if we emphasized it more?)

**Learning documentation** (start building knowledge base):
- "Subject lines with specific benefit (time saved, money saved) outperform generic announcements by 15-25%"
- "Benefit-focused subject lines work across all customer segments (SMB, mid-market, enterprise)"
- "Unsubscribe rate is not negatively impacted by benefit-focused subject lines"
- "Test hypothesis was correct; specific benefits > generic"

### Step 7: Build Test Roadmap & Iterate
Create systematic testing plan; experimentation compounds:

**Testing roadmap** (for next 3 months):
- Week 1-2: Subject line optimization (highest impact, fast execution) → Expected 15-20% CTR improvement
- Week 3-4: CTA button text test (what action language works?) → Expected 10-15% conversion improvement
- Week 5-6: Landing page headline test (does value prop land?) → Expected 8-12% conversion improvement
- Week 7-8: Email frequency test (how many emails per week before unsubscribe rate spiked?) → Expected 20% in throughput
- Week 9-10: Audience segment test (different segments respond to different messages?) → Inform future segmentation

**Testing velocity**:
- Aim to run 4-8 experiments per quarter
- Start with high-impact, fast-execution tests (email subject lines, ad copy)
- Graduate to bigger tests (landing page redesign, new channel)
- Layer learning on learning (test 1 informs test 2)

**Compounding impact**:
- Test 1: 15% improvement
- Test 2: 10% improvement
- Test 3: 8% improvement
- Test 4: 12% improvement
- Cumulative: 1.15 × 1.10 × 1.08 × 1.12 = 1.54 = 54% total improvement over baseline

**Preventing test fatigue**:
- Not every idea gets tested (filter for high-impact, tractable ideas)
- Batch related tests (if subject lines win, then test body copy; if landing page headline wins, then test sub-headline)
- Share learnings across team (other channels can apply learnings from email tests)
- Celebrate wins publicly (builds momentum and experimentation culture)

## Output Template

**Experiment Design Document:**

**Hypothesis:**
"If [specific change], then [metric] will improve by [X%], because [reason]."

**Baseline & Success Criteria:**
- Current metric: X%
- Target metric: X%
- Statistical significance required: 95%+
- Minimum sample size: [Number]

**Test Design:**
- Control: [Description of current version]
- Variation: [Description of test version]
- Duration: [Weeks]
- Audience: [Who is included?]

**Primary Metric:**
- Name: [Metric name]
- How measured: [Definition and calculation]

**Secondary Metrics:**
- [Metric name] - watch for negative impact

**Results** (fill in after test runs):
- Control: [X% or X outcome]
- Variation: [X% or X outcome]
- Improvement: [Y% relative improvement]
- Statistical significance: [Z% confidence]

**Decision:** Implement / Do Not Implement / Inconclusive

**Learnings:**
1. [Key insight]
2. [Key insight]
3. [Key insight]

**Follow-up test:**
[What to test next based on this learning]

## Quality Gates

1. **Clear hypothesis**: Hypothesis is specific, testable, and grounded in logic (not a vague question)
2. **Realistic metric**: Primary metric is measurable, attributable to test, and relevant to business goal
3. **Adequate sample size**: Plan includes sample size large enough for statistical significance (100+ conversions per variation)
4. **Control integrity**: Control and variation differ only in tested variable; all else is identical
5. **Measurement setup**: Tracking is configured correctly; baseline established before test runs
6. **Results interpretation**: Analysis includes statistical significance check; not just "one version is higher"
7. **Learning documentation**: Results are recorded with context and insights; shared with team
8. **Follow-up plan**: Next test identified based on learnings; experimentation continues

## Examples

### Good Example: Email Subject Line Test

**Hypothesis**: "If we use benefit-focused subject lines mentioning specific time savings, then CTR will increase by 20%, because specific benefits are more compelling than generic announcements."

**Control**: "New feature released: Workflow automation"
**Variation**: "Save 10 hours per week with workflow automation"

**Baseline**: 4.2% CTR (420 clicks / 10,000 sends)
**Target**: 5.0% CTR or higher (18%+ improvement)

**Results**:
- Control: 4.2% (420 clicks)
- Variation: 5.3% (530 clicks)
- Improvement: 1.1 pp (26% improvement)
- Significance: 97.5% confidence (statistically significant)

**Decision**: Implement variation across all workflow automation emails

**Learnings**:
1. Specific benefit (hours saved) outperforms feature announcement
2. Works across all segments (SMB, mid-market, enterprise)
3. Unsubscribe rate unchanged (no downside)

**Follow-up test**: Which benefit language wins—"save time," "save money," or "improve quality"?

### Bad Example: Uncontrolled, Unmeasured Change

**Situation**: Manager says "Let's try mentioning our ROI calculator in emails"

**What happens**:
- No hypothesis or expected outcome defined
- Someone updates a few random emails to include ROI calculator mention
- No baseline measurement established
- Results measured vaguely ("Seems like people clicked more")
- No statistical analysis
- Change implemented based on gut feeling, not data
- Learning: None. Next iteration has no basis.

**Result**: Unmeasured change makes it into standard template. 6 months later, someone questions whether it's actually valuable. No one remembers why it was added. Email effectiveness unclear.

## Common Mistakes

1. **Hypothesis too vague**: "We should test a new headline" (which headline? why? what outcome?). Solution: Formulate specific hypothesis with expected outcome and reason.

2. **Wrong metric**: Testing time-on-page when you care about conversions. Low time-on-page might indicate easy quick decision or confusing page. Solution: Pick primary metric aligned to business goal (conversion, not engagement vanity metric).

3. **Insufficient sample size**: Running test for 1 week with only 50 conversions per variation, calling winner on small difference. Solution: Wait for 100+ conversions per variation; run statistical significance test.

4. **Multiple simultaneous changes**: Testing new headline + new CTA + new color + new image all at once. Can't tell which drove the result. Solution: A/B test; change only one variable.

5. **Peeking at results mid-test**: Checking results on day 3, seeing variation winning, implementing immediately. Random variation early looks like winner. Solution: Don't peek; commit to sample size and duration before launching.

6. **Not documenting results**: Completing test, getting result, forgetting to save learning. Next person tests same thing again. Solution: Standardized template; shared folder; quarterly knowledge base review.

## Anti-Patterns

1. **The HiPPO (Highest Paid Person's Opinion) Override**: Test shows one result; executive prefers other outcome and implements anyway. Kills experimentation culture. Solution: Leadership commits to trusting test results before test runs; decision tree decided in advance.

2. **The Sample Size Chasing Pattern**: Test isn't winning quickly, so extend duration indefinitely hoping to eventually win. Introduces external variables; wastes time on marginal improvement. Solution: Commit to sample size and duration upfront; if doesn't win, move to next test.

3. **The Negative Result Burial Pattern**: Test shows variation loses; team embarrassed and hides results. Learning opportunity lost. Solution: Celebrate negative results ("Now we know X doesn't work"); document learning; move to next test.

4. **The Micro-Optimization Spiral**: Testing 47 variations of button colors and copy, gaining 1-2% improvements, while ignoring major structural issues (is positioning right? is audience right?). Diminishing returns. Solution: Test bigger variables first (targeting, positioning, offer); then optimize small elements.

5. **The Measurement Blind Spot**: Can't tell if test worked because tracking is broken, or metric is poorly defined. Wastes time running test with bad data. Solution: Verify tracking before test launches; run test with IT/analytics to confirm setup.

6. **The Single Test Mentality**: Running one test, getting one result, thinking that's universal truth. "Subject lines with benefits win" based on one test. Solution: Replicate winning tests across different channels/audiences; build pattern, not individual datapoints.
