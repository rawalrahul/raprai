---
name: data-labeling-guide
description: "Create comprehensive annotation guidelines with task definitions, label taxonomies, decision trees for ambiguous cases, quality metrics (inter-annotator agreement, Cohen's kappa), annotator training, calibration, edge case documentation, and feedback loops."
category: ai-automation
difficulty: intermediate
model_boost: "Fixes ML training failures caused by poor-quality labels; enables systematic label generation at scale"
---

# Data Labeling Guide

## Purpose
This skill teaches you to systematize data annotation so that multiple annotators produce consistent, high-quality labels for machine learning training. You'll create clear labeling instructions with examples, define label taxonomies, document edge cases and their resolution, measure inter-rater reliability, conduct annotator training, track label quality, and improve through feedback loops. The output is a reusable labeling system that produces training data good enough for production models.

## When to Use
- Building training datasets from scratch (no pre-labeled data)
- Fine-tuning models requiring domain-specific labels
- Creating datasets larger than one person can reasonably label
- Projects where label quality directly impacts model accuracy (NLU, medical imaging, content moderation)
- **Do NOT use when**: Using existing labeled datasets, pure zero-shot approaches, or synthetic data generation

## Instructions

### Step 1: Task Definition and Label Taxonomy Design
Define exactly what annotators need to label and what labels are valid.

**Task Definition Template**:
```yaml
labeling_task:
  id: "email_sentiment_classification"
  name: "Classify customer email sentiment"
  description: "Categorize incoming customer support emails by emotional tone"

  objective:
    - Primary: "Classify whether email expresses positive, negative, or neutral sentiment"
    - Secondary: "Identify underlying emotions (frustration, satisfaction, urgency)"

  input_definition:
    format: "Raw customer email text"
    length_range: "1 sentence to 10 paragraphs"
    examples:
      - "Your product is amazing! Best purchase I've made."
      - "Still waiting for support. Very frustrated. This is unacceptable."
      - "Question about shipping costs for order #12345"

  output_definition:
    label_set: ["positive", "negative", "neutral"]
    required_fields:
      - primary_sentiment: "One of {positive, negative, neutral}"
      - confidence: "How confident are you? [very_low, low, medium, high, very_high]"
    optional_fields:
      - emotion_tags: "List of emotions detected (frustration, satisfaction, urgency, etc.)"
      - customer_issue_category: "Type of issue (billing, product, shipping, account, other)"

  success_criteria:
    - Inter-rater agreement (Cohen's Kappa) >= 0.75
    - Annotator training accuracy >= 90% on gold standard examples
    - Time to label: 1-2 minutes per email (baseline)

  edge_case_handling:
    - Sarcasm: "Treat literally opposite meaning (e.g., 'Great job!' said sarcastically = negative)"
    - Mixed sentiment: "If >30% of email is positive and >30% negative, label as 'mixed' or take primary sentiment"
    - Non-English: "Flag and escalate; do not attempt to label"
    - Spam/Gibberish: "Label as 'neutral' and mark spam_flag=true"
```

**Label Taxonomy Design**:
```yaml
label_taxonomy:
  sentiment:
    level_1: [positive, negative, neutral]
    level_2:
      positive:
        - highly_satisfied
        - satisfied
        - optimistic
      negative:
        - frustrated
        - angry
        - disappointed
      neutral:
        - informational
        - transactional
        - factual_only

  # Hierarchical taxonomy: allows different granularity levels
  # Annotators can label at appropriate level of detail

  validity_rules:
    - "Each email must have exactly one level_1 label"
    - "level_2 label optional; if present, must be child of level_1"
    - "Confidence score required for all labels"

  dependencies:
    - "If sentiment = positive AND contains_complaint = true: Mark as edge case"
    - "If confidence < 'medium': Annotator should flag for review"
```

**Anti-Examples and Boundary Cases**:
```yaml
boundary_cases:
  case_1:
    input: "The product works, but shipping took 3 weeks. Disappointed."
    rationale: "Mixed sentiment: satisfied with product (positive), but unhappy with service (negative). Primary sentiment = negative (recency bias: last statement)"
    correct_label: "negative"
    why_not_other: "Not 'positive' because overall experience negative. Not 'neutral' because strong emotions expressed."

  case_2:
    input: "Just checking on my order. When will it arrive?"
    rationale: "Transactional, no emotion expressed."
    correct_label: "neutral"
    why_not_other: "Not positive/negative; purely informational"

  case_3:
    input: "LOL your customer service is absolutely terrible!! 😡"
    rationale: "Sarcasm detector: 'terrible' = negative, anger emoji confirms. Despite 'LOL', sentiment is negative."
    correct_label: "negative"
    why_not_other: "Sarcasm + emotion cues override casual 'LOL' opener"

  case_4:
    input: "I've emailed 5 times and no response. This is ridiculous."
    rationale: "High frustration, unresolved issue. Multiple failed interactions."
    correct_label: "negative"
    emotion_tags: ["frustrated", "angry", "urgency"]
```

### Step 2: Annotation Guidelines and Decision Tree
Create step-by-step instructions to guide annotators.

**Annotation Process Flow**:
```
Step 1: Read email carefully
  └─ Are there unclear terms? (proceed to glossary)

Step 2: Identify primary emotion/tone
  ├─ Is there a clear positive tone? (satisfied, grateful, excited)
  │  └─ Label: "positive" → Go to Step 4
  ├─ Is there a clear negative tone? (frustrated, angry, disappointed)
  │  └─ Label: "negative" → Go to Step 4
  └─ Is tone neutral/transactional? (purely informational, no emotion)
     └─ Label: "neutral" → Go to Step 4

Step 3: Handle mixed sentiment (if applicable)
  ├─ Is >20% of email positive AND >20% negative?
  │  ├─ Is there a primary concern (recent event, repeated theme)?
  │  │  └─ Label based on primary concern
  │  └─ Unclear primary: Mark confidence = "low"

Step 4: Assign confidence level
  ├─ Very clear: confidence = "very_high"
  ├─ Mostly clear: confidence = "high"
  ├─ Somewhat ambiguous: confidence = "medium"
  ├─ Quite unclear: confidence = "low"
  └─ Completely uncertain: confidence = "very_low"

Step 5: Optional - Tag secondary emotions
  ├─ frustration: "Expressions of annoyance, impatience"
  ├─ satisfaction: "Expressions of happiness, gratitude"
  ├─ urgency: "Time-sensitive requests or complaints"
  └─ resignation: "Giving up, accepting negative outcome"

Step 6: Submit and move to next
```

**Decision Tree Diagram**:
```
                        Read Email
                            |
                   Identify Primary Tone?
                    /         |         \
                Positive?   Neutral?    Negative?
                /             |            \
            POSITIVE        NEUTRAL       NEGATIVE
              |               |              |
         Assign         Assign           Assign
         Confidence     Confidence       Confidence
            |               |              |
         Done            Done            Done
```

**Glossary of Terms**:
```yaml
glossary:
  frustrated:
    definition: "Feeling annoyed, impatient, or blocked from achieving goal"
    indicators:
      - "Repeated use of 'still waiting', 'no response', 'unacceptable'"
      - "Exclamation marks or caps for emphasis"
      - "Questions like 'When will this be fixed?'"
    examples:
      - ❌ Email: "I've waited 2 weeks with no update. When will you respond?"
        Indicator: Repeated waiting, impatience
      - ✓ Label: frustrated (negative)

  sarcasm:
    definition: "Saying opposite of what you mean for ironic effect"
    indicators:
      - "Contradiction between words and tone (e.g., LOL + angry emoji)"
      - "Overly enthusiastic phrasing + negative context"
      - "Exclamation + context is negative"
    examples:
      - ❌ Email: "Oh great, another billing error! 🙄"
      - Indicator: 'Oh great' = sarcasm, emoji = sarcasm cue
      - ✓ Treat as: negative (opposite of literal meaning)

  mixed_sentiment:
    definition: "Email contains both positive and negative sentiments"
    handling_rule: "If both >20%, identify PRIMARY concern (recency, emphasis, repeated theme)"
    examples:
      - ❌ Email: "Product quality is excellent! Unfortunately, shipping took 3 weeks."
        Primary: Negative (shipping is explicit complaint, recency)
      - ✓ Label: negative
```

### Step 3: Quality Metrics and Inter-Annotator Agreement
Measure consistency to ensure label quality.

**Cohen's Kappa Calculation**:
```python
from sklearn.metrics import cohen_kappa_score
import numpy as np

def calculate_cohens_kappa(annotator1_labels: list,
                          annotator2_labels: list) -> float:
    """
    Measure agreement between two annotators
    Accounts for chance agreement

    Interpretation:
    - 0.81-1.00: Almost perfect agreement
    - 0.61-0.80: Substantial agreement
    - 0.41-0.60: Moderate agreement
    - 0.21-0.40: Fair agreement
    - < 0.20: Slight agreement
    - <= 0: No agreement / worse than random

    Target: >= 0.75 for production data
    """

    kappa = cohen_kappa_score(annotator1_labels, annotator2_labels)
    return kappa

# Example
annotator1 = ['positive', 'negative', 'positive', 'neutral', 'positive']
annotator2 = ['positive', 'negative', 'positive', 'neutral', 'negative']
# One disagreement on last example

kappa = calculate_cohens_kappa(annotator1, annotator2)
# kappa = 0.78 (substantial agreement)
```

**Confusion Matrix Analysis**:
```python
from sklearn.metrics import confusion_matrix
import pandas as pd

def analyze_disagreements(annotator1: list, annotator2: list,
                         labels: list) -> dict:
    """
    Analyze where annotators disagree
    Identify confusing label pairs
    """

    cm = confusion_matrix(annotator1, annotator2, labels=labels)
    df = pd.DataFrame(cm, index=labels, columns=labels)

    print("Confusion Matrix:")
    print(df)

    # Find most common mistakes
    disagreements = []
    for i, label_i in enumerate(labels):
        for j, label_j in enumerate(labels):
            if i != j and cm[i][j] > 0:
                disagreements.append({
                    "from": label_i,
                    "to": label_j,
                    "count": cm[i][j],
                    "pct": cm[i][j] / cm[i].sum()
                })

    disagreements.sort(key=lambda x: x["count"], reverse=True)
    print("\nTop disagreements:")
    for d in disagreements[:5]:
        print(f"  {d['from']} → {d['to']}: {d['count']} times ({d['pct']:.1%})")

    return {"confusion_matrix": df, "top_disagreements": disagreements}

# Example output:
"""
Confusion Matrix:
           positive  negative  neutral
positive        85         8         7
negative         3        92         5
neutral          6         4        90

Top disagreements:
  positive → neutral: 8 times (8.6%)
  negative → neutral: 5 times (5.1%)
"""
```

### Step 4: Annotator Training and Calibration
Train annotators and measure their competence.

**Training Protocol**:
```python
class AnnotatorTraining:
    """
    Train annotators and measure readiness to label data
    """

    async def run_training_session(self, annotator_id: str,
                                  training_examples: list[dict],
                                  target_accuracy: float = 0.90):
        """
        1. Present training examples with explanations
        2. Have annotator label subset
        3. Compare to gold labels
        4. Repeat until target accuracy achieved
        """

        round_num = 0
        accuracy = 0

        while accuracy < target_accuracy and round_num < 5:
            round_num += 1

            # Present training subset (10-20 examples)
            sample_size = min(20, len(training_examples))
            training_subset = random.sample(training_examples, sample_size)

            print(f"Round {round_num}: Labeling {sample_size} examples...")

            # Annotator labels examples
            annotator_labels = []
            for example in training_subset:
                label = await self.prompt_annotator(annotator_id, example)
                annotator_labels.append(label)

            # Compare to gold labels
            gold_labels = [ex["gold_label"] for ex in training_subset]
            accuracy = self.calculate_accuracy(annotator_labels, gold_labels)

            print(f"Accuracy: {accuracy:.1%}")

            if accuracy < target_accuracy:
                # Provide feedback on mistakes
                mistakes = self.analyze_mistakes(
                    annotator_labels,
                    gold_labels,
                    training_subset
                )

                print("Review these cases:")
                for mistake in mistakes[:3]:
                    print(f"  {mistake['input']}")
                    print(f"    Your label: {mistake['your_label']}")
                    print(f"    Correct: {mistake['gold_label']}")
                    print(f"    Reason: {mistake['explanation']}")

                # Continue to next round
                continue

        if accuracy >= target_accuracy:
            print(f"✓ Training complete. Ready to annotate.")
            return {"status": "approved", "final_accuracy": accuracy}
        else:
            print(f"✗ Did not reach target accuracy after {round_num} rounds")
            return {"status": "rejected", "final_accuracy": accuracy}
```

**Calibration Session**:
```python
class CalibrationSession:
    """
    Run joint calibration where annotators discuss disagreements
    Align on edge cases and improve collective understanding
    """

    async def run_calibration(self, annotators: list[str],
                             calibration_examples: list[dict],
                             target_kappa: float = 0.75):
        """
        1. All annotators independently label same set
        2. Discuss disagreements
        3. Revise understanding
        4. Repeat until sufficient agreement
        """

        round_num = 0
        kappa = 0

        while kappa < target_kappa and round_num < 3:
            round_num += 1

            print(f"Calibration Round {round_num}")

            # All annotators label same examples
            all_annotations = {}
            for annotator in annotators:
                all_annotations[annotator] = []
                for example in calibration_examples:
                    label = await self.prompt_annotator(annotator, example)
                    all_annotations[annotator].append(label)

            # Calculate pairwise agreement
            kappas = []
            for i in range(len(annotators)):
                for j in range(i + 1, len(annotators)):
                    pairwise_kappa = cohen_kappa_score(
                        all_annotations[annotators[i]],
                        all_annotations[annotators[j]]
                    )
                    kappas.append(pairwise_kappa)

            avg_kappa = np.mean(kappas)
            print(f"Average pairwise Kappa: {avg_kappa:.3f}")

            if avg_kappa >= target_kappa:
                print("✓ Calibration complete")
                return {"status": "complete", "final_kappa": avg_kappa}

            # Find major disagreements
            disagreements = self.find_disagreement_examples(
                all_annotations,
                calibration_examples
            )

            print(f"Found {len(disagreements)} disagreements")
            print("Discussing the following cases:")

            for example in disagreements[:5]:
                print(f"\nExample: {example['input'][:100]}...")
                for annotator in annotators:
                    print(f"  {annotator}: {example['annotations'][annotator]}")

            print("\nReview the guidelines and try again.")

        return {"status": "incomplete", "final_kappa": avg_kappa}
```

### Step 5: Edge Case Documentation
Create a reference guide for difficult examples.

**Edge Case Log**:
```yaml
edge_case_log:
  version: "1.2.0"
  last_updated: "2024-01-15"

  cases:
    - id: "edge_001"
      category: "sarcasm"
      example:
        input: "Oh great, another shipping delay! 😒"
        annotator1_label: "positive"
        annotator2_label: "negative"

      resolution:
        correct_label: "negative"
        rule: "Ignore literal 'great'; use emoji + context clues"
        explanation: "Sarcasm detector: sarcasm cues (😒, caps, exclamation) override literal words"

      added_to_guidelines: "Yes"
      update_version: "1.1.0"

    - id: "edge_002"
      category: "mixed_sentiment"
      example:
        input: "Product is excellent but support is terrible. Very disappointed overall."
        annotator1_label: "positive"
        annotator2_label: "negative"

      resolution:
        correct_label: "negative"
        rule: "When mixed, use recency and emphasis. 'Very disappointed' is final, strong statement."
        explanation: "Email states both positive (product) and negative (support), but concludes with strong negative. Use conclusion as primary."

      added_to_guidelines: "Yes"
      update_version: "1.1.0"

    - id: "edge_003"
      category: "non_english"
      example:
        input: "Das Produkt ist sehr gut, aber ich bin unzufrieden mit dem Service."
        annotator1_label: "negative"
        annotator2_label: "escalate"

      resolution:
        correct_label: "ESCALATE_DO_NOT_LABEL"
        rule: "If email is in language other than English, mark as escalate. Do not attempt to label."
        explanation: "Task is English-language sentiment classification. Non-English emails should be flagged for human review or translation."

      added_to_guidelines: "Yes"
      update_version: "1.0.0"
```

### Step 6: Labeling Quality Monitoring
Track quality throughout annotation campaign.

**Quality Dashboard**:
```python
class QualityMonitor:
    """
    Track labeling quality metrics in real-time
    Alert if quality drops
    """

    def __init__(self):
        self.annotator_stats = {}
        self.quality_history = []

    async def track_annotation(self, annotator_id: str,
                              example_id: str,
                              label: str,
                              gold_label: str = None,
                              confidence: float = None):
        """
        Track individual annotation
        Update running statistics
        """

        if annotator_id not in self.annotator_stats:
            self.annotator_stats[annotator_id] = {
                "count": 0,
                "correct": 0,
                "accuracy": 0,
                "avg_confidence": 0,
                "confidence_list": []
            }

        stats = self.annotator_stats[annotator_id]
        stats["count"] += 1

        if gold_label and label == gold_label:
            stats["correct"] += 1

        stats["accuracy"] = stats["correct"] / stats["count"]

        if confidence:
            stats["confidence_list"].append(confidence)
            stats["avg_confidence"] = np.mean(stats["confidence_list"])

        # Alert if accuracy drops
        if stats["count"] > 20 and stats["accuracy"] < 0.80:
            print(f"⚠️  WARNING: {annotator_id} accuracy below 80% ({stats['accuracy']:.1%})")
            return {"status": "alert", "reason": "low_accuracy"}

        return {"status": "ok"}

    def get_annotator_report(self, annotator_id: str) -> dict:
        """Generate annotator performance report"""
        stats = self.annotator_stats.get(annotator_id, {})
        return {
            "annotator": annotator_id,
            "labels_completed": stats.get("count", 0),
            "accuracy": stats.get("accuracy", 0),
            "avg_confidence": stats.get("avg_confidence", 0),
            "status": "good" if stats.get("accuracy", 0) >= 0.85 else "needs_review"
        }
```

### Step 7: Feedback Loops and Continuous Improvement
Use annotation results to improve guidelines.

**Feedback Loop Process**:
```python
class AnnotationFeedbackLoop:
    """
    Systematically improve labeling process based on results
    """

    async def analyze_and_improve(self, completed_annotations: list[dict],
                                 inter_rater_kappa: float):
        """
        1. Analyze disagreements
        2. Identify systematic issues
        3. Update guidelines
        4. Re-label disputed cases
        5. Measure improvement
        """

        # Step 1: Identify problem cases
        disagreement_cases = [
            ann for ann in completed_annotations
            if len(ann["annotator_labels"]) > 1 and
               not all(x == ann["annotator_labels"][0] for x in ann["annotator_labels"])
        ]

        print(f"Found {len(disagreement_cases)} cases with disagreement")

        if len(disagreement_cases) == 0:
            print("✓ All cases agreed. No improvements needed.")
            return

        # Step 2: Categorize disagreements
        disagreement_categories = {}
        for case in disagreement_cases:
            # Use label taxonomy to categorize
            category = self.categorize_disagreement(case)
            if category not in disagreement_categories:
                disagreement_categories[category] = []
            disagreement_categories[category].append(case)

        # Print top disagreement sources
        print("\nTop disagreement sources:")
        for cat, cases in sorted(
            disagreement_categories.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]:
            print(f"  {cat}: {len(cases)} cases ({len(cases)/len(disagreement_cases):.1%})")

        # Step 3: Update guidelines if pattern detected
        if len(disagreement_cases) > len(completed_annotations) * 0.10:
            # > 10% disagreement = systematic issue
            print("\nRecommending guideline updates:")
            print("- Add edge cases to documentation")
            print("- Clarify ambiguous definitions")
            print("- Provide more decision tree examples")

        # Step 4: Measure improvement in next batch
        print("\nImplementing improvements and re-training annotators...")
        # Conduct calibration session with new guidance
        new_kappa = await self.recalibrate_annotators()
        improvement = ((new_kappa - inter_rater_kappa) / inter_rater_kappa) * 100
        print(f"Kappa improved by {improvement:.1f}% (from {inter_rater_kappa:.3f} to {new_kappa:.3f})")
```

## Output Template

**Annotation Guidelines Document**:
```markdown
# [Task Name] Annotation Guidelines v1.0

## Task Overview
[Definition, objective, scope]

## Labels and Taxonomy
[Valid labels, hierarchical structure if any]

## Annotation Process
[Step-by-step instructions with decision tree]

## Examples and Anti-Examples
[10+ annotated examples with explanations]

## Glossary
[Definitions of confusing terms]

## Edge Cases
[Known difficult cases with resolutions]

## Quality Standards
[Target inter-rater agreement, accuracy thresholds]

## FAQ
[Common questions from annotators]
```

## Quality Gates

1. **Inter-Rater Kappa >= 0.75**: Substantial agreement between annotators
2. **Training Accuracy >= 90%**: Annotators pass competency test
3. **Calibration Kappa >= 0.75**: Aligned understanding after discussion
4. **Production Accuracy >= 85%**: Each annotator maintains accuracy
5. **Edge Case Coverage >= 90%**: All identified edge cases documented
6. **Label Distribution Reasonable**: No class imbalance > 90/10
7. **Feedback Loop Closed**: Improvements documented and implemented

## Examples

### Good Annotation Guidelines: Email Sentiment
```
Task: Classify customer support email sentiment

Labels: positive, negative, neutral

Process:
1. Read email (2-3 times if needed)
2. Identify primary tone
3. Assign confidence
4. Label

Example: "Product is great but shipping was slow."
- Analysis: Mixed sentiment
- Primary: Negative (recent complaint, explicit 'slow')
- Label: negative
- Confidence: high (clear negative recency)

Calibration Kappa: 0.82 ✓ Excellent agreement
Training accuracy: 92% ✓ All annotators ready
```

## Common Mistakes

1. **Vague Label Definitions**
   - ❌ "positive = likes it, negative = doesn't"
   - ✓ "positive = email expresses gratitude, satisfaction, or excitement"

2. **No Training / Calibration**
   - ❌ Hand off guidelines and expect consistency
   - ✓ Train each annotator, run calibration, measure Kappa

3. **Ignoring Disagreements**
   - ❌ Two annotators disagree; just take majority vote
   - ✓ Analyze disagreement, update guidelines, re-label

4. **Labels Without Context**
   - ❌ "Label each sentence independently"
   - ✓ "Consider full email context when labeling"

## Anti-Patterns

1. **Too-Fine-Grained Taxonomy**
   - ❌ 50+ label categories (impossible to distinguish consistently)
   - ✓ 3-5 core labels, optional secondary categories

2. **Changing Guidelines Mid-Annotation**
   - ❌ Clarify label definition after 500 emails labeled (inconsistency)
   - ✓ Finalize guidelines before scaling; document all changes with version
