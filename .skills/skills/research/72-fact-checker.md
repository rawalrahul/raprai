---
name: fact-checker-systematic
description: "Systematically verify factual claims through source hierarchy evaluation, cross-reference validation, confidence rating, and correction drafting to establish ground truth and counter misinformation."
category: research
difficulty: intermediate
model_boost: "Weak models rely on training data accuracy and miss source quality assessment"
---

# Systematic Fact-Checking

## Purpose
Fact-checking verifies whether specific claims match reality through systematic evidence gathering, source evaluation, and logical assessment. Unlike casual "is this true or false?" fact-checking rigorously documents source quality, distinguishes strong vs. weak evidence, identifies contested vs. settled claims, and produces confidence-rated conclusions with transparency about uncertainty. Effective fact-checking prevents misinformation spread, supports evidence-based decision-making, and establishes institutional knowledge of what's known and what's disputed.

## When to Use
- Verifying statistics, research findings, or expert claims before decision-making
- Responding to misinformation or contested claims in public/internal contexts
- Building knowledge base of verified facts on specific topics
- Evaluating credibility of information sources or speakers
- Supporting fact-dependent decisions (policy, investment, hiring, etc.)
- **Do NOT use when**: Evaluating opinions/values (not fact-checkable), conducting expert judgment synthesis (use research skill instead), or doing casual "sniff test" verification

## Instructions

### Step 1: Extract Claims to Fact-Check
Identify specific, falsifiable claims, not opinions. Examples of checkable vs. non-checkable:
- **Checkable**: "US inflation rate in 2022 was 8.0%", "Company X has 50,000 employees", "Study showed 70% of people adopt new habit within 30 days"
- **Non-checkable**: "This product is good", "Remote work is better than office", "Young people care more about social media than previous generations" (opinion statements, not facts)

Document claims with context: What's the original source making the claim? When was it made? Who is the audience? Example: "Elon Musk tweeted on March 1 that Tesla Gigafactory Texas produced 2 million vehicles in 2023."

For compound claims ("China is the world's largest economy AND fastest-growing economy"), separate into atomic facts to check individually.

Create claim checklist: List 5-10 claims prioritized by importance (decisions depend on?), controversiality (contested by credible sources?), and specificity (checkable with evidence?).

### Step 2: Establish Source Hierarchy and Credibility Criteria
Not all sources are equally credible. Establish hierarchy for evidence weight:

**Tier 1 (Strongest evidence)**:
- Primary data: Academic studies with peer review, government official statistics (census, labor department), institutional research from reputable organizations
- Primary sources: Original documents, official records, direct measurements
- Credibility factors: Peer-reviewed methodology, transparent assumptions, published source (not just assertion)

**Tier 2 (Strong evidence)**:
- Academic research without peer review, industry reports with transparent methodology, news from established outlets with fact-checking practices
- Secondary sources: Books from established academic publishers, established news organizations' reporting
- Credibility factors: Institution reputation, editorial oversight, transparency about sources

**Tier 3 (Moderate evidence)**:
- News from secondary outlets, reports from advocacy organizations, statements from recognized experts
- Credibility factors: Organizational reputation, track record of accuracy, transparency about conflicts of interest

**Tier 4 (Weak evidence)**:
- Social media claims, opinion articles, statements from unnamed sources, "industry insiders"
- Credibility factors: Anonymous, unverifiable, motivated reasoning visible

**Tier 5 (No credibility)**:
- Deliberate misinformation, conspiracy sources, statements contradicted by stronger evidence elsewhere

Define for your fact-check: What evidence sources count as Tier 1 vs. Tier 2? For example, for health claims, CDC statistics = Tier 1; medical journals = Tier 1; news reporting = Tier 2; social media = Tier 4.

### Step 3: Conduct Systematic Evidence Search
For each claim, search Tier 1-2 sources first:

**For statistics** ("China's population is 1.4 billion"):
- Check official source: UN World Population Prospects, national statistical agencies. Google Scholar, census data
- Compare multiple official sources: Do they align? If diverge, document discrepancy (measurement date? definition difference?)
- Check for dated information: When was statistic measured? Is it current? (2020 vs. 2024 data shows different picture)
- Look for methodological notes: How was statistic gathered? Any limitations?

**For research findings** ("70% of people form new habits within 30 days"):
- Find original study: What journal? Who conducted it? Sample size? Methodology? Don't rely on popular article summarizing study; read original study
- Check study quality: Peer-reviewed? What's the study design (RCT, observational, survey)? Any conflicts of interest? Limitations section?
- Check replication: Has study been replicated? Do other studies support or contradict finding?
- Check citation: Is study widely cited by other researchers or largely ignored? (Citation count suggests research community acceptance, though not always indicator of truth)

**For historical claims** ("Event X happened on date Y"):
- Primary sources: Contemporary documents, official records, eyewitness accounts
- Scholarly consensus: What do history textbooks and academic historians agree on? Disagreement between reputable sources suggests claim is contested
- Corroborate with multiple sources: One account sufficient? Or do you need 2-3+ independent sources confirming?

**For expert claims** ("Expert X says technology Y will become mainstream"):
- Expert credential: Is X actually an expert? What's their track record predicting trends?
- Bias: Does X have financial interest in prediction coming true? (Prediction from expert selling product is weaker evidence than unbiased expert)
- Compare to consensus: What do other experts in field say? Is this expert outlier or mainstream view?

Search strategy:
1. Use Google Scholar for academic research (filter by recent, peer-reviewed)
2. Check government/institutional databases (CDC.gov, BLS.gov, UN.org)
3. Check established news fact-checking sites (Snopes, FactCheck.org, PolitiFact for politics)
4. Search domain-specific databases (PubMed for medical claims, Scopus for research)
5. Assess source bias: Is source motivated to support/attack claim?

### Step 4: Evaluate Source Quality for Each Piece of Evidence
For each source found, rate quality and credibility:

**Peer review status**: Was evidence published in peer-reviewed venue? If not, why? (Breaking news legitimate reason; uncontroversial claim in journal acceptable; controversial finding in non-reviewed source suspicious)

**Author credentials**: Who conducted research? Academic institution, research organization, or unknown source? Track record of accuracy?

**Methodology transparency**: Are assumptions documented? Sample size stated? Limitations acknowledged? Transparent methodology = more credible. Hidden methodology = suspicious.

**Conflict of interest**: Does author benefit from claim being true? (Researcher employed by company making product they study recommending = conflict)

**Corroboration**: Do other credible sources reach same conclusion? Unique finding (only one source) requires stronger evidence quality.

**Date**: When was evidence produced? Still current? (2010 technology claim may be outdated by 2024)

Create source evaluation matrix for each claim documenting 3-5 key sources and their credibility scores.

### Step 5: Identify Contested vs. Settled Claims
Determine whether claim is scientifically settled or actively contested:

**Settled claims** (broad scientific/expert consensus, evidence highly concordant):
- Examples: "Earth is round", "Vaccines prevent disease", "Climate is warming"
- Evidence: >95% of experts agree, multiple independent lines of evidence support, scientific consensus documented in major reports
- Treatment: These don't require extensive evidence; cite consensus and strongest evidence; note that despite consensus, small scientific disagreement exists but is fringe

**Actively contested claims** (legitimate expert disagreement, evidence mixed):
- Examples: "Optimal retirement savings rate is X%", "Technology Y will replace Z", "Policy intervention X produces outcome Y"
- Evidence: Credible experts on both sides, studies supporting multiple positions, causation disputed
- Treatment: Present evidence for multiple positions; note contestation explicitly; avoid false balance (don't treat fringe view as equally credible as mainstream); acknowledge uncertainty

**Fringe claims** (contradicted by overwhelming evidence, supported only by non-credible sources):
- Examples: "Vaccines cause autism" (contradicted by multiple large studies), "Moon landing was faked" (contradicted by independent verification)
- Evidence: Only fringe/ideological sources support; mainstream sources reject with strong evidence
- Treatment: Clearly identify as contradicted; cite strongest contradicting evidence; brief explanation of how misinformation spread; don't give fringe excessive credibility

### Step 6: Assess Confidence Rating
Rate confidence in conclusion based on evidence quality and consistency:

**High confidence (90%+)**: Multiple Tier 1 sources agree; settled scientific consensus; no credible contradictory sources; claim specific and measurable.
- Examples: "US median household income in 2023 was $74,000" (Census Bureau official statistic)

**Moderate-high confidence (70-89%)**: Multiple Tier 2 sources agree; Tier 1 source supports but limited evidence; some minor contradictions from non-credible sources.
- Examples: "Remote work increases productivity for knowledge workers" (multiple studies support; some contrary findings but weaker)

**Moderate confidence (50-69%)**: Evidence mixed from credible sources; contested claim with arguments on both sides; some Tier 2 sources support, others disagree.
- Examples: "Long-term remote work requires more intentional team-building" (some research support, some contradictions, reasonably contested)

**Low confidence (30-49%)**: Limited credible evidence; claim not well-studied; evidence contradicts as often as supports; or significant uncertainty in evidence quality.
- Examples: "Artificial intelligence will replace 50% of jobs by 2030" (speculation, not well-established evidence)

**Very low confidence (<30%)**: Primarily non-credible sources; contradicted by stronger evidence; false claim identified.
- Examples: "Vaccines cause autism" (multiple large studies contradict; claim comes from retracted study and non-credible sources)

Document confidence rating with reasoning: What sources support? What confidence issues (limited evidence, dated, methodological concerns)? What contradicts?

### Step 7: Draft Fact-Check Correction
Write clear, evidence-based response to claim:

**Structure for settled true claims**:
"Claim is accurate. [Brief evidence summary]. [Strongest evidence citation]. No credible sources contradict this finding."

**Structure for settled false claims**:
"Claim is false. Evidence shows [opposite]. [Multiple evidence sources support correct version]. Original claim came from [source], which [explanation of why source unreliable]. Myth spread because [sociological reason], but has been thoroughly contradicted."

**Structure for contested claims**:
"Claim is contested among experts. [Evidence supporting claim] supports it. However, [evidence against] contradicts it. [Expert position] is majority view, while [alternative expert position] is minority position. The disagreement reflects [fundamental uncertainty or different values/assumptions]."

**Avoid**:
- Ambiguous language ("might be true" – if uncertain, state confidence level explicitly)
- Strawman arguments (addressing weaker version of claim while ignoring strong version)
- False balance (treating fringe view as equally credible as mainstream without evidence)
- Ad hominem attacks on sources (focus on evidence quality, not personal attacks)

**Include citations**: Link to strongest evidence sources; provide DOI or URLs to primary sources; note date evidence accessed.

### Step 8: Address Misinformation Narratives
Understand how misinformation spreads; address root causes:

**Why does misinformation spread**?
- Cognitive bias: People believe claims confirming existing beliefs (confirmation bias)
- Emotional resonance: Claims triggering fear, outrage, or hope spread faster
- Source confusion: People forget source of information; remember claim
- Complexity: Falsifying simple claim is harder than correcting nuanced truth
- Repeated exposure: Hearing false claim multiple times increases belief

**Counter-strategies**:
- Pre-bunking: Inoculate audiences against misinformation by teaching how it spreads before exposure
- Repeated truth: Counter misinformation with accurate version repeated multiple times (truth repetition overcomes false claim repetition)
- Address motivation: Explain why claim is believed (emotional appeal) even as correcting it
- Provide alternative explanation: Give people alternative narrative explaining observations that motivated misinformation
- Cite credible sources: Source credibility matters; corrections from credible sources more persuasive than from partisan sources

Example: If claim is "COVID vaccines have killed millions of people" (false; mortality data contradicts), address as:
- Why believed: Fear of new vaccines, distrust of government/pharma, emotional response to real vaccine side effects
- Counter: Present actual safety data from multiple countries (settled, not contested claim); acknowledge real but rare side effects exist; explain how misinformation conflates causation with coincidence
- Alternative narrative: "Vaccines have side effects, but serious ones are rare [X in 1 million] vs. disease mortality [Y in 1 million]"

### Step 9: Document Fact-Check Methodology
Record how fact-check was conducted to enable verification:

**Questions answered**:
- What claim was fact-checked? (Exact quote if available, with source)
- What sources were consulted? (List with credibility rating)
- What evidence was found? (Summary for and against claim)
- What's the confidence rating and why?
- Who conducted the fact-check? (Credential, potential bias)
- When was fact-check completed? (Important for time-sensitive claims)

Create fact-check summary document showing:
- Original claim with source
- Fact-check conclusion (true/false/contested with confidence rating)
- Evidence summary (1 paragraph for each major piece of evidence found)
- Full citations with links
- Methodology notes (what sources checked, any limitations)

### Step 10: Create Fact-Check Database and Updates
Build systematic knowledge base for reference:

**Fact-check repository**:
- Claim: [specific, exact wording]
- Status: True/False/Contested
- Confidence: [90%+ / 70-89% / 50-69% / etc.]
- One-line summary: [concise conclusion]
- Evidence: [3-5 key sources with links]
- Full fact-check: [detailed explanation]
- Date checked: [when]
- Related facts: [linked fact-checks on related topics]

**Regular updates**:
- Check if new evidence emerged: For contested claims, are researchers reaching new consensus?
- Update for time-sensitive facts: "US inflation rate is 8%" true for 2022, outdated for 2024
- Note retracted studies: If original source is retracted, update fact-check with explanation
- Track narrative evolution: How did misinformation change over time? Update as narrative evolves

## Output Template

### Claim Being Fact-Checked
**Original claim**: [Exact quote]
**Source**: [Who made claim, when, in what context]
**Claim category**: [Political, scientific, health, economic, historical]

### Fact-Check Conclusion
**Rating**: [TRUE / FALSE / CONTESTED / UNVERIFIABLE] (confidence: [%])
**One-line summary**: [Concise conclusion]

### Evidence Summary

**Evidence supporting claim**:
- [Source 1, credibility rating]: [What it says, key findings]
- [Source 2, credibility rating]: [What it says, key findings]

**Evidence contradicting claim**:
- [Source 1, credibility rating]: [What it says, contradictory finding]
- [Source 2, credibility rating]: [What it says, contradictory finding]

**Expert consensus**:
[If settled] Mainstream experts agree: [consensus position]. Credible dissent: [none/minority position]
[If contested] Experts divided: [majority position % of experts]; [minority position % of experts]

### Detailed Fact-Check

[1-2 paragraph explanation of what claim means, why it matters, what's at stake in the truth]

[Detailed evidence section explaining strongest evidence for and against; addressing any nuance or complexity]

[If false] Why did this misinformation spread? [Explanation of narrative appeal, emotional resonance]

### Source Citations
1. [Full citation], [URL], [accessed date]
2. [Full citation], [URL], [accessed date]
[5-10 key sources with full citations]

### Confidence Assessment
- **Confidence level**: [%] [HIGH / MODERATE / LOW]
- **Uncertainty sources**: [What would change assessment? What's ambiguous?]
- **Updated**: [When was this last verified?]

## Quality Gates

1. **Claim extracted accurately**: Original claim quoted precisely with source, date, and context documented; complex claims separated into atomic facts
2. **Source hierarchy established**: Clear criteria for Tier 1-5 sources defined; relevant to domain (medical claims vs. economic claims use different source hierarchies)
3. **Tier 1 sources searched**: Primary data, peer-reviewed sources, official statistics consulted first; search strategy documented showing what sources were checked
4. **Source quality evaluated**: Each significant source rated on peer review status, author credentials, methodology transparency, conflict of interest, corroboration
5. **Contested vs. settled distinction made**: Claim identified as settled (consensus, strong evidence), contested (legitimate disagreement), or fringe (contradicted, no credible support)
6. **Confidence rating justified**: Rating (90%+, 70-89%, 50-69%, 30-49%, <30%) with explicit reasoning about evidence strength and remaining uncertainty
7. **Multiple sources cited**: Minimum 3 credible sources cited for conclusion; for contested claims, sources on multiple sides of debate cited
8. **Correction drafted clearly**: Fact-check conclusion written in accessible language; avoids jargon; addresses likely audience misconceptions; provides alternative explanation if applicable
9. **Misinformation narrative addressed**: For false claims, explanation of why misinformation spreads; counter-strategies suggested; not just "this is false"
10. **Full documentation transparent**: Methodology notes show what was checked, when, by whom; limitations acknowledged; updates noted as new evidence emerges

## Examples

### Good Fact-Check (True)
**Claim**: "US inflation rate in 2022 was 8.0%"
**Source**: Various news articles, January 2023
**Conclusion**: TRUE (confidence 99%)

**Evidence**: U.S. Bureau of Labor Statistics reported Consumer Price Index inflation of 8.0% for 2022 (December 2021 to December 2022, annual rate). This is published data, not estimate. Federal Reserve, World Bank, and major news organizations all cite same figure.

**Why high confidence**: Official government statistic from BLS, which has decades of credibility and transparent methodology. No credible source disputes this figure. Measurement method well-established. All international observers report consistent figure.

### Good Fact-Check (False)
**Claim**: "Vaccines cause autism"
**Original source**: Wakefield et al. 1998 study
**Conclusion**: FALSE (confidence 99%)

**Evidence against claim**:
- Original study retracted in 2010 by journal Lancet due to ethical violations and data fraud
- Author Andrew Wakefield lost medical license due to misconduct
- 15+ large studies since involving 1.2M+ children found NO link between vaccines and autism
- Autism diagnosis trends increased before vaccine introduction and continued same rate in unvaccinated populations
- No biological mechanism identified explaining how vaccines could cause autism

**Evidence narrative**: Wakefield study claimed vaccine-autism link but had multiple problems: small sample (12 children), paid advocacy group funded study, falsified data (coerced students into conclusions). Despite major flaws, claim spread due to parent anxiety about vaccines and distrust of institutions. Repeated exposure increased belief despite contradictory evidence.

**Why high confidence**: This is settled science with overwhelming evidence from multiple large, independent studies. No credible medical organization (CDC, WHO, American Academy of Pediatrics) supports vaccine-autism link. Rare fringe anti-vaccine sources promote claim, but are contradicted by all major health authorities.

### Good Fact-Check (Contested)
**Claim**: "Remote work increases productivity for knowledge workers"
**Conclusion**: CONTESTED (confidence 60%) — evidence mixed with reasonable disagreement

**Evidence supporting claim**:
- Stanford study (Bloom et al. 2015): Remote work experiment showed 13% productivity increase, primarily from fewer distractions
- Microsoft research (2022): Remote work improved focus time, reduced interruptions in some roles
- Some workers report higher productivity with home environment (fewer commute interruptions, personalized workspace)

**Evidence contradicting claim**:
- MIT research (2023): Hybrid work shows productivity gains in focused work, but collaboration/innovation reduced by 29% when team distributed
- Yahoo case study: CEO discontinued work-from-home policy, cited declining engagement and innovation
- Some studies show productivity gains are task-dependent (routine work benefits more than collaborative work)

**Expert consensus**: No clear consensus; researchers note productivity depends on job type, company culture, and individual factors. Routine, independent work shows productivity gains remote. Collaborative, creative work shows mixed or negative productivity in full-remote settings.

**Why moderate confidence**: Evidence exists on both sides from credible sources. Productivity is complex (can't measure via single metric); studies focus on different job types; selection bias (some workers choosing remote are more disciplined). Claim is largely true for some jobs (e.g., software developer) and less true for others (e.g., new employee training, creative collaboration).

### Poor Fact-Check
- Claims no evidence found without checking multiple sources
- Relies on single source (non-peer-reviewed blog post)
- Doesn't acknowledge expert disagreement on contested claim
- Uses language "probably false" without confidence rating
- Attacks person making claim rather than evaluating evidence
- No sources cited
- Outdated evidence (cites 2010 study for 2024 claim without checking if newer evidence exists)

## Common Mistakes

1. **Confusing "no evidence found" with "false claim"**: Just because you can't find support doesn't mean claim is false. Burden of proof differs: extraordinary claims (contradicting consensus) require strong evidence to be true; ordinary claims require evidence to be false. Solution: Distinguish "not proven" from "disproven." If claim is unsupported but plausible, label as "unverifiable" or "unsupported," not "false," unless evidence actively contradicts it.

2. **Over-weighting recent evidence**: Latest study published contradicts decades of consensus. Treat latest finding as potentially important, but one study doesn't overturn consensus. Solution: Check if recent finding is replicable, whether other experts agree it changes consensus, whether effect size is meaningful. Consensus changes when pattern of evidence shifts, not from single study.

3. **Relying on secondary sources without checking original**: News article claims "Study shows X." Read original study; news article mischaracterized or oversimplified finding. Solution: For important claims, always check original source before citing. Compare news summary to what study actually says. Don't cite news article's interpretation; cite actual finding.

4. **False balance on contested claims**: Presenting fringe view as equally credible as mainstream view. Example: "Some experts say vaccines cause autism; others say they don't" implies both are equally credible. Solution: If claim is contested, present evidence on both sides but note credibility difference (mainstream majority view vs. fringe minority view). Avoid equal weight framing; specify "consensus is X, minority view is Y."

5. **Ignoring methodological flaws in supporting sources**: Source agrees with your claim; you cite it. Source has major methodological flaws (small sample, self-reported data, no control group, obvious conflicts of interest). Solution: Evaluate source quality not just agreement with claim. Don't assume agreement means credible. Weaker evidence supporting your conclusion is still weak.

6. **Fail to track time-sensitive updates**: Fact-check stated "COVID vaccines reduce hospitalization by X%" accurate for Delta variant. Six months later, new variant emerges with different effectiveness. Old fact-check is outdated. Solution: For time-sensitive claims, note explicitly when evidence applies. Check periodically if new evidence emerged (especially for claims about evolving situations). Update fact-checks as evidence changes.

## Anti-Patterns

1. **Motivated reasoning in source selection**: Unconsciously select sources supporting your prior belief; ignore contradicting sources. "I believe X, found sources supporting X, fact-check concluded X true." Solution: Deliberately search for strongest evidence against your expected conclusion. If you can't find credible evidence contradicting your conclusion, increase confidence slightly. If you find strong contradictory evidence, update conclusion.

2. **Treating prediction/speculation as fact-checkable claim**: "AI will replace 50% of jobs by 2030." This is prediction, not fact. Fact-checks work for claims about past/present, not future. Solution: Flag future predictions as speculation. Fact-check instead whether evidence supports concern about AI job displacement (past/present data). Don't pretend to fact-check unknowable futures.

3. **Adopting tone policing**: Framing false claim as "misinformation" from bad actor. Actually, claim came from person with reasonable beliefs who encountered misinformation. Tone suggests bad faith. Solution: Distinguish claim from claimant. Some people spread misinformation unknowingly. Separate "this claim is false" from "person is deceptive." Assume good faith unless evidence of intentional deception.

4. **Silo-ing fact-checks without context**: Fact-checking isolated claim without understanding larger narrative. "X is false" correct, but fact-check doesn't address why belief in X is rising or what misconception drives it. Solution: For important fact-checks, provide context: Why do people believe this? What's the emotional or cognitive appeal? Provide alternative explanation addressing underlying concern.

5. **Responding to bad-faith requests with evidence**: Someone demands you fact-check "obvious falsehood" as Gish Gallop (throwing so many false claims at you that responding consumes all time). Spending hours fact-checking each claim when no amount of evidence would change their mind. Solution: Identify bad-faith pattern; don't fact-check demand if person clearly won't engage with evidence. Focus fact-checking effort on fence-sitters and people genuinely uncertain.

6. **Over-updating on weak evidence**: Single small study contradicts established consensus; you update your fact-check conclusion significantly. Actually, one small study shouldn't overturn consensus. Solution: Update conclusions when pattern of evidence shifts, not from isolated studies. Large studies > small studies. Replicated findings > single findings. Multiple independent researchers > single research group. Consensus from established institutions > fringe claims.
