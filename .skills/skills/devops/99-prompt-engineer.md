---
name: prompt-engineer
description: "Design, test, and iterate AI prompts using few-shot examples, chain-of-thought reasoning, self-consistency voting, and A/B testing to maximize model performance on your task."
category: devops
difficulty: intermediate
model_boost: "Fixes vague prompts that get poor model output; teaches systematic prompt optimization"
---

# Prompt Engineer

## Purpose

Large language models (LLMs) are tools that respond to text input (prompts). A bad prompt gets bad output; a well-designed prompt gets reliable, useful output. This skill provides techniques to write better prompts: few-shot examples to guide the model, chain-of-thought reasoning to improve logic, self-consistency voting to pick best answers, and A/B testing to measure improvements. You'll exit with a systematic process to go from mediocre prompts to reliably good ones.

## When to Use

- You're using Claude, GPT-4, or other LLMs for production tasks
- Model outputs are unreliable or off-target
- You want to improve model accuracy without fine-tuning
- You're building an AI application and need repeatable quality
- You're struggling to get the model to follow instructions
- **Do NOT use when**: You have <10 examples to test with (not enough data), or you need guaranteed correctness (LLMs are probabilistic; use traditional code for safety-critical)

## Instructions

### Step 1: Clarify Your Task

Define what success looks like before writing the prompt.

**Task definition**:

```
Task: Classify customer support emails as bug report, feature request, or complaint

Input: Email text
Output: Classification + confidence (high/medium/low)

Example success:
- Email: "Your app crashes when I upload large files"
- Expected output: bug_report (high confidence)

Example of failure:
- Model outputs: confused response, wrong classification, nonsense

Success metric: 95%+ accuracy on held-out test set of 100 emails
```

**Be specific**:
- What's the input? (Text, number, structured data?)
- What's the output? (Classification, generation, summarization?)
- What are edge cases? (Ambiguous emails, emails that mix categories?)
- How will you measure success? (Accuracy, human review, business metric?)

### Step 2: Start Simple, Then Iterate

Begin with a basic prompt. Don't over-engineer before testing.

**Bad (too complex)**:
```
You are an expert customer support analyst with 20 years of experience...
Consider linguistic nuances, cultural context, implicit meanings...
[20 paragraphs of instructions]
Classify the email into one of three categories...
```

**Good (simple first)**:
```
Classify this email as: bug_report, feature_request, or complaint

Email: [TEXT]

Classification:
```

Test this simple version. If it works, done. If not, improve incrementally.

### Step 3: Add Few-Shot Examples

Few-shot learning: Show the model examples of correct input/output pairs.

**Zero-shot** (no examples):
```
Classify this email: "Your app crashes when..."
Classification: [model guesses]
```

**Few-shot** (examples):
```
Examples:

Email: "When I upload large files, the app crashes. Can you fix this?"
Classification: bug_report

Email: "I'd love an offline mode for your app."
Classification: feature_request

Email: "Your customer service is terrible. No one responds."
Classification: complaint

Now classify this:
Email: "Your app crashes when..."
Classification:
```

**Guidelines for examples**:
- Use real examples from your data (not synthetic)
- Include edge cases (borderline examples)
- Balance classes (if you have 2 bug reports, show 2; not 10)
- Use 2-5 examples (more doesn't always help; sometimes hurts)

### Step 4: Use Chain-of-Thought Reasoning

Chain-of-thought: Ask the model to explain its reasoning step-by-step.

**Without chain-of-thought**:
```
Classify: "Your app crashes when I upload large files"
Classification: bug_report
```

**With chain-of-thought**:
```
Classify: "Your app crashes when I upload large files"

Let's think step by step:
1. The email describes a problem: "app crashes"
2. This is a malfunction, not a feature request
3. It's a factual issue, not a complaint about service
4. Classification: bug_report

Confidence: high
```

Chain-of-thought often improves accuracy, especially on complex tasks.

### Step 5: Test and Measure

Create a test set and measure accuracy.

**Test set** (hold out 10-20% of data):

```
Test set: 20 emails (5 each of bug, feature, complaint)

Prompt 1 (simple):
- Accuracy: 75% (15/20 correct)

Prompt 2 (with examples):
- Accuracy: 90% (18/20 correct)

Prompt 3 (with chain-of-thought):
- Accuracy: 95% (19/20 correct)

Winner: Prompt 3
```

**Test script** (pseudocode):

```python
test_emails = [
    {"email": "...", "expected": "bug_report"},
    {"email": "...", "expected": "feature_request"},
    # ... 18 more
]

correct = 0
for test in test_emails:
    output = claude.prompt(test['email'])
    if output['classification'] == test['expected']:
        correct += 1

accuracy = correct / len(test_emails)
print(f"Accuracy: {accuracy * 100}%")
```

### Step 6: Self-Consistency Voting

For tasks where accuracy matters, run multiple times and vote.

**Self-consistency approach**:

```
For each email, run classification 3 times.
Output whichever classification appears most frequently.

Email: "Your app crashes when..."

Run 1: bug_report (confidence: high)
Run 2: bug_report (confidence: high)
Run 3: complaint (confidence: medium)

Voting result: bug_report (2/3 votes)
Final output: bug_report (high confidence)

For single-run outputs, confidence would be uncertain.
Voting makes it more reliable.
```

**Cost**: Voting 3x costs 3x API calls, but increases accuracy significantly.

**When to use voting**:
- High-stakes tasks (legal, financial classification)
- Complex reasoning tasks
- When accuracy is more important than latency

### Step 7: Prompt Template and Variables

Generalize your prompt so it works across inputs.

**Template** (with variables):

```
You are a customer support classifier.

Examples:

Email: "When I upload large files, the app crashes."
Classification: bug_report

Email: "Can you add offline mode?"
Classification: feature_request

Email: "Your support team never responds!"
Classification: complaint

Now classify this email:

Email: {{EMAIL_TEXT}}

Classification: {{OUTPUT}}

Confidence: {{CONFIDENCE_LEVEL}}
```

Use placeholders ({{VARIABLE}}) that you fill in for each input. This makes prompts reusable and testable.

### Step 8: A/B Test Prompt Variants

Test multiple prompt variations to find the best.

**Variant A** (simple):
```
Classify: [EMAIL]
Classification:
```

**Variant B** (with examples):
```
[Examples]
Classify: [EMAIL]
Classification:
```

**Variant C** (with chain-of-thought):
```
[Examples]
[EMAIL]
Let's think step by step:
...
Classification:
```

**Test on same 20 examples**:

```
Variant A: 75% accuracy (15/20)
Variant B: 90% accuracy (18/20)
Variant C: 95% accuracy (19/20)

Winner: Variant C
```

Use Variant C going forward. Test new variants quarterly or when requirements change.

### Step 9: Error Analysis

When the model fails, understand why.

**Failed example**:

```
Email: "I want the app to remember my preferences between sessions."
Expected: feature_request
Model output: complaint
Confidence: high (wrong!)

Analysis:
- Model might have misread "remember" as a negative
- Or grouped it with complaint words
- Fix: Add an example similar to this (preference storage request)
```

**Add to examples**:
```
Email: "Can you save my settings between sessions?"
Classification: feature_request
```

Retrain with this example; test again.

### Step 10: Monitor Production Quality

After deploying, monitor real-world performance.

**Monitoring approach**:

```
Weekly report:
- Total classifications: 1,000
- Automated accuracy: 92% (based on examples)
- Manual review sample: 50 emails
- Actual accuracy: 88%
- Gap: 4% (model optimistic on test set)

Identify failure patterns:
- 5 misclassifications: confused feature requests with complaints
- 3 misclassifications: didn't recognize bug reports with vague language

Iterate:
- Add 3 new examples to training set
- Retrain and re-test
- Deploy new version
```

**Continuous improvement**:
- Monthly error analysis
- Quarterly retraining
- Quarterly new A/B tests for further improvements

## Output Template

```
# Prompt Engineering Specification

## Task Definition
- **Input**: [Description]
- **Output**: [Description]
- **Success metric**: [Accuracy / human review / business metric]

## Prompt (Final Version)
```
[Your final prompt here]
```

## Few-Shot Examples
- Example 1: [Input] → [Expected output]
- Example 2: [Input] → [Expected output]
- Example 3: [Input] → [Expected output]

## Test Set
- Size: [N examples]
- Accuracy: [%]
- Failed cases: [List of misclassifications]

## A/B Testing Results
| Variant        | Accuracy | Notes                |
|----------------|----------|----------------------|
| Baseline       | 75%      | Simple prompt        |
| With examples  | 90%      | Few-shot examples    |
| With reasoning | 95%      | Chain-of-thought     |

## Deployment
- Model: [Claude / GPT-4 / other]
- Version: [Prompt version number]
- Production accuracy: [Measured over time]
- Monitoring: [Weekly / monthly review]

## Improvement Roadmap
- [ ] Add self-consistency voting (if high-stakes)
- [ ] Monthly error analysis and retraining
- [ ] Quarterly A/B tests for further optimization
```

## Quality Gates (5+)

1. **Test Set Realistic**: Does your test set represent real data? (Not toy examples.)
2. **Accuracy Measured**: Do you know the actual accuracy, not just "feels good"?
3. **Examples Specific**: Are your few-shot examples specific to your task? (Not generic.)
4. **Failure Analysis Done**: Do you understand when/why the model fails?
5. **Monitoring in Place**: Will you track production quality after deployment?

## Examples

### Good Prompt (Specific, Few-Shot, Measured)

```
Classify customer support emails.

Examples:

Email: "When I upload files >100MB, the app crashes. Can you fix?"
Classification: bug_report

Email: "Can you add a dark mode? Would love it."
Classification: feature_request

Email: "Your support team never responds. Terrible service."
Classification: complaint

Classify this email:

Email: [TEXT]

Classification:
```

**Test accuracy**: 95% (19/20)
**Confidence**: High; ready for production

---

### Bad Prompt (Vague, No Examples)

```
Classify the email.
```

**Test accuracy**: 60% (12/20)
**Problem**: No guidance; model guesses
**Fix**: Add examples and task description

## Common Mistakes (3+)

1. **No Test Set**: You think the prompt is good, deploy it, then discover it fails in production. Test before deploying.

2. **Too Many Examples**: You add 20 examples (trying to be thorough). Model gets confused; accuracy drops. Use 2-5 high-quality examples.

3. **Synthetic Examples**: You make up examples instead of using real data. Model learns patterns from your made-up data, not real data. Use real examples.

4. **No Monitoring**: You deploy and forget about it. 3 months later, drift happens; accuracy drops. Monitor quarterly.

5. **Prompt Versioning**: You keep changing the prompt without tracking which version is deployed. Always version prompts; track which version is in production.

## Anti-Patterns (3+)

1. **Optimization Theater**: You spend 40 hours perfecting a prompt to get 99% accuracy on a test set. Real production drops to 80% (data distribution is different). Instead: start simple, test on real data, iterate.

2. **Model Hallucination**: You ask the model to generate summaries without a few-shot example. Model hallucinates (makes stuff up). Add examples showing what you expect; model improves.

3. **Prompt Length Explosion**: Prompt starts at 100 words; grows to 2000 words as you add edge case handling. Document edge cases separately; keep prompt concise.

4. **No Error Handling**: Prompt assumes inputs are well-formed. Real data is messy (typos, strange formatting). Add instructions: "If input is unclear, explain why instead of guessing."

---

**Next Steps**: Pick a task. Write a simple prompt. Test on 20 examples. Measure accuracy. Add few-shot examples. Retrain. Measure again. Track improvement.
