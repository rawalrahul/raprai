---
name: ai-safety-checklist
description: "Comprehensive AI deployment safety: pre-deployment bias/hallucination testing, runtime monitoring with automated quality scoring, incident response, compliance documentation (GDPR/CCPA), and rollback procedures."
category: ai-automation
difficulty: advanced
model_boost: "Fixes unsafe AI deployments; prevents biased outputs, PII leaks, hallucinations, and compliance violations from reaching production"
---

# AI Safety Checklist

## Purpose
This skill teaches you to systematically identify and mitigate risks before deploying AI systems. You'll learn to test for bias across demographics, measure hallucination rates, detect and redact PII, establish runtime monitoring with automated quality scoring, design incident response procedures, and ensure compliance with data protection regulations. The output is a production-ready AI system with documented safety measures, clear rollback procedures, and governance that meets regulatory standards.

## When to Use
- Before any AI system reaches production
- Deploying to regulated industries (healthcare, finance, legal)
- Systems making consequential decisions (hiring, lending, content moderation)
- Handling sensitive personal data
- High-stakes applications requiring safety assurance
- **Do NOT use when**: Internal testing only, non-consequential outputs, or prototype-stage development

## Instructions

### Step 1: Pre-Deployment Bias Testing
Measure and document disparities across demographics before launch.

**Bias Testing Framework**:
```python
class BiasTestingFramework:
    """
    Systematically measure bias across demographics
    """

    async def test_demographic_parity(self, model, test_set: dict,
                                     demographic_field: str = "gender") -> dict:
        """
        Test: Do predictions favor one demographic group?

        Metric: Demographic Parity
        Fair if: P(positive_decision|D=A) ≈ P(positive_decision|D=B)
        """

        results = {}

        # Stratify test set by demographic
        demographic_groups = self.stratify(test_set, demographic_field)

        for demo, samples in demographic_groups.items():
            positive_count = 0

            for sample in samples:
                prediction = await model.predict(sample)
                if prediction["decision"] == "positive":
                    positive_count += 1

            positive_rate = positive_count / len(samples)
            results[demo] = positive_rate

        # Check disparity
        max_rate = max(results.values())
        min_rate = min(results.values())
        disparity = max_rate - min_rate

        # Fairness threshold: < 5% disparity acceptable
        is_fair = disparity < 0.05

        return {
            "metric": "demographic_parity",
            "per_demographic": results,
            "max_disparity": disparity,
            "is_fair": is_fair,
            "recommendation": (
                "Safe to deploy" if is_fair
                else "Investigate disparities; consider rebalancing data"
            )
        }

    async def test_equal_opportunity(self, model, test_set: dict,
                                    demographic_field: str = "race") -> dict:
        """
        Test: Do people from disadvantaged groups get equal chances?

        Metric: Equal Opportunity
        Fair if: TPR(D=A) ≈ TPR(D=B) [True Positive Rate equal]
        """

        from sklearn.metrics import confusion_matrix

        results = {}
        demographic_groups = self.stratify(test_set, demographic_field)

        for demo, samples in demographic_groups.items():
            true_positives = 0
            false_negatives = 0

            for sample in samples:
                prediction = await model.predict(sample)
                is_positive = sample["label"] == "positive"
                predicted_positive = prediction["decision"] == "positive"

                if is_positive and predicted_positive:
                    true_positives += 1
                elif is_positive and not predicted_positive:
                    false_negatives += 1

            # True Positive Rate = TP / (TP + FN)
            total_positives = true_positives + false_negatives
            tpr = true_positives / total_positives if total_positives > 0 else 0

            results[demo] = {
                "true_positive_rate": tpr,
                "sample_size": len(samples)
            }

        # Check TPR parity
        tprs = [v["true_positive_rate"] for v in results.values()]
        max_tpr = max(tprs)
        min_tpr = min(tprs)
        tpr_disparity = max_tpr - min_tpr

        is_fair = tpr_disparity < 0.10  # < 10% disparity acceptable

        return {
            "metric": "equal_opportunity",
            "per_demographic": results,
            "tpr_disparity": tpr_disparity,
            "is_fair": is_fair,
            "recommendation": (
                "Safe to deploy" if is_fair
                else "Adjust thresholds or retrain to equalize TPR"
            )
        }

    async def test_disparate_impact(self, model, test_set: dict,
                                   protected_attribute: str = "race") -> dict:
        """
        Legal test: 80% rule (protected class success rate >= 80% of baseline)

        Example: If 50% of majority group approved, 40% of minority approved
        Disparate impact if: 40 / 50 = 80% (marginal)
        """

        groups = self.stratify(test_set, protected_attribute)
        success_rates = {}

        for group, samples in groups.items():
            successes = sum(1 for s in samples if await self.is_success(model, s))
            success_rates[group] = successes / len(samples)

        # Baseline = highest success rate
        baseline = max(success_rates.values())

        # Check 80% rule
        disparate_impact_violations = {}
        for group, rate in success_rates.items():
            ratio = rate / baseline if baseline > 0 else 0
            if ratio < 0.80:
                disparate_impact_violations[group] = ratio

        is_safe = len(disparate_impact_violations) == 0

        return {
            "metric": "disparate_impact_80_rule",
            "baseline_success_rate": baseline,
            "per_group_rates": success_rates,
            "violations": disparate_impact_violations,
            "is_safe": is_safe,
            "recommendation": (
                "Legally compliant" if is_safe
                else f"80% rule violated for groups: {list(disparate_impact_violations.keys())}"
            )
        }
```

**Bias Testing Checklist**:
```yaml
before_deployment_test:
  - "Gender bias: Test across male/female/non-binary"
  - "Race bias: Test across racial groups in dataset"
  - "Age bias: Test across age ranges"
  - "Disability bias: Test with disability-related attributes"
  - "Geographic bias: Test across regions (if applicable)"
  - "Socioeconomic bias: Test across income levels"

test_results_required:
  - "Demographic parity disparity < 5%"
  - "Equal opportunity TPR disparity < 10%"
  - "80% rule not violated (disparate impact)"
  - "No group has > 10% error rate difference"
  - "Minority groups not systematically disadvantaged"

if_bias_detected:
  action_1: "Rebalance training data (oversample minority if needed)"
  action_2: "Adjust decision threshold per group (if allowed legally)"
  action_3: "Retrain model on debiased dataset"
  action_4: "Re-test all bias metrics"
  action_5: "Document fairness limitations in system card"
```

### Step 2: Hallucination and Factuality Testing
Measure how often AI outputs false information.

**Hallucination Measurement**:
```python
class HallucinationTesting:
    """
    Measure how often model generates false information
    """

    async def measure_factuality(self, model, fact_test_set: list[dict]) -> dict:
        """
        Test: Does model stick to facts or make things up?

        fact_test_set: [{query, expected_answer, context}, ...]
        """

        results = {
            "correct": 0,
            "hallucinated": 0,
            "partially_correct": 0,
            "refused": 0
        }

        hallucinations = []

        for test in fact_test_set:
            response = await model.answer(test["query"], context=test.get("context"))

            # Check if response is factually correct
            is_correct = await self.check_factuality(
                response,
                test["expected_answer"],
                test["context"]
            )

            if is_correct == "correct":
                results["correct"] += 1
            elif is_correct == "hallucinated":
                results["hallucinated"] += 1
                hallucinations.append({
                    "query": test["query"],
                    "model_response": response,
                    "correct_answer": test["expected_answer"]
                })
            elif is_correct == "partial":
                results["partially_correct"] += 1
            elif is_correct == "refused":
                results["refused"] += 1

        total = len(fact_test_set)
        hallucination_rate = results["hallucinated"] / total

        return {
            "correct_rate": results["correct"] / total,
            "hallucination_rate": hallucination_rate,
            "partial_rate": results["partially_correct"] / total,
            "refusal_rate": results["refused"] / total,
            "is_safe": hallucination_rate < 0.05,  # < 5% acceptable
            "examples": hallucinations[:5],  # Show worst cases
            "recommendation": (
                "Safe to deploy" if hallucination_rate < 0.05
                else f"Hallucination rate too high ({hallucination_rate:.1%}); "
                     "consider RAG, fine-tuning, or stronger guardrails"
            )
        }

    async def measure_with_entailment_model(self, model, test_set: list[dict]) -> dict:
        """
        Use NLI model to check if response is entailed by context
        """
        from transformers import pipeline

        nli = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli")

        hallucination_count = 0

        for test in test_set:
            response = await model.answer(test["query"])
            context = test.get("context", "")

            # Check if context entails response
            result = nli(context, response,
                        hypothesis_template="This text supports: {}")

            if result["scores"][0] < 0.5:  # Low entailment = hallucination
                hallucination_count += 1

        hallucination_rate = hallucination_count / len(test_set)

        return {
            "hallucination_rate": hallucination_rate,
            "is_safe": hallucination_rate < 0.10
        }
```

**Test Dataset Requirements**:
```yaml
factuality_test_set:
  size: "50-100 queries with known correct answers"
  examples:
    - query: "Who is the current president of France?"
      context: "None (general knowledge)"
      expected_answer: "Emmanuel Macron"

    - query: "What is the revenue of Acme Corp in 2023?"
      context: "Acme Corp annual report 2023 (PDF text)"
      expected_answer: "$5.2 billion"

  coverage:
    - "General knowledge questions"
    - "Domain-specific facts (customer use case)"
    - "Temporal facts (dates, timelines)"
    - "Numerical facts (statistics, amounts)"
    - "Rare/lesser-known facts (high hallucination risk)"
```

### Step 3: PII Detection and Redaction
Identify and remove sensitive personal information before output.

**PII Detection**:
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class PIIDetectionAndRedaction:
    """
    Detect and redact PII (personally identifiable information)
    """

    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

    async def detect_pii(self, text: str) -> list[dict]:
        """
        Scan text for PII
        Returns list of detected PII entities
        """

        results = self.analyzer.analyze(
            text,
            language="en",
            entities=["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                     "CREDIT_CARD", "BANK_ACCOUNT", "SSN", "US_PASSPORT"]
        )

        pii_found = []
        for result in results:
            pii_found.append({
                "type": result.entity_type,
                "text": text[result.start:result.end],  # The PII value
                "position": (result.start, result.end),
                "confidence": result.score
            })

        return pii_found

    async def redact_pii(self, text: str, redaction_method: str = "MASK") -> str:
        """
        Remove PII from text

        redaction_method:
        - "MASK": Replace with asterisks (***-***-**-1234)
        - "REMOVE": Delete entirely
        - "HASH": Replace with hash digest
        """

        results = self.analyzer.analyze(text, language="en")

        if redaction_method == "MASK":
            anonymized = self.anonymizer.anonymize(
                text,
                analyzer_results=results,
                operators={
                    "DEFAULT": {"type": "mask", "masking_char": "*"}
                }
            )
        elif redaction_method == "REMOVE":
            anonymized = self.anonymizer.anonymize(
                text,
                analyzer_results=results,
                operators={
                    "DEFAULT": {"type": "remove"}
                }
            )

        return anonymized.text

    async def audit_pii_leakage(self, model, test_set: list[str]) -> dict:
        """
        Check if model outputs contain PII
        """

        pii_leaks = []

        for input_text in test_set:
            output = await model.generate(input_text)

            pii_in_output = await self.detect_pii(output)

            if pii_in_output:
                pii_leaks.append({
                    "input": input_text,
                    "output": output,
                    "pii_detected": pii_in_output
                })

        leakage_rate = len(pii_leaks) / len(test_set)

        return {
            "pii_leakage_count": len(pii_leaks),
            "leakage_rate": leakage_rate,
            "is_safe": leakage_rate == 0,  # Zero tolerance for PII leaks
            "examples": pii_leaks[:3],
            "recommendation": (
                "Safe to deploy" if leakage_rate == 0
                else "Add PII detection guardrail before output"
            )
        }
```

**PII Safeguards**:
```yaml
architectural_safeguards:
  - "Remove PII from training data before fine-tuning"
  - "Add runtime PII detection filter (output layer)"
  - "Mask PII in logging/monitoring"
  - "Encrypt data at rest and in transit"
  - "Limit who can access logs containing PII"

compliance_checklist:
  - "GDPR: Right to be forgotten (delete user data on request)"
  - "GDPR: Data processing agreements with vendors"
  - "GDPR: Privacy impact assessment completed"
  - "CCPA: Ability to opt out of data sale"
  - "CCPA: Consumer access to collected data"
  - "HIPAA: De-identification of health data (if applicable)"
```

### Step 4: Runtime Monitoring and Automated Quality Scoring
Continuously measure model performance in production.

**Quality Scoring System**:
```python
class AutomatedQualityScoring:
    """
    Score each AI output for quality and flag concerning cases
    """

    async def score_output(self, input_text: str, model_output: str,
                          reference: str = None) -> dict:
        """
        Generate quality score for single output
        """

        scores = {}

        # 1. Length-based sanity check
        output_length = len(model_output.split())
        scores["length_sanity"] = 1.0 if 10 < output_length < 1000 else 0.3

        # 2. Coherence (using sentence transformer)
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        input_emb = model.encode(input_text)
        output_emb = model.encode(model_output)

        similarity = np.dot(input_emb, output_emb) / (
            np.linalg.norm(input_emb) * np.linalg.norm(output_emb)
        )
        scores["relevance_to_input"] = similarity  # 0-1

        # 3. Toxicity check
        from transformers import pipeline
        toxicity_classifier = pipeline("text-classification",
                                      model="michellejieli/NSFW_text_classifier")
        toxicity_result = toxicity_classifier(model_output)
        scores["toxicity"] = 1.0 - toxicity_result[0]["score"]  # Invert

        # 4. PII detection
        pii_count = len(await self.detect_pii(model_output))
        scores["pii_free"] = 1.0 if pii_count == 0 else 0.0

        # 5. Factuality (if reference provided)
        if reference:
            from evaluate import load
            bertscore = load("bertscore")
            score = bertscore.compute(predictions=[model_output],
                                     references=[reference], lang="en")
            scores["factuality"] = score["f1"][0]

        # Overall score (weighted average)
        weights = {
            "length_sanity": 0.1,
            "relevance_to_input": 0.25,
            "toxicity": 0.25,
            "pii_free": 0.25,
            "factuality": 0.15
        }

        overall = sum(scores.get(k, 0) * v for k, v in weights.items())

        return {
            "overall_score": overall,  # 0-1
            "dimension_scores": scores,
            "flag_for_review": overall < 0.6,  # Flag low quality
            "quality_level": (
                "high" if overall > 0.8
                else "medium" if overall > 0.6
                else "low"
            )
        }

    async def batch_score_outputs(self, outputs: list[tuple[str, str]]) -> dict:
        """
        Score batch of outputs, aggregate statistics
        """

        scores = []
        for input_text, model_output in outputs:
            score = await self.score_output(input_text, model_output)
            scores.append(score)

        overall_scores = [s["overall_score"] for s in scores]
        flagged_count = sum(1 for s in scores if s["flag_for_review"])

        return {
            "mean_score": np.mean(overall_scores),
            "median_score": np.median(overall_scores),
            "std_dev": np.std(overall_scores),
            "min_score": np.min(overall_scores),
            "max_score": np.max(overall_scores),
            "flagged_for_review": flagged_count,
            "flagged_percentage": flagged_count / len(outputs),
            "health_status": (
                "healthy" if np.mean(overall_scores) > 0.8
                else "needs_attention" if np.mean(overall_scores) > 0.6
                else "critical"
            )
        }
```

**Alerting Rules**:
```yaml
monitoring_alerts:
  quality_degradation:
    trigger: "Average quality score drops below 0.7"
    action: "Page oncall engineer; check for data distribution shift"

  hallucination_spike:
    trigger: "Hallucination rate increases by > 2%"
    action: "Pause model; investigate training data issue"

  pii_leakage:
    trigger: "Any PII detected in production output"
    action: "Immediate page; emergency mitigation required"

  bias_detected:
    trigger: "Demographic disparity > 10% for protected attribute"
    action: "Review recent changes; potentially disable model"

  error_rate:
    trigger: "Error rate > 5% (API failures, crashes)"
    action: "Check API health; consider fallback system"
```

### Step 5: Incident Response and Rollback
Prepare for when something goes wrong.

**Incident Response Plan**:
```yaml
incident_severity_levels:
  severity_1_critical:
    definition: "PII leakage, major bias, complete model failure"
    sla_response: "5 minutes"
    action: "Immediate rollback to previous version"

  severity_2_high:
    definition: "Quality degradation > 10%, rate limit violations"
    sla_response: "30 minutes"
    action: "Investigate root cause; potentially rollback"

  severity_3_medium:
    definition: "Quality degradation 5-10%, occasional errors"
    sla_response: "4 hours"
    action: "Investigate; deploy patch or monitor"

  severity_4_low:
    definition: "Minor quality issues, no user impact"
    sla_response: "Next business day"
    action: "Log issue; plan for next release"

incident_response_checklist:
  on_incident_detection:
    - "Immediately notify #incidents channel"
    - "Begin runbook for this incident type"
    - "Assess severity (1-4)"
    - "If Severity 1: Trigger rollback (see below)"
    - "Document timeline of events"
    - "Notify affected customers (if applicable)"

  during_incident:
    - "Keep customer communication updated (30-min intervals)"
    - "Root cause analysis (start immediately, parallel to fix)"
    - "Implement fix or workaround"
    - "Validate fix doesn't introduce new issues"
    - "Gradual rollout (if not critical emergency)"

  post_incident:
    - "Conduct post-mortem within 24 hours"
    - "Document root cause and prevention measures"
    - "Create tickets for improvements"
    - "Update runbooks with lessons learned"
    - "Share findings in team meeting"
```

**Rollback Procedure**:
```python
class RollbackProcedure:
    """
    Quickly revert to previous known-good model
    """

    async def execute_rollback(self, reason: str, severity: int):
        """
        Rollback current model to previous stable version
        """

        print(f"EMERGENCY ROLLBACK: {reason} (Severity {severity})")

        # Step 1: Identify previous stable version
        previous_version = await self.get_previous_stable_model()
        print(f"Rolling back to version: {previous_version.version_id}")

        # Step 2: Validation check on backup
        validation = await self.validate_model(previous_version)
        if not validation["is_healthy"]:
            print("⚠️  Previous version also compromised!")
            return {"status": "rollback_failed", "escalation_required": True}

        # Step 3: Switch traffic to previous model
        await self.switch_traffic(previous_version.model_endpoint)
        print(f"✓ Traffic switched to {previous_version.version_id}")

        # Step 4: Monitor metrics
        for i in range(10):  # Monitor for 5 minutes (30s checks)
            metrics = await self.get_current_metrics()
            print(f"Check {i+1}: Quality={metrics['quality_score']:.2f}, "
                  f"Errors={metrics['error_rate']:.1%}")

            if metrics["quality_score"] < 0.7:
                print("⚠️  Rollback not helping; quality still degraded")
                await self.escalate_to_human()
                break

        print("✓ Rollback complete; system stable")

        # Step 5: Notify stakeholders
        await self.notify_incident_channel(
            f"Rollback to {previous_version.version_id} complete. "
            f"Reason: {reason}"
        )

        return {"status": "success", "version": previous_version.version_id}

    async def get_previous_stable_model(self) -> dict:
        """Retrieve last known-good model"""
        versions = await self.list_model_versions()  # Ordered by date
        # Find most recent version that was stable for > 1 week
        for version in versions:
            if version["days_deployed"] > 7 and version["health_status"] == "healthy":
                return version
        return versions[0]  # Fallback: use oldest available
```

### Step 6: Compliance and Governance
Document safety measures for legal/regulatory requirements.

**Model Card Documentation**:
```yaml
model_card:
  model_name: "Customer Support AI"
  version: "2.1.0"
  release_date: "2024-01-15"

  intended_use:
    primary: "Classify customer support emails by sentiment"
    out_of_scope:
      - "Hiring decisions"
      - "Medical diagnosis"
      - "Financial advice"

  performance_summary:
    accuracy: "92%"
    f1_score: "0.91"
    test_set_size: "1000 emails"

  fairness_assessment:
    demographic_parity_disparity: "3.2%"
    equal_opportunity_tpr_disparity: "4.1%"
    protected_attributes: ["gender", "race", "age"]
    fairness_status: "SAFE"

  limitations:
    - "Lower accuracy on sarcastic emails (85% vs 92% overall)"
    - "Minimal non-English email examples; not recommended for other languages"
    - "Performance may degrade on very long emails (> 5000 chars)"

  dataset_information:
    source: "Internal customer support emails, 2021-2023"
    size: "50,000 labeled emails"
    demographics:
      - "50/50 gender split"
      - "Racially diverse (representative of customer base)"
      - "Age range: 18-80"

  privacy_considerations:
    - "Training data anonymized; no PII retained"
    - "Model does not memorize training examples"
    - "Output includes PII redaction filter"

  ethical_considerations:
    - "Model may have residual gender bias; monitor in production"
    - "Not designed for adversarial robustness"
    - "Regular audits recommended"

  contact: "ai-safety-team@company.com"
```

**GDPR Compliance Checklist**:
```yaml
gdpr_compliance:
  lawful_basis:
    - "Specify why processing personal data (Recital 42)"
    - "Document consent or legitimate interest"
    - "Example: 'Process customer emails to improve support quality'"

  data_minimization:
    - "Only collect data needed for stated purpose"
    - "Remove PII from training data"
    - "Don't build shadow profiles"

  transparency:
    - "Privacy notice: Tell users data is processed by AI"
    - "No hidden tracking or profiling"

  data_subject_rights:
    - "Right to access: Users can request their data"
    - "Right to be forgotten: Delete user data on request"
    - "Right to object: Users can opt-out of processing"
    - "Data portability: Export user data in standard format"

  data_protection_impact_assessment:
    - "Completed before deployment"
    - "Documented in DPIA_2024_CustomerSupportAI.pdf"

  documentation:
    - "Processing agreement with all vendors (Google, OpenAI, etc.)"
    - "Data retention policy (delete after 12 months)"
    - "Data breach response plan (notify regulators within 72 hours)"

  accountability:
    - "Data Protection Officer assigned (if applicable)"
    - "Regular privacy audits (quarterly)"
    - "Training for staff handling personal data"
```

**CCPA Compliance Checklist**:
```yaml
ccpa_compliance:
  consumer_rights:
    - "Right to know: Disclose data collected and how used"
    - "Right to delete: Delete personal information on request"
    - "Right to opt-out: Don't sell consumer data"
    - "Right to non-discrimination: Same service if consumer opts out"

  privacy_policy:
    - "Clear disclosure of data collection practices"
    - "Explain use of personal information"
    - "Categories of information disclosed/sold"
    - "Right to delete / opt-out instructions"

  opt_out_mechanism:
    - "Simple method to opt-out (one-click)"
    - "Responsive to opt-out requests (within 45 days)"
    - "Don't penalize opting out"

  verification:
    - "Verify consumer identity before fulfilling request"
    - "Keep audit log of requests"
```

### Step 7: Continuous Monitoring and Improvement
Measure long-term model health and iterate.

**Monitoring Dashboard**:
```yaml
production_dashboard:
  metrics:
    - name: "Quality Score (Hourly)"
      value: "0.82"
      trend: "↓ -2% since yesterday"
      alert_threshold: "< 0.70"

    - name: "Hallucination Rate"
      value: "3.2%"
      trend: "stable"
      alert_threshold: "> 5%"

    - name: "PII Leakage Events"
      value: "0"
      trend: "OK"
      alert_threshold: "> 0"

    - name: "Demographic Disparity"
      value: "4.1%"
      trend: "stable"
      alert_threshold: "> 5%"

    - name: "Model Latency (P99)"
      value: "1.2s"
      trend: "stable"
      alert_threshold: "> 5s"

    - name: "API Error Rate"
      value: "0.1%"
      trend: "↓ improving"
      alert_threshold: "> 1%"

  recent_incidents:
    - date: "2024-01-14 03:15"
      severity: "2 - High"
      description: "Quality score dropped to 0.65 for 30 minutes"
      root_cause: "API latency spike, switched fallback"
      resolution_time: "15 minutes"
```

## Output Template

**AI Safety Report**:
```markdown
# Safety Audit Report: [Model Name] v[Version]

## Executive Summary
[Pass/Fail on critical safety gates]

## Bias Testing Results
[Demographic parity, equal opportunity, disparate impact]

## Hallucination Testing
[Factuality rate, examples of hallucinations]

## PII Detection
[PII leakage rate, redaction effectiveness]

## Compliance Status
[GDPR, CCPA, industry-specific requirements]

## Monitoring Setup
[Metrics tracked, alerts configured]

## Incident Response
[Procedures, rollback criteria]

## Recommendations
[Required fixes before deployment, nice-to-haves]

## Sign-Off
[Safety review approval, date, reviewer]
```

## Quality Gates

1. **Bias < Threshold**: Demographic disparity < 5%, no 80% rule violations
2. **Hallucination < 5%**: Factuality rate >= 95%
3. **Zero PII Leakage**: No personal information in outputs
4. **Compliance Complete**: GDPR/CCPA requirements met
5. **Monitoring Deployed**: All metrics tracked, alerts active
6. **Incident Response Ready**: Runbooks documented, rollback tested
7. **Safety Review Passed**: Signed off by compliance/safety team

## Examples

### Good Safety Profile: Financial Advice Chatbot
```
Bias Testing: ✓
- Gender parity: 2.1% disparity (target < 5%)
- Race parity: 3.8% disparity (target < 5%)
- Age parity: 4.2% disparity (target < 5%)

Hallucination: ✓
- Factuality rate: 98% (target >= 95%)
- 2 hallucinations out of 100 test queries

PII Detection: ✓
- PII leakage: 0% (zero tolerance)
- PII redaction: 100% coverage

Compliance: ✓
- GDPR: Data processing agreement signed
- CCPA: Opt-out mechanism deployed
- SOX: Audit trail logged

Monitoring: ✓
- Quality score: 0.85 (target >= 0.80)
- Latency P99: 1.2s (target < 5s)
- Error rate: 0.1% (target < 1%)

Status: SAFE FOR PRODUCTION
```

## Common Mistakes

1. **No Pre-Deployment Testing**
   - ❌ Deploy model directly after training
   - ✓ Run full bias, hallucination, PII tests before launch

2. **Testing Only Happy Path**
   - ❌ Test on clean data only; ignore edge cases
   - ✓ Test adversarial inputs, misspellings, PII-laden texts

3. **No Continuous Monitoring**
   - ❌ Deploy and forget; only check when user complains
   - ✓ Dashboard with real-time metrics and alerts

4. **No Rollback Plan**
   - ❌ "We'll fix it" if something goes wrong
   - ✓ Pre-tested rollback procedure, documented and rehearsed

5. **Ignoring Compliance**
   - ❌ "We handle data responsibly" without documentation
   - ✓ GDPR/CCPA compliance checked, legal reviewed

## Anti-Patterns

1. **Trust Single Fairness Metric**
   - ❌ "Accuracy is 90%, so model is fair"
   - ✓ Test demographic parity, equal opportunity, disparate impact

2. **No Ground Truth for Hallucinations**
   - ❌ "Looks reasonable to me"
   - ✓ Measure against factual test set with known answers

3. **Reactive Safety (After Incident)**
   - ❌ Add safety measures only after problem discovered
   - ✓ Proactive pre-deployment testing

4. **Rollback Too Slow**
   - ❌ Rollback takes 2 hours (users suffer)
   - ✓ Automated one-click rollback, < 5 min recovery
