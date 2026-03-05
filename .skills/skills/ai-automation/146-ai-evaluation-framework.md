---
name: ai-evaluation-framework
description: "Build AI evaluation frameworks with rubrics, automated metrics (BLEU/ROUGE/BERTScore), human evaluation protocols, A/B testing, regression testing, bias detection, and evaluation dataset versioning."
category: ai-automation
difficulty: advanced
model_boost: "Fixes AI systems deployed without proper evaluation; prevents quality regressions and bias issues from going undetected"
---

# AI Evaluation Framework

## Purpose
This skill teaches you to systematically evaluate AI outputs across multiple dimensions: relevance, correctness, safety, bias, and consistency. You'll design evaluation rubrics, implement automated metrics (BLEU, ROUGE, BERTScore, custom), conduct human evaluations with calibration, run A/B tests between models, detect regressions, measure and mitigate bias, and version your evaluation datasets. The output is a production-grade evaluation system that catches quality issues before they reach users.

## When to Use
- Before deploying any AI model to production
- Comparing two models or approaches
- Monitoring model quality over time (regression testing)
- Ensuring AI outputs meet accuracy/safety thresholds
- Detecting bias across demographics
- Creating golden test sets for model development
- **Do NOT use when**: Single demo scripts, internal prototyping without plans to scale

## Instructions

### Step 1: Design Evaluation Rubrics
Create human-readable scoring frameworks for qualitative assessment.

**Rubric Structure**:
```yaml
rubric:
  task: "Summarizing research papers"
  dimensions:
    - name: Relevance
      description: "Does the summary capture the main findings?"
      levels:
        1_not_relevant:
          description: "Summary doesn't address the paper's main topic"
          example: "Paper is about neural networks, summary discusses climate change"
        2_partially_relevant:
          description: "Summary mentions some key topics but misses major findings"
          example: "Summary mentions architecture but omits accuracy improvements"
        3_relevant:
          description: "Summary covers main findings with minor omissions"
          example: "Summary captures architecture and results, one secondary finding missed"
        4_highly_relevant:
          description: "Summary accurately covers all major findings"
          example: "Summary includes architecture, datasets, results, and implications"

    - name: Accuracy
      description: "Are factual claims in the summary accurate to the paper?"
      levels:
        1_multiple_errors:
          description: "Multiple factual errors or misrepresentations"
          example: "Claims 95% accuracy when paper shows 85%"
        2_some_errors:
          description: "1-2 minor inaccuracies"
          example: "Misquotes one statistic but other facts correct"
        3_mostly_accurate:
          description: "No significant errors; minor imprecision acceptable"
          example: "Facts correct; minor rounding acceptable"
        4_highly_accurate:
          description: "All factual claims match paper exactly"
          example: "Figures, dates, findings all match source"

    - name: Clarity
      description: "Is the summary easy to understand?"
      levels:
        1_confusing:
          description: "Hard to follow; unclear relationships between ideas"
        2_somewhat_unclear:
          description: "Readable but requires effort; some sentences confusing"
        3_clear:
          description: "Generally clear; understandable to subject experts"
        4_very_clear:
          description: "Accessible to non-experts; excellent prose"

  scoring:
    method: "Average of all dimension scores"
    threshold: "3.0 (all dimensions >= 3)"
    examples:
      good:
        score: 3.7
        rationale: "Relevant (4), Accurate (3), Clear (4) = (4+3+4)/3 = 3.67"
      poor:
        score: 2.0
        rationale: "Relevant (2), Accurate (2), Clear (2) = 2.0 (below threshold)"
```

**Calibration Process** (ensure consistent scoring):
```python
class RubricCalibration:
    """
    Train annotators to score consistently
    Measure inter-rater reliability (Cohen's Kappa)
    """

    async def run_calibration_session(self, annotators: list[str],
                                     calibration_samples: int = 10):
        """
        1. All annotators score same 10 examples
        2. Discuss disagreements, refine rubric
        3. Re-score, measure agreement
        4. Repeat until Kappa >= 0.75
        """

        round_num = 1
        kappa = 0

        while kappa < 0.75 and round_num <= 3:
            print(f"Calibration Round {round_num}")

            # All annotators score same samples
            scores = {}
            for annotator in annotators:
                scores[annotator] = await annotator.score_batch(
                    calibration_samples
                )

            # Calculate inter-rater agreement
            kappa = calculate_cohens_kappa(scores)
            print(f"Cohen's Kappa: {kappa:.3f}")

            if kappa < 0.75:
                # Discuss disagreements
                disagreements = find_disagreements(scores, threshold=1)
                print(f"Disagreements on {len(disagreements)} samples")

                # Refine rubric and try again
                round_num += 1

        return kappa >= 0.75

    @staticmethod
    def calculate_cohens_kappa(scores: dict) -> float:
        """
        Measure agreement between raters
        Kappa > 0.75 = substantial agreement
        Kappa 0.6-0.75 = moderate agreement
        """
        # Implementation: sklearn.metrics.cohen_kappa_score
        pass
```

### Step 2: Implement Automated Evaluation Metrics
Use metrics for fast, objective assessment.

**Text Generation Metrics**:
```python
from evaluate import load

class AutomatedMetrics:
    """Standard metrics for text generation tasks"""

    def __init__(self):
        self.bleu = load("bleu")
        self.rouge = load("rouge")
        self.bertscore = load("bertscore")
        self.meteor = load("meteor")

    async def evaluate_summary(self, prediction: str,
                              references: list[str]) -> dict:
        """
        Evaluate summarization with multiple metrics

        prediction: Generated summary
        references: 1+ gold-standard summaries (multiple valid summaries possible)
        """

        # BLEU: n-gram overlap (strict, for machine translation)
        # Range: 0-1 (1 = perfect match)
        bleu_score = self.bleu.compute(
            predictions=[prediction],
            references=[[ref for ref in references]]
        )
        # Returns: {"bleu": 0.45, "precisions": [...], "brevity_penalty": 0.98}

        # ROUGE: Recall-oriented Understudy for Gisting Evaluation
        # ROUGE-1: unigram overlap, ROUGE-L: longest common subsequence
        rouge_score = self.rouge.compute(
            predictions=[prediction],
            references=references
        )
        # Returns: {"rouge1": 0.52, "rouge2": 0.30, "rougeL": 0.49}

        # BERTScore: Contextual embeddings (better for semantics)
        # Range: 0-1 (1 = semantically perfect)
        bert_score = self.bertscore.compute(
            predictions=[prediction],
            references=references,
            lang="en"
        )
        # Returns: {"precision": [...], "recall": [...], "f1": [0.78]}

        # METEOR: Machine Evaluation for Translation with Explicit Ordering
        meteor_score = self.meteor.compute(
            predictions=[prediction],
            references=[[ref] for ref in references]
        )

        return {
            "bleu": bleu_score["bleu"],
            "rouge1": rouge_score["rouge1"],
            "rouge2": rouge_score["rouge2"],
            "rougeL": rouge_score["rougeL"],
            "bertscore_f1": bert_score["f1"][0],
            "meteor": meteor_score["meteor"]
        }
```

**Task-Specific Metrics**:
```python
class TaskSpecificMetrics:
    """Metrics tuned for specific tasks"""

    @staticmethod
    def evaluate_classification(predictions: list[str],
                               references: list[str]) -> dict:
        """Evaluate classification accuracy"""
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support

        accuracy = accuracy_score(references, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            references, predictions, average='weighted'
        )

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    @staticmethod
    def evaluate_qa(predictions: list[str],
                   references: list[str]) -> dict:
        """Evaluate question-answering with exact match and F1"""
        from evaluate import load

        squad_metric = load("squad")
        results = squad_metric.compute(
            predictions=predictions,
            references=references
        )
        # Returns: {"exact": 0.75, "f1": 0.82}
        return results

    @staticmethod
    def evaluate_retrieval(retrieval_results: list[list[str]],
                          relevant_docs: list[list[str]]) -> dict:
        """Evaluate retrieval with precision, recall, MRR, NDCG"""
        from sklearn.metrics import ndcg_score

        metrics = {}

        # Precision@K
        metrics["precision_at_5"] = np.mean([
            len(set(results[:5]) & set(relevant)) / min(5, len(results))
            for results, relevant in zip(retrieval_results, relevant_docs)
        ])

        # Mean Reciprocal Rank (MRR)
        mrr_scores = []
        for results, relevant in zip(retrieval_results, relevant_docs):
            for rank, doc in enumerate(results, 1):
                if doc in relevant:
                    mrr_scores.append(1.0 / rank)
                    break
            else:
                mrr_scores.append(0)
        metrics["mrr"] = np.mean(mrr_scores)

        return metrics
```

**Custom Metrics**:
```python
class CustomMetrics:
    """Define domain-specific metrics"""

    @staticmethod
    def toxicity_score(text: str) -> float:
        """
        Score how toxic/harmful the text is
        Uses Perspective API or similar
        Range: 0-1 (0 = not toxic, 1 = highly toxic)
        """
        from perspective import PerspectiveAPI
        client = PerspectiveAPI()
        result = client.analyze(text)
        return result["TOXICITY"]["score"]

    @staticmethod
    def readability_score(text: str) -> float:
        """
        Score text readability (Flesch-Kincaid grade level)
        Returns grade level (8 = 8th-grade level)
        """
        from textstat import flesch_kincaid_grade
        return flesch_kincaid_grade(text)

    @staticmethod
    def factuality_score(claim: str, context: str) -> float:
        """
        Score how well-supported claim is by context
        Uses entailment models
        """
        from transformers import pipeline
        nli = pipeline("zero-shot-classification",
                      model="facebook/bart-large-mnli")
        result = nli(context, claim, hypothesis_template="This text supports: {}")
        # Returns confidence that context supports claim
        return result["scores"][0]

    @staticmethod
    def semantic_consistency(texts: list[str]) -> float:
        """
        Score semantic coherence across multiple texts
        Measures if texts discuss same topic
        """
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts)

        # Calculate cosine similarity between consecutive texts
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i+1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1])
            )
            similarities.append(sim)

        return np.mean(similarities)
```

### Step 3: Human Evaluation Protocols
Design and execute systematic human evaluation.

**Human Evaluation Structure**:
```python
class HumanEvaluation:
    """
    Orchestrate human evaluation of AI outputs
    """

    async def run_evaluation(self, samples: list[dict],
                            annotators: list[str],
                            num_per_annotator: int = 50,
                            overlap: int = 10):
        """
        Distribute evaluation tasks to multiple annotators

        samples: List of (input, prediction) pairs to evaluate
        annotators: List of annotator IDs
        num_per_annotator: How many samples each annotator evaluates
        overlap: How many samples annotators both evaluate (for agreement)
        """

        # Distribute samples: ensure some overlap for measuring agreement
        assignments = self.distribute_samples(
            samples,
            annotators,
            num_per_annotator,
            overlap
        )

        results = {}

        for annotator, assigned_samples in assignments.items():
            print(f"Assigning {len(assigned_samples)} samples to {annotator}")

            results[annotator] = await self.collect_annotations(
                annotator,
                assigned_samples
            )

        # Calculate inter-rater agreement on overlapping samples
        agreement = self.calculate_agreement(results)
        print(f"Inter-rater Kappa: {agreement:.3f}")

        # Aggregate results
        aggregated = self.aggregate_annotations(results, overlap_only=False)

        return aggregated

    def distribute_samples(self, samples: list, annotators: list,
                          num_per_annotator: int, overlap: int) -> dict:
        """
        Distribute samples such that:
        - Each annotator gets num_per_annotator samples
        - overlap samples are evaluated by multiple annotators
        """
        assignments = {annotator: [] for annotator in annotators}

        # Unique samples per annotator
        unique_per_annotator = num_per_annotator - (overlap // len(annotators))

        # Distribute unique samples
        for i, sample in enumerate(samples):
            annotator = annotators[i % len(annotators)]
            assignments[annotator].append(sample)

        # Add overlap samples to all annotators
        overlap_samples = samples[:overlap]
        for annotator in annotators:
            assignments[annotator].extend(overlap_samples)

        return assignments

    def calculate_agreement(self, results: dict) -> float:
        """Calculate inter-rater agreement using Cohen's Kappa"""
        # Find overlapping samples
        annotator_list = list(results.keys())

        if len(annotator_list) < 2:
            return 1.0  # Single annotator always agrees with self

        scores_annotator_1 = results[annotator_list[0]]
        scores_annotator_2 = results[annotator_list[1]]

        # Find overlapping IDs
        overlap_ids = set(scores_annotator_1.keys()) & set(scores_annotator_2.keys())

        scores_1 = [scores_annotator_1[id] for id in overlap_ids]
        scores_2 = [scores_annotator_2[id] for id in overlap_ids]

        from sklearn.metrics import cohen_kappa_score
        return cohen_kappa_score(scores_1, scores_2)

    @staticmethod
    def aggregate_annotations(results: dict, overlap_only: bool = False) -> dict:
        """
        Combine annotations from multiple annotators
        For each sample, take average or majority vote
        """
        aggregated = {}

        # Collect all sample IDs
        all_ids = set()
        for annotator_results in results.values():
            all_ids.update(annotator_results.keys())

        for sample_id in all_ids:
            scores = []
            for annotator, annotator_results in results.items():
                if sample_id in annotator_results:
                    scores.append(annotator_results[sample_id])

            aggregated[sample_id] = {
                "mean": np.mean(scores),
                "std": np.std(scores),
                "num_annotators": len(scores)
            }

        return aggregated
```

### Step 4: A/B Testing and Model Comparison
Rigorously compare two models using statistical tests.

**A/B Test Design**:
```python
class ABTest:
    """
    Compare two models: A (baseline) and B (new)
    """

    async def run_ab_test(self, model_a, model_b,
                         test_set: list[dict],
                         num_samples: int = 200) -> dict:
        """
        Run statistical A/B test

        Returns: Which model is better, with confidence
        """

        # Sample from test set
        samples = random.sample(test_set, num_samples)

        scores_a = []
        scores_b = []

        for sample in samples:
            pred_a = await model_a.predict(sample["input"])
            pred_b = await model_b.predict(sample["input"])

            # Evaluate with automated metrics
            score_a = self.evaluate(pred_a, sample["reference"])
            score_b = self.evaluate(pred_b, sample["reference"])

            scores_a.append(score_a)
            scores_b.append(score_b)

        # Perform statistical significance test
        from scipy.stats import ttest_ind

        t_statistic, p_value = ttest_ind(scores_a, scores_b)

        mean_a = np.mean(scores_a)
        mean_b = np.mean(scores_b)
        std_a = np.std(scores_a)
        std_b = np.std(scores_b)

        # Determine winner
        if p_value < 0.05:  # Significance level
            if mean_b > mean_a:
                winner = "B"
                improvement = ((mean_b - mean_a) / mean_a) * 100
            else:
                winner = "A"
                improvement = ((mean_a - mean_b) / mean_b) * 100
        else:
            winner = "Tie"
            improvement = 0

        return {
            "model_a_mean": mean_a,
            "model_a_std": std_a,
            "model_b_mean": mean_b,
            "model_b_std": std_b,
            "t_statistic": t_statistic,
            "p_value": p_value,
            "winner": winner,
            "improvement_percent": improvement,
            "confident": p_value < 0.05
        }
```

### Step 5: Regression Testing
Prevent quality degradation with golden test sets.

**Regression Test Suite**:
```python
class RegressionTestSuite:
    """
    Monitor model quality over time
    Alert if metrics drop below baseline
    """

    def __init__(self, baseline_metrics: dict):
        self.baseline = baseline_metrics  # From previous stable model
        self.history = []

    async def run_regression_test(self, model, test_set: list[dict]) -> dict:
        """
        Evaluate new model against baseline
        """

        results = {}

        for metric_name, baseline_value in self.baseline.items():
            # Compute current metric value
            current_value = await self.compute_metric(
                model,
                test_set,
                metric_name
            )

            regression = baseline_value - current_value  # Positive = degradation
            regression_percent = (regression / baseline_value) * 100

            results[metric_name] = {
                "baseline": baseline_value,
                "current": current_value,
                "regression_absolute": regression,
                "regression_percent": regression_percent,
                "is_regression": regression > 0.01  # Threshold
            }

        # Check if any metric regressed significantly
        significant_regressions = [
            (name, info) for name, info in results.items()
            if info["regression_percent"] > 2  # > 2% degradation
        ]

        if significant_regressions:
            print("REGRESSION DETECTED:")
            for metric_name, info in significant_regressions:
                print(f"  {metric_name}: {info['baseline']:.3f} → {info['current']:.3f}")
            return {"status": "FAIL", "details": significant_regressions}
        else:
            print("✓ No regressions detected")
            return {"status": "PASS", "details": results}

    async def compute_metric(self, model, test_set: list[dict],
                            metric_name: str) -> float:
        """Compute specific metric on test set"""
        predictions = []
        references = []

        for sample in test_set:
            pred = await model.predict(sample["input"])
            predictions.append(pred)
            references.append(sample["reference"])

        # Use automated metrics
        if metric_name == "bleu":
            from evaluate import load
            bleu = load("bleu")
            return bleu.compute(predictions=predictions, references=references)["bleu"]

        elif metric_name == "accuracy":
            from sklearn.metrics import accuracy_score
            return accuracy_score(references, predictions)

        # ... other metrics
```

### Step 6: Bias Detection and Mitigation
Measure and address fairness issues across demographics.

**Bias Evaluation**:
```python
class BiasDetection:
    """
    Detect bias in AI outputs across demographics
    """

    async def evaluate_demographic_parity(self, model,
                                         test_set: list[dict],
                                         demographic_field: str) -> dict:
        """
        Check if model performs equally well across demographics

        Metric: Demographic Parity
        Fair if P(Y=1|D=A) ≈ P(Y=1|D=B) for all demographics
        """

        # Stratify test set by demographic
        demographic_groups = self.stratify_by_demographic(test_set, demographic_field)

        results = {}

        for demographic, samples in demographic_groups.items():
            predictions = []
            references = []

            for sample in samples:
                pred = await model.predict(sample["input"])
                predictions.append(pred)
                references.append(sample["reference"])

            # Compute metric (e.g., accuracy)
            accuracy = self.compute_accuracy(predictions, references)
            results[demographic] = accuracy

        # Check for disparity
        max_accuracy = max(results.values())
        min_accuracy = min(results.values())
        disparity = max_accuracy - min_accuracy

        return {
            "per_demographic": results,
            "max_disparity": disparity,
            "fair": disparity < 0.05,  # < 5% disparity is acceptable
            "recommendation": (
                "OK" if disparity < 0.05
                else "Retrain with balanced data" if disparity < 0.10
                else "Consider demographic-specific models"
            )
        }

    async def evaluate_equal_opportunity(self, model,
                                        test_set: list[dict],
                                        demographic_field: str) -> dict:
        """
        Check if model has equal true positive rate across demographics

        Fair if TPR(D=A) ≈ TPR(D=B)
        """
        from sklearn.metrics import confusion_matrix

        demographic_groups = self.stratify_by_demographic(test_set, demographic_field)
        results = {}

        for demographic, samples in demographic_groups.items():
            predictions = []
            references = []

            for sample in samples:
                pred = await model.predict(sample["input"])
                predictions.append(pred)
                references.append(sample["reference"])

            # True positive rate
            tn, fp, fn, tp = confusion_matrix(references, predictions).ravel()
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

            results[demographic] = tpr

        # Check equality
        max_tpr = max(results.values())
        min_tpr = min(results.values())
        disparity = max_tpr - min_tpr

        return {
            "per_demographic_tpr": results,
            "tpr_disparity": disparity,
            "fair": disparity < 0.10,
            "recommendation": (
                "OK" if disparity < 0.10
                else "Review training data; ensure balanced positive examples"
            )
        }
```

### Step 7: Evaluation Dataset Versioning
Version and maintain evaluation datasets for reproducibility.

**Dataset Versioning**:
```python
class EvaluationDatasetManager:
    """
    Manage versions of evaluation datasets
    Track changes, ensure reproducibility
    """

    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.versions = {}

    def create_version(self, samples: list[dict], metadata: dict) -> str:
        """
        Create new version of evaluation dataset

        Returns: version ID (e.g., "v1.2.3")
        """
        version_id = self.next_version()

        version_data = {
            "id": version_id,
            "created_at": now(),
            "num_samples": len(samples),
            "samples": samples,
            "metadata": metadata,
            "hash": hashlib.sha256(
                json.dumps(samples, sort_keys=True).encode()
            ).hexdigest()
        }

        self.versions[version_id] = version_data

        # Store to database for persistence
        self.save_version(version_data)

        return version_id

    def next_version(self) -> str:
        """Generate next semantic version"""
        if not self.versions:
            return "v1.0.0"

        last_version = max(self.versions.keys())
        # Parse and increment version
        major, minor, patch = map(int, last_version[1:].split("."))
        return f"v{major}.{minor}.{patch + 1}"

    def get_version(self, version_id: str) -> dict:
        """Retrieve specific dataset version"""
        return self.versions.get(version_id)

    def diff_versions(self, version_a: str, version_b: str) -> dict:
        """Compare two versions"""
        data_a = self.get_version(version_a)
        data_b = self.get_version(version_b)

        samples_a = set(sample["id"] for sample in data_a["samples"])
        samples_b = set(sample["id"] for sample in data_b["samples"])

        return {
            "added": samples_b - samples_a,
            "removed": samples_a - samples_b,
            "num_changes": len((samples_a | samples_b) - (samples_a & samples_b))
        }
```

## Output Template

**Evaluation Framework Document**:
```markdown
# [Model/System Name] Evaluation Framework

## Evaluation Dimensions
[Rubrics for each quality dimension]

## Metrics
[Automated metrics used with rationale]

## Human Evaluation Protocol
[Annotator instructions, calibration results]

## Test Sets
[Train/val/test split, versioning, size]

## Baseline Results
[Previous best results as reference]

## Bias Assessment
[Results for demographic parity, equal opportunity]

## Success Criteria
[Thresholds for each metric]
```

## Quality Gates

1. **Rubric Calibration Kappa >= 0.75**: Annotators agree substantially
2. **Automated Metrics Validated**: Correlation with human judgment >= 0.80
3. **Test Set Coverage**: Representative of production distribution
4. **Bias Assessment Complete**: Minimum disparity < 5% for critical applications
5. **A/B Test Powered**: Sample size sufficient for statistical significance
6. **Regression Tests Passing**: All metrics above baseline thresholds
7. **Evaluation Dataset Versioned**: Full audit trail maintained

## Examples

### Good Evaluation: LLM-Generated Summaries
```
Rubric Dimensions:
- Relevance: Does summary capture main findings?
- Accuracy: Are facts correct vs original?
- Conciseness: Is it appropriately brief?

Metrics:
- Automated: ROUGE-1 F1, BERTScore F1
- Human: 3-point Likert scale per dimension

A/B Test Results:
- Model A (GPT-3.5): 0.72 ROUGE, 3.2/5 human rating
- Model B (GPT-4): 0.81 ROUGE, 4.1/5 human rating
- Improvement: +12.5% ROUGE, +28% human rating
- Significance: p < 0.001 ✓ Statistically significant

Bias Check:
- English native speakers: 4.0/5
- English non-native: 3.9/5
- Disparity: 0.1 ✓ Fair
```

## Common Mistakes

1. **Evaluating on Training Data**
   - ❌ Test model on same samples used in development
   - ✓ Hold out separate test set, evaluate after training complete

2. **Single Metric / No Triangulation**
   - ❌ Use only BLEU score for summarization
   - ✓ Combine ROUGE, BERTScore, human evaluation

3. **No Bias Assessment**
   - ❌ Model performs well on average; ignore per-demographic results
   - ✓ Always test demographic parity and equal opportunity

4. **Underpowered A/B Tests**
   - ❌ Test on 10 samples, declare winner (high variance)
   - ✓ Test on 200+ samples, use proper statistical test

5. **No Regression Monitoring**
   - ❌ Deploy new version without checking vs baseline
   - ✓ Automated regression tests before deployment

## Anti-Patterns

1. **Cherry-Picking Test Sets**
   - ❌ Use only easy examples to evaluate model
   - ✓ Stratified random sampling from full distribution

2. **Changing Evaluation Methodology**
   - ❌ Use different metrics for each model comparison
   - ✓ Standardize on single evaluation framework

3. **Human Evaluation Without Calibration**
   - ❌ Ask annotators to score without rubric training
   - ✓ Calibration session first; measure inter-rater agreement
