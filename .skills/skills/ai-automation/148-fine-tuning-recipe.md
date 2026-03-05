---
name: fine-tuning-recipe
description: "Master model fine-tuning with use case validation, dataset preparation, base model selection, hyperparameter tuning, training monitoring, evaluation on held-out set, A/B deployment, and cost estimation."
category: ai-automation
difficulty: advanced
model_boost: "Fixes under-performing models by determining when to fine-tune vs prompt engineering vs RAG; provides systematic hyperparameter optimization"
---

# Fine-Tuning Recipe

## Purpose
This skill teaches you to systematically fine-tune language models to specialize them for your domain or task. You'll learn when fine-tuning is actually needed (vs prompt engineering or RAG), how to prepare high-quality training datasets, select base models, configure hyperparameters scientifically, monitor training, evaluate on held-out data, conduct safe A/B rollouts, and estimate costs. The output is a fine-tuned model that outperforms prompting on your specific task, with documented decision rationale.

## When to Use
- Model doesn't perform adequately with prompting alone (accuracy < target)
- Repeating the same task 100+ times (cost justification)
- Need consistent output format (JSON, structured data)
- Domain-specific language requiring specialized knowledge
- Latency or cost reduction is critical (smaller, cheaper model beats large one)
- **Do NOT use when**: Adequate performance with prompting, task is one-off, or labeled data is unavailable

## Instructions

### Step 1: Use Case Validation and Feasibility Analysis
Determine if fine-tuning is actually the right solution.

**Decision Framework**:
```python
class FinetuneDecisionTool:
    """
    Decide: Fine-tune vs Prompt Engineering vs RAG
    """

    async def should_finetune(self, use_case: dict) -> dict:
        """
        Evaluate feasibility and ROI of fine-tuning

        use_case: {
            "task": "customer intent classification",
            "baseline_accuracy_prompting": 0.75,
            "target_accuracy": 0.95,
            "monthly_volume": 10000,
            "cost_budget": 500
        }
        """

        analysis = {}

        # 1. Performance Gap Analysis
        perf_gap = use_case["target_accuracy"] - use_case["baseline_accuracy_prompting"]
        analysis["performance_gap"] = perf_gap

        if perf_gap <= 0.05:
            return {
                "recommendation": "PROMPTING",
                "reasoning": "Performance gap small; prompting sufficient",
                "analysis": analysis
            }

        # 2. Volume & Cost Analysis
        monthly_prompting_cost = (
            use_case["monthly_volume"] *
            self.cost_per_api_call("gpt-4")
        )
        analysis["monthly_prompting_cost"] = monthly_prompting_cost

        # 3. Fine-tuning Cost
        finetune_training_cost = 500  # Estimate
        monthly_finetune_inference_cost = (
            use_case["monthly_volume"] *
            self.cost_per_api_call("gpt-3.5-turbo")  # Cheaper after fine-tune
        )
        analysis["finetune_training_cost"] = finetune_training_cost
        analysis["monthly_finetune_cost"] = monthly_finetune_inference_cost

        # 4. ROI Calculation
        monthly_savings = monthly_prompting_cost - monthly_finetune_inference_cost
        payback_months = finetune_training_cost / monthly_savings if monthly_savings > 0 else float('inf')

        analysis["monthly_savings"] = monthly_savings
        analysis["payback_months"] = payback_months

        # 5. Data Availability
        labeled_data_available = use_case.get("labeled_examples", 0) >= 100
        analysis["sufficient_training_data"] = labeled_data_available

        if not labeled_data_available:
            return {
                "recommendation": "PROMPTING_WITH_RAG",
                "reasoning": "Insufficient training data for fine-tuning",
                "analysis": analysis
            }

        # 6. Final Decision
        if payback_months < 12 and perf_gap > 0.10:
            return {
                "recommendation": "FINE_TUNE",
                "reasoning": f"Performance gap {perf_gap:.1%}, ROI in {payback_months:.1f} months",
                "analysis": analysis
            }
        elif perf_gap > 0.05:
            return {
                "recommendation": "FINETUNE_OR_RAG",
                "reasoning": "Either approach viable; RAG faster to implement",
                "analysis": analysis
            }
        else:
            return {
                "recommendation": "PROMPTING",
                "reasoning": "Prompting sufficient for this use case",
                "analysis": analysis
            }

    @staticmethod
    def cost_per_api_call(model: str) -> float:
        """Estimate cost per API call"""
        costs = {
            "gpt-4": 0.03 / 1000,  # Avg token cost
            "gpt-3.5-turbo": 0.001 / 1000,
            "fine-tuned-gpt-3.5": 0.0015 / 1000
        }
        return costs.get(model, 0)
```

**Pre-Fine-Tuning Checklist**:
```yaml
checklist:
  data_availability:
    - "Labeled training examples available: >= 100" ✓
    - "High-quality labels (human verified or gold standard)" ✓
    - "Representative of production data distribution" ✓

  performance_analysis:
    - "Baseline prompt accuracy measured" ✓
    - "Target accuracy >= baseline + 5%" ✓
    - "Performance gap justifiable (time/cost)" ✓

  cost_analysis:
    - "Training cost estimated" ✓
    - "Monthly savings calculated" ✓
    - "ROI > 6 months" ✓

  technical_feasibility:
    - "Training data in correct format" ✓
    - "GPU/compute resources available" ✓
    - "Model framework compatible with use case" ✓

  if_all_checked: "Proceed to dataset preparation"
  if_any_unchecked: "Address gaps or choose alternative (prompting/RAG)"
```

### Step 2: Dataset Preparation and Preprocessing
Prepare high-quality training data in correct format.

**Data Format and Validation**:
```python
class DatasetPreparation:
    """
    Prepare training data for fine-tuning
    Format depends on platform (OpenAI, HuggingFace, etc.)
    """

    @staticmethod
    def prepare_openai_format(examples: list[dict]) -> list[dict]:
        """
        OpenAI fine-tuning format
        """
        formatted = []

        for example in examples:
            formatted_example = {
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": example["input"]},
                    {"role": "assistant", "content": example["output"]}
                ]
            }
            formatted.append(formatted_example)

        return formatted

    @staticmethod
    def validate_dataset(examples: list[dict]) -> tuple[bool, list[str]]:
        """
        Check data quality before training
        """
        errors = []

        for i, example in enumerate(examples):
            # Check required fields
            if "input" not in example:
                errors.append(f"Example {i}: Missing 'input' field")
            if "output" not in example:
                errors.append(f"Example {i}: Missing 'output' field")

            # Check field lengths
            if len(example.get("input", "")) < 5:
                errors.append(f"Example {i}: Input too short (< 5 chars)")
            if len(example.get("output", "")) < 1:
                errors.append(f"Example {i}: Output empty")

            # Check for duplicates
            if i > 0:
                prev = examples[i-1]
                if example.get("input") == prev.get("input"):
                    errors.append(f"Example {i}: Duplicate input to {i-1}")

            # Check token count
            input_tokens = len(example.get("input", "").split())
            if input_tokens > 4000:
                errors.append(f"Example {i}: Input too long ({input_tokens} tokens)")

        return len(errors) == 0, errors

    @staticmethod
    def split_train_val_test(examples: list[dict],
                            train_ratio: float = 0.8,
                            val_ratio: float = 0.1) -> tuple[list, list, list]:
        """
        Split dataset ensuring no leakage
        """
        import random
        random.shuffle(examples)

        train_size = int(len(examples) * train_ratio)
        val_size = int(len(examples) * val_ratio)

        train = examples[:train_size]
        val = examples[train_size:train_size + val_size]
        test = examples[train_size + val_size:]

        return train, val, test

    @staticmethod
    def detect_imbalance(examples: list[dict], label_field: str = "label") -> dict:
        """
        Check for class imbalance in dataset
        """
        label_counts = {}

        for example in examples:
            label = example.get(label_field)
            label_counts[label] = label_counts.get(label, 0) + 1

        total = len(examples)
        distribution = {k: v/total for k, v in label_counts.items()}

        max_ratio = max(distribution.values())
        min_ratio = min(distribution.values())
        imbalance = max_ratio / min_ratio if min_ratio > 0 else float('inf')

        return {
            "label_counts": label_counts,
            "distribution": distribution,
            "imbalance_ratio": imbalance,
            "is_balanced": imbalance < 3  # Acceptable range
        }

# Data quality example:
examples = [
    {"input": "What is machine learning?", "output": "ML is a subset of AI..."},
    {"input": "Explain neural networks", "output": "Neural networks are..."},
    # ... 50+ more examples
]

is_valid, errors = DatasetPreparation.validate_dataset(examples)
if is_valid:
    train, val, test = DatasetPreparation.split_train_val_test(examples)
    print(f"Dataset ready: {len(train)} train, {len(val)} val, {len(test)} test")
else:
    print(f"Data issues: {errors}")
```

**Deduplication and Cleaning**:
```python
class DatasetCleaning:
    """Remove duplicates, fix encoding issues, normalize text"""

    @staticmethod
    def remove_duplicates(examples: list[dict]) -> list[dict]:
        """
        Remove exact and near-duplicate examples
        Keep first occurrence
        """
        seen_inputs = set()
        unique_examples = []

        for example in examples:
            input_text = example.get("input", "").lower().strip()

            # Exact duplicate
            if input_text in seen_inputs:
                continue

            # Near-duplicate (very similar inputs)
            is_duplicate = any(
                similarity(input_text, seen) > 0.95
                for seen in seen_inputs
            )
            if is_duplicate:
                continue

            seen_inputs.add(input_text)
            unique_examples.append(example)

        removed = len(examples) - len(unique_examples)
        print(f"Removed {removed} duplicates")
        return unique_examples

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for consistency"""
        # Remove extra whitespace
        text = " ".join(text.split())

        # Fix common encoding issues
        text = text.replace("â€™", "'")  # Smart quote
        text = text.replace("â€œ", '"')
        text = text.replace("â€\x9d", '"')

        return text
```

### Step 3: Base Model Selection
Choose the right foundation model for fine-tuning.

**Model Comparison Matrix**:
```yaml
models:
  gpt-3.5-turbo:
    size: "20B parameters"
    cost_per_1m_tokens: "$0.50 (input), $1.50 (output)"
    finetune_cost: "$3 per 1M tokens"
    inference_latency: "1-2 seconds"
    strengths:
      - "General purpose, good at diverse tasks"
      - "Cheap to fine-tune and use"
      - "Fast inference"
    weaknesses:
      - "Less powerful than GPT-4"
      - "Smaller context window"
    best_for:
      - "Cost-sensitive applications"
      - "High-volume inference"
      - "Well-established tasks"

  gpt-4:
    size: "Unknown (larger than 3.5)"
    cost_per_1m_tokens: "$30 (input), $60 (output)"
    finetune_cost: "Not available as of Jan 2024"
    inference_latency: "5-10 seconds"
    strengths:
      - "Best in class performance"
      - "Longer context window"
      - "Better reasoning"
    weaknesses:
      - "Very expensive"
      - "Slow inference"
    best_for:
      - "Complex reasoning tasks"
      - "High-quality is critical"
      - "Budget not primary constraint"

  llama-2-7b:
    size: "7 billion parameters"
    cost: "$0 (open source, self-hosted)"
    inference_latency: "100-500ms on GPU"
    strengths:
      - "Free, fully open source"
      - "Can be deployed on-device"
      - "Fine-tune on consumer GPU"
    weaknesses:
      - "Lower quality than GPT-3.5"
      - "Requires infrastructure"
      - "No API support"
    best_for:
      - "Cost-critical, high-volume"
      - "On-device deployment"
      - "Privacy-sensitive applications"

  mistral-7b:
    size: "7 billion parameters"
    cost: "$0.10 per 1M input tokens (Mistral API)"
    inference_latency: "200-400ms"
    strengths:
      - "Good quality at low cost"
      - "Small enough for fine-tuning"
      - "Open weights available"
    best_for:
      - "Budget-friendly with reasonable quality"
      - "Custom fine-tuning required"
```

**Base Model Selection Decision Tree**:
```
Budget Available?
├─ < $100/month → Llama-2 or Mistral (open source)
├─ $100-$1000/month → GPT-3.5-turbo
└─ > $1000/month → GPT-4 possible

Performance Requirements?
├─ "Good enough" (> 85% accuracy) → GPT-3.5
├─ "Very good" (> 90%) → GPT-4
└─ "Excellent" (> 95%) → GPT-4 + larger model

Inference Speed?
├─ Real-time (< 1 sec) → Llama-2, Mistral
├─ Few seconds (1-5 sec) → GPT-3.5
└─ Can wait (> 5 sec) → GPT-4

Recommendation Path:
Cost-sensitive + Speed critical
  └─ Llama-2-7B (self-hosted) or Mistral
Quality-critical + Budget available
  └─ GPT-4
Balanced
  └─ GPT-3.5-turbo fine-tuned
```

### Step 4: Hyperparameter Configuration
Set learning rate, epochs, batch size, and other training parameters.

**Hyperparameter Defaults** (starting point):
```python
class HyperparameterConfig:
    """
    Recommended hyperparameters for fine-tuning
    Adjust based on dataset size and performance
    """

    # For small dataset (100-500 examples)
    SMALL_DATASET = {
        "learning_rate": 2e-5,  # Lower learning rate = safer
        "batch_size": 8,
        "num_epochs": 3,  # More epochs with small data
        "warmup_steps": 50,
        "weight_decay": 0.01,
        "gradient_accumulation": 1
    }

    # For medium dataset (500-5000 examples)
    MEDIUM_DATASET = {
        "learning_rate": 2e-5,
        "batch_size": 16,
        "num_epochs": 2,
        "warmup_steps": 100,
        "weight_decay": 0.01,
        "gradient_accumulation": 2
    }

    # For large dataset (5000+ examples)
    LARGE_DATASET = {
        "learning_rate": 5e-5,
        "batch_size": 32,
        "num_epochs": 1,
        "warmup_steps": 200,
        "weight_decay": 0.01,
        "gradient_accumulation": 1
    }

    # Max token limits
    MAX_TOKENS = {
        "input": 512,  # Max input length
        "output": 256,  # Max output length
        "total": 768
    }
```

**Hyperparameter Tuning Strategy**:
```python
class HyperparameterTuning:
    """
    Systematically explore hyperparameters
    """

    async def grid_search(self, train_data: list[dict],
                         val_data: list[dict],
                         param_grid: dict) -> dict:
        """
        Grid search over hyperparameters
        Evaluate each combination on validation set
        """

        best_result = None
        best_val_accuracy = 0

        for learning_rate in param_grid["learning_rates"]:
            for batch_size in param_grid["batch_sizes"]:
                for num_epochs in param_grid["num_epochs_list"]:
                    config = {
                        "learning_rate": learning_rate,
                        "batch_size": batch_size,
                        "num_epochs": num_epochs,
                        # Other params fixed
                    }

                    # Train model with this config
                    model = await self.train(train_data, config)

                    # Evaluate on validation set
                    val_accuracy = await self.evaluate(model, val_data)

                    print(f"LR={learning_rate}, BS={batch_size}, Epochs={num_epochs}: Accuracy={val_accuracy:.3f}")

                    if val_accuracy > best_val_accuracy:
                        best_val_accuracy = val_accuracy
                        best_result = {
                            "config": config,
                            "val_accuracy": val_accuracy,
                            "model": model
                        }

        return best_result

    # Example usage:
    param_grid = {
        "learning_rates": [1e-5, 2e-5, 5e-5],
        "batch_sizes": [8, 16, 32],
        "num_epochs_list": [1, 2, 3]
    }
    best = await HyperparameterTuning().grid_search(train, val, param_grid)
    print(f"Best config: LR={best['config']['learning_rate']}, Accuracy={best['val_accuracy']:.3f}")
```

### Step 5: Training Monitoring and Early Stopping
Watch for overfitting and stop training when validation plateaus.

**Training Metrics to Track**:
```python
class TrainingMonitor:
    """
    Monitor training progress, detect overfitting
    """

    def __init__(self, patience: int = 3):
        self.train_losses = []
        self.val_losses = []
        self.val_accuracies = []
        self.patience = patience
        self.best_val_loss = float('inf')
        self.patience_counter = 0

    async def on_epoch_end(self, epoch: int, train_loss: float,
                          val_loss: float, val_accuracy: float):
        """Called after each epoch"""

        self.train_losses.append(train_loss)
        self.val_losses.append(val_loss)
        self.val_accuracies.append(val_accuracy)

        print(f"Epoch {epoch+1}: Train Loss={train_loss:.4f}, "
              f"Val Loss={val_loss:.4f}, Val Accuracy={val_accuracy:.3f}")

        # Early stopping check
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            self.patience_counter = 0
            print(f"  ✓ New best validation loss!")
            return {"status": "continue"}
        else:
            self.patience_counter += 1
            if self.patience_counter >= self.patience:
                print(f"  ⚠️  Validation loss not improving for {self.patience} epochs")
                return {"status": "stop", "reason": "early_stopping"}

        # Check for overfitting
        if epoch >= 2:
            train_trend = self.train_losses[-1] < self.train_losses[-2]
            val_trend = self.val_losses[-1] < self.val_losses[-2]

            if train_trend and not val_trend:
                print(f"  ⚠️  Possible overfitting (train loss decreasing, val loss increasing)")

        return {"status": "continue"}

    def plot_training_curves(self):
        """Visualize training progress"""
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        # Loss curves
        ax1.plot(self.train_losses, label="Train Loss")
        ax1.plot(self.val_losses, label="Val Loss")
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Loss")
        ax1.legend()
        ax1.set_title("Training Curves")

        # Accuracy curve
        ax2.plot(self.val_accuracies, label="Val Accuracy")
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Accuracy")
        ax2.legend()
        ax2.set_title("Validation Accuracy")

        plt.tight_layout()
        plt.show()
```

### Step 6: Evaluation on Held-Out Test Set
Final quality assessment before deployment.

**Evaluation Metrics**:
```python
class FinetunedModelEvaluation:
    """
    Evaluate fine-tuned model vs baseline
    """

    async def evaluate(self, model, test_set: list[dict]) -> dict:
        """
        Comprehensive evaluation
        """
        predictions = []
        references = []

        for example in test_set:
            pred = await model.predict(example["input"])
            predictions.append(pred)
            references.append(example["output"])

        # Metrics
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
        from evaluate import load

        accuracy = accuracy_score(references, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            references, predictions, average="weighted"
        )

        # BLEU score (for text generation)
        bleu = load("bleu")
        bleu_score = bleu.compute(predictions=predictions, references=[[ref] for ref in references])

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "bleu": bleu_score["bleu"]
        }

    async def compare_with_baseline(self, finetuned_model, baseline_prompt) -> dict:
        """
        Compare fine-tuned model vs prompting baseline
        """
        test_set = self.load_test_set()

        # Evaluate fine-tuned model
        ft_results = await self.evaluate(finetuned_model, test_set)

        # Evaluate baseline
        baseline_results = {"accuracy": 0.75}  # From earlier measurement

        # Compare
        improvement = ft_results["accuracy"] - baseline_results["accuracy"]
        improvement_pct = (improvement / baseline_results["accuracy"]) * 100

        return {
            "finetuned_accuracy": ft_results["accuracy"],
            "baseline_accuracy": baseline_results["accuracy"],
            "improvement_absolute": improvement,
            "improvement_percent": improvement_pct,
            "winner": "finetuned" if ft_results["accuracy"] > baseline_results["accuracy"] else "baseline"
        }
```

### Step 7: A/B Testing and Safe Deployment
Roll out fine-tuned model gradually with monitoring.

**Canary Deployment**:
```python
class SafeDeployment:
    """
    Deploy fine-tuned model gradually
    Measure quality before full rollout
    """

    async def run_canary_deployment(self, model_a_baseline, model_b_finetuned,
                                   production_traffic: int = 10000) -> dict:
        """
        Canary deployment strategy:
        - Week 1: 10% traffic to new model, 90% to baseline
        - If quality OK, increase to 25%
        - If quality OK, increase to 50%
        - If quality OK, full rollout to 100%

        Metrics to watch: Accuracy, latency, errors
        """

        canary_stages = [
            {"traffic_percentage": 10, "days": 1},
            {"traffic_percentage": 25, "days": 3},
            {"traffic_percentage": 50, "days": 7},
            {"traffic_percentage": 100, "days": 0}  # Full rollout
        ]

        for stage in canary_stages:
            traffic_pct = stage["traffic_percentage"]
            duration = stage["days"]

            print(f"\nCanary Stage: {traffic_pct}% traffic for {duration} days")

            # Route traffic
            traffic_b = int(production_traffic * traffic_pct / 100)
            traffic_a = production_traffic - traffic_b

            # Monitor results
            results_a = await self.monitor_traffic(model_a_baseline, traffic_a, duration)
            results_b = await self.monitor_traffic(model_b_finetuned, traffic_b, duration)

            # Compare
            accuracy_a = results_a["accuracy"]
            accuracy_b = results_b["accuracy"]

            print(f"Baseline accuracy: {accuracy_a:.3f}")
            print(f"Finetuned accuracy: {accuracy_b:.3f}")

            if accuracy_b < accuracy_a - 0.02:  # > 2% regression
                print(f"⚠️  Quality regression detected! Rolling back...")
                return {
                    "status": "rollback",
                    "reason": "quality_regression",
                    "accuracy_drop": accuracy_a - accuracy_b
                }

            # Latency check
            if results_b["latency_p99"] > results_a["latency_p99"] * 2:
                print(f"⚠️  Latency too high! Rolling back...")
                return {"status": "rollback", "reason": "high_latency"}

            # Quality OK, continue to next stage
            if accuracy_b >= accuracy_a - 0.01:
                print(f"✓ Quality acceptable, proceeding to next stage")
            else:
                print(f"Quality borderline but acceptable")

        return {"status": "success", "new_model_active": True}
```

### Step 8: Cost Estimation
Calculate training and inference costs.

**Cost Breakdown**:
```python
class CostEstimation:
    """
    Estimate fine-tuning and inference costs
    """

    @staticmethod
    def estimate_training_cost(num_training_examples: int, model: str = "gpt-3.5-turbo") -> dict:
        """
        Training cost based on examples and model

        OpenAI pricing (as of Jan 2024):
        - GPT-3.5-turbo: $3 per 1M input tokens, $6 per 1M output tokens
        """

        # Estimate tokens
        avg_input_tokens = 200
        avg_output_tokens = 50
        num_epochs = 2

        total_input_tokens = num_training_examples * avg_input_tokens * num_epochs
        total_output_tokens = num_training_examples * avg_output_tokens * num_epochs

        # Calculate cost
        input_cost = (total_input_tokens / 1e6) * 3.0  # $3 per 1M input tokens
        output_cost = (total_output_tokens / 1e6) * 6.0  # $6 per 1M output tokens

        return {
            "training_cost": input_cost + output_cost,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "breakdown": {
                "input_cost": input_cost,
                "output_cost": output_cost
            }
        }

    @staticmethod
    def estimate_inference_cost(monthly_volume: int,
                               avg_input_tokens: int = 200,
                               avg_output_tokens: int = 50,
                               model: str = "gpt-3.5-turbo") -> dict:
        """
        Inference cost for using fine-tuned model

        Fine-tuned models are 3x cheaper than base models
        """

        # Cost per token
        if model == "gpt-3.5-turbo":
            input_cost_per_1m = 0.50  # Fine-tuned is $0.50 per 1M (vs $3 base)
            output_cost_per_1m = 1.50  # Fine-tuned is $1.50 per 1M (vs $6 base)

        monthly_input_tokens = monthly_volume * avg_input_tokens
        monthly_output_tokens = monthly_volume * avg_output_tokens

        monthly_input_cost = (monthly_input_tokens / 1e6) * input_cost_per_1m
        monthly_output_cost = (monthly_output_tokens / 1e6) * output_cost_per_1m

        return {
            "monthly_cost": monthly_input_cost + monthly_output_cost,
            "cost_per_request": (monthly_input_cost + monthly_output_cost) / monthly_volume,
            "monthly_input_tokens": monthly_input_tokens,
            "monthly_output_tokens": monthly_output_tokens,
            "breakdown": {
                "input_cost": monthly_input_cost,
                "output_cost": monthly_output_cost
            }
        }

    @staticmethod
    def roi_analysis(training_cost: float, monthly_savings: float) -> dict:
        """
        Calculate ROI and payback period
        """
        payback_months = training_cost / monthly_savings if monthly_savings > 0 else float('inf')
        yearly_roi = (monthly_savings * 12 - training_cost) / training_cost * 100

        return {
            "training_cost": training_cost,
            "monthly_savings": monthly_savings,
            "payback_months": payback_months,
            "yearly_roi": yearly_roi,
            "is_profitable": payback_months < 12
        }
```

## Output Template

**Fine-Tuning Report**:
```markdown
# [Task Name] Fine-Tuning Report

## Use Case Validation
[Decision rationale, cost-benefit analysis]

## Dataset Summary
- Training: X examples
- Validation: X examples
- Test: X examples
- Distribution: [label distribution]

## Base Model Selection
[Chosen model, rationale, alternatives considered]

## Hyperparameters
[Final config with tuning methodology]

## Training Results
[Loss curves, training time, resource usage]

## Evaluation Results
[Accuracy, precision, recall, F1, comparison to baseline]

## Deployment Plan
[Canary stages, rollback criteria, monitoring]

## Cost Analysis
[Training cost, inference cost, ROI]
```

## Quality Gates

1. **Test Set Performance**: Accuracy >= target threshold
2. **No Regression vs Baseline**: New model >= baseline - 1%
3. **Training Curves Healthy**: No overfitting signals
4. **Evaluation Reproducible**: Results consistent across runs
5. **Cost Justifiable**: ROI positive within 12 months
6. **Safe Deployment Possible**: Model can be canary deployed
7. **Documentation Complete**: All decisions documented

## Examples

### Good Fine-Tuning: Customer Intent Classification
```
Baseline (prompting): 78% accuracy
Target: 90% accuracy

Data: 2000 labeled customer queries
Model: GPT-3.5-turbo
Learning rate: 2e-5
Epochs: 2

Results:
- Fine-tuned accuracy: 92% ✓ (exceeds target)
- No regression vs baseline ✓
- Training time: 30 minutes
- Cost: $45 (training) + $50/month (inference)
- ROI: 1 month ✓

Deployment: Canary 10% → 25% → 50% → 100% over 2 weeks
```

## Common Mistakes

1. **Training on Validation Data**
   - ❌ Use same split for training and validation
   - ✓ Separate 80/10/10 train/val/test before starting

2. **Too High Learning Rate / Overfitting**
   - ❌ Learning rate 1e-3 (causes divergence)
   - ✓ Start with 2e-5 for fine-tuning; adjust down if needed

3. **No Early Stopping / Wasted Epochs**
   - ❌ Train for 10 epochs regardless of val loss
   - ✓ Monitor validation loss, stop when plateaus

4. **Incomplete Evaluation**
   - ❌ Only check accuracy; ignore latency, cost
   - ✓ Compare baseline, fine-tuned, cost per request

## Anti-Patterns

1. **Fine-Tuning Without Use Case Validation**
   - ❌ Fine-tune because "more training = better"
   - ✓ Establish baseline first; prove improvement needed

2. **Massive Dataset Not Needed**
   - ❌ Use 50,000 examples (expensive, diminishing returns)
   - ✓ Start with 500-1000 examples; validate ROI

3. **Full Rollout Without Canary**
   - ❌ Deploy to 100% users immediately
   - ✓ Canary 10% first; monitor quality
