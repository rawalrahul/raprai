---
name: literature-review-systematic
description: "Conduct systematic literature reviews with structured search strategies, inclusion/exclusion criteria, evidence synthesis matrices, and identified research gaps to produce comprehensive knowledge synthesis."
category: research
difficulty: advanced
model_boost: "Weak models struggle with systematic methodology and synthesis logic"
---

# Systematic Literature Review

## Purpose
A systematic literature review synthesizes existing research evidence through a transparent, reproducible methodology. Unlike narrative reviews, it applies rigorous inclusion/exclusion criteria, systematically searches multiple databases, evaluates study quality, and synthesizes findings using explicit frameworks. This prevents bias, identifies research gaps, and establishes an authoritative knowledge foundation for decision-making, policy development, or future research agendas.

## When to Use
- Establishing evidence base for a research question or policy decision
- Identifying research gaps and framing future studies
- Synthesizing divergent findings across studies
- Supporting systematic scoping or meta-analysis
- Updating existing evidence bases (living reviews)
- **Do NOT use when**: Quick opinion summaries are needed, exploring exploratory narratives without inclusion criteria, or when time constraints prevent rigorous methodology

## Instructions

### Step 1: Define Research Question and Protocol
Develop a PICO framework (Population, Intervention, Comparison, Outcome). Write a specific, focused question: "In [population], does [intervention] compared to [comparison] affect [outcome]?" Document protocol in PROSPERO or equivalent registry. Include: scope boundaries, study design eligibility, date ranges, language restrictions, and primary/secondary outcomes. This prevents question-drift and reporting bias.

### Step 2: Design Inclusion/Exclusion Criteria
Establish explicit criteria before searching. Examples:
- **Include**: Peer-reviewed articles, published 2015-2024, English language, randomized trials + observational studies
- **Exclude**: Opinion pieces, editorials, studies measuring only surrogate endpoints, dissertations without publication

Create a decision tree with specific operationalizations. Pilot-test criteria on 50 abstracts with multiple reviewers to ensure clarity. Use Cohen's kappa to measure inter-rater reliability (target >0.60).

### Step 3: Conduct Systematic Database Search
Search minimum 3-5 databases (PubMed, Scopus, Web of Science, EMBASE, domain-specific databases). Develop search strategies using controlled vocabulary (MeSH, EMTREE) + free text keywords. Document exact search strings including Boolean operators, date ranges, field restrictions. Example: "(mental health OR psychiatric) AND (social media OR digital) AND (systematic review OR meta-analysis) NOT editorials" in PubMed 2015-2024.

Use citation tracking (forward/backward) to identify missed studies. Register final search date. Document search yield: initial results, after deduplication, abstracts screened, full texts reviewed, final inclusions.

### Step 4: Screen Studies Using Staged Process
**Stage 1 (Abstract screening)**: Two independent reviewers screen all titles/abstracts against inclusion criteria using screening software (DistillerSR, Covidence). Resolve disagreements through discussion or third reviewer. Document reasons for exclusion.

**Stage 2 (Full-text review)**: Retrieve full texts of potentially eligible studies. Screen against detailed criteria. Document reasons for exclusion (study design, outcome measures, population, etc.). Maintain PRISMA flow diagram throughout.

### Step 5: Extract Data Using Standardized Forms
Create detailed extraction template including: study characteristics (design, setting, dates), population (n, demographics), intervention/comparison details, outcome measures, results (effect sizes, p-values, confidence intervals), quality assessment items, funding sources, conflicts of interest.

Two reviewers independently extract data from all studies. Verify accuracy on 10% sample. Record authors' raw data directly; avoid calculations from reported statistics when possible. Track extraction completion date.

### Step 6: Assess Study Quality Using Validated Tools
Select appropriate quality assessment tool by study design:
- **RCTs**: Cochrane Risk of Bias (ROB-2)
- **Observational**: ROBINS-I or Newcastle-Ottawa Scale
- **Qualitative**: CASP Qualitative Checklist
- **Diagnostic**: QUADAS-2

Rate bias domains (selection, performance, detection, attrition, reporting) on standardized scales. Two reviewers assess quality independently. Avoid excluding studies based on quality; instead stratify synthesis by quality level.

### Step 7: Create Evidence Synthesis Matrix
Organize studies in comprehensive table with: citation, study design, population, intervention, comparison, outcomes, effect sizes, study quality. Use standardized outcome formatting (SMD, RR, OR with 95% CI). Identify study heterogeneity: clinical (population, intervention), methodological (design, measurement), statistical (effect size variation).

### Step 8: Synthesize Findings and Identify Gaps
**If homogeneous evidence**: Conduct meta-analysis if ≥10 similar studies with comparable outcomes. Calculate pooled effect sizes, assess heterogeneity (I²), examine publication bias (Egger test, funnel plots). Perform sensitivity analyses (excluding low-quality studies, different outcome definitions).

**If heterogeneous evidence**: Conduct narrative synthesis describing patterns, effect size ranges, consistency across subgroups (by population, intervention intensity, outcome measurement). Use vote-counting cautiously; prioritize effect sizes. Identify modifying factors (what works for whom, under what conditions).

**Gap identification**: Document:
- Populations understudied (e.g., elderly, ethnic minorities)
- Intervention variations not tested
- Long-term outcome data gaps (>5 years follow-up)
- Outcome measures needed (e.g., quality of life, economic outcomes)
- Geographic/clinical context gaps
- Study design limitations (minimal RCTs vs. observational)

### Step 9: Assess Certainty of Evidence (GRADE)
Rate confidence in effect estimates:
- **High**: Consistent RCT evidence, minimal bias
- **Moderate**: RCTs with limitations or observational evidence, generally consistent
- **Low**: Observational studies, inconsistent findings, significant limitations
- **Very Low**: Case reports, expert opinion, conflicting results

Document reasons for downgrading (study limitations, inconsistency, imprecision, indirectness, publication bias).

### Step 10: Report Using PRISMA Checklist
Follow PRISMA 2020 guidelines for transparent reporting. Include: PRISMA checklist, protocol registration, search strategies, PRISMA flow diagram, characteristics of included studies table, risk of bias summary figures, synthesis approaches, certainty of evidence assessment, discussion of implications for practice/research.

## Output Template

### [Research Question]
[PICO framework with specific question]

### Search Strategy Summary
- **Databases searched**: [3+ databases, dates]
- **Total records**: [number]; **After deduplication**: [number]; **Full texts reviewed**: [number]; **Included studies**: [number]
- **Search strategy**: [URL to appendix with full search strings]

### Inclusion/Exclusion Criteria
- **Population**: [specification]
- **Intervention**: [specification]
- **Comparison**: [specification]
- **Outcomes**: Primary [list], Secondary [list]
- **Study designs**: [eligible designs]
- **Exclusions**: [explicit exclusion reasons]

### Evidence Synthesis Matrix
[Table with 12+ columns: Citation, Design, N, Population, Intervention, Comparison, Primary Outcome, Effect Size (95% CI), Quality Rating, Funding, Notable Limitations, Key Findings]

### Quality Assessment Summary
[Bar chart or text: % studies rated low/moderate/high quality by design; domains with most bias]

### Main Findings
[3-5 key synthesis findings with effect sizes, confidence intervals, heterogeneity metrics, subgroup patterns]

### Research Gaps Identified
- **Population gaps**: [underrepresented groups, settings]
- **Intervention gaps**: [untested variations, dosing, duration questions]
- **Outcome gaps**: [unmeasured constructs, follow-up duration]
- **Study design gaps**: [RCT vs. observational, active vs. passive control]
- **Geographic/cultural gaps**: [underrepresented regions]

### Research Agenda (2-3 Priority Questions)
[Next studies most needed to advance field]

### Certainty of Evidence (GRADE Summary)
[Table: Outcome | # Studies | Effect Size | Study Limitations | Inconsistency | Indirectness | Imprecision | Pub Bias | GRADE Rating]

## Quality Gates

1. **Protocol registered**: PROSPERO/equivalent before screening with protocol accessible
2. **Search reproducibility**: All search strings documented with dates and databases listed
3. **Dual review**: Minimum 80% of abstract/full-text screening done independently by 2+ reviewers with Cohen's kappa ≥0.60
4. **Complete extraction**: Data extraction template documented; verification on 10%+ of studies confirms >95% accuracy
5. **Quality assessment**: All included studies rated using validated tool; two reviewers independently assess ≥80% of studies
6. **Synthesis transparency**: Evidence matrix includes 12+ data columns; heterogeneity explicitly described
7. **Gap identification**: ≥5 distinct research gaps documented with evidence for what's missing
8. **PRISMA compliance**: Final report includes PRISMA checklist (scored >25/27 items) and flow diagram
9. **Certainty assessment**: All primary outcomes rated using GRADE methodology; rationale documented for downgrades
10. **Recency**: Search completed within 12 months of publication; search strategy updated yearly for living reviews

## Examples

### Good Literature Review
**Question**: "In adults with type 2 diabetes, does intensive lifestyle intervention compared to usual care reduce cardiovascular events?"

**Search**: PubMed, Scopus, EMBASE; 1995-2024; yielded 2,847 records → 127 full texts reviewed → 18 RCTs included (N=47,000+)

**Synthesis**: Intensive lifestyle reduces cardiovascular events (RR=0.93, 95% CI 0.88-0.98, I²=0.%), sustained at 10+ years. Effect stronger in those <55 years (RR=0.85 vs. 0.98 in older), with metabolic syndrome (RR=0.89 vs. 1.01 without). Modest heterogeneity by intervention component emphasis (weight loss vs. exercise).

**Gaps identified**: Limited long-term follow-up (>10 years) in women, minimal data on economic outcomes, underrepresentation of non-White populations, timing of intervention (early vs. late diabetes) not well-studied.

### Poor Literature Review
- Searches only PubMed with simple keywords ("diabetes intervention")
- Uses arbitrary publication date range (last 5 years) without justification
- Single reviewer screens abstracts
- Mixes study types (RCTs, case studies, expert opinion) without stratification
- No quality assessment
- Synthesizes through vote-counting (8 studies showed benefit, 4 didn't)
- Reports effect directions without effect sizes or confidence intervals
- Lists research needs generally without evidence for gaps
- No PRISMA checklist; missing search strategy details

## Common Mistakes

1. **Unstated population boundaries**: Including studies of "people with diabetes" without specifying type 1 vs. type 2, age, comorbidity. Results in incomparable populations; heterogeneity becomes unexplainable. Solution: Define population precisely in PICO; document how boundary decisions affect interpretation.

2. **Single-database searching**: Searching only PubMed or Google Scholar misses systematic evidence (journals not indexed, conference proceedings, grey literature). Solution: Minimum 3 databases across disciplines; add grey literature search (ProQuest Dissertations, clinical trial registries, conference proceedings).

3. **Ignoring publication bias**: Small underpowered studies often show larger effects; selective publication of positive results inflates pooled estimates. Solution: Create funnel plots (if ≥10 studies), conduct Egger's test, consider trim-and-fill methods. Discuss how missing studies might change conclusions.

4. **Inadequate quality assessment**: Screening for RCT design alone misses performance bias (unblinded participants), detection bias (unblinded outcome assessment), attrition bias (>20% dropout). Weak studies bias synthesis. Solution: Use validated tool (ROB-2 for RCTs); rate every bias domain; stratify synthesis by quality level.

5. **Conflating heterogeneity with inconsistency**: I² >50% indicates statistical heterogeneity but doesn't explain why. Heterogeneity from genuine effect modification (e.g., age-dependent response) differs from heterogeneity from methodological differences. Solution: Explore heterogeneity sources through subgroup analyses (pre-planned), sensitivity analyses (varying inclusion criteria), meta-regression (study-level predictors).

6. **Synthesis without transparency**: Stating "studies were mixed" without quantifying effect sizes, confidence intervals, or sample sizes prevents readers from evaluating strength. Solution: Report effect sizes (SMD, RR, OR) with 95% CI; explicit subgroup estimates; sample sizes underlying pooled estimates.

## Anti-Patterns

1. **Selecting inclusion criteria post-hoc**: Defining population, intervention, or outcome specifications after seeing studies introduces bias toward supporting preliminary hypotheses. Anti-pattern: "We decided to focus on women aged >60 after seeing the data." Solution: Pre-register protocol with PROSPERO before screening begins; document any protocol amendments with justification.

2. **Cherry-picking quality assessment criteria**: Excluding low-quality studies without pre-specified criteria or applying stricter standards to studies conflicting with conclusions. Anti-pattern: "We excluded observational studies because they were lower quality" while including uncontrolled case series. Solution: Pre-specify quality thresholds; apply consistently; never exclude based on results; stratify synthesis by quality instead.

3. **Assuming systematic review proves causation**: Even with meta-analysis of RCTs, confounding at study design level (selection of populations, measurement error) persists. Synthesized associations aren't causal until theory explains mechanism and alternative explanations excluded. Anti-pattern: Concluding "X causes Y" from pooled observational studies. Solution: Assess certainty using GRADE; distinguish association from causation; note unmeasured confounding.

4. **Updating reviews without protocol amendment tracking**: Adding new populations, outcomes, or study designs in updated reviews without documenting changes introduces selection bias. Anti-pattern: "We added outcomes not mentioned in the original protocol." Solution: Register protocol amendments in PROSPERO with dates and rationale; transparently report protocol changes in updated review.

5. **Ignoring outcome measurement heterogeneity**: Different instruments measuring same construct (depression via PHQ-9 vs. BDI vs. Clinical Interview) produce incomparable effect sizes. Pooling different measures without standardization inflates heterogeneity. Anti-pattern: "Study A used instrument X, Study B used instrument Y; we averaged effect sizes." Solution: Standardize all continuous outcomes to same metric (SMD); document instrument differences; explore measurement heterogeneity in subgroup analyses.

6. **Passive waiting for studies to be published**: Circulating pre-print versions, contacting authors for unpublished data, searching trial registries takes effort but minimizes publication bias. Anti-pattern: Only citing published articles. Solution: Search trial registries (ClinicalTrials.gov) for unpublished results; contact authors for outcomes not fully reported; include pre-prints with notation.
