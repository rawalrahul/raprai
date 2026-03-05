---
name: data-cleaner
description: "Implement systematic data cleaning pipelines with missing value imputation, duplicate removal, type coercion, outlier detection, and normalization. Produces clean dataset and audit report."
category: data
difficulty: intermediate
model_boost: "Weak model struggles with incomplete/inconsistent raw data"
---

# Data Cleaner

## Purpose
Data quality directly impacts analysis validity and model performance. This skill systematizes the data cleaning process through documented pipelines that handle missing values, duplicates, type inconsistencies, outliers, and normalization in a reproducible, auditable manner. The output includes both the cleaned dataset and a comprehensive cleaning report tracking all transformations.

## When to Use
- Preparing raw data for analysis or modeling
- Standardizing data ingestion processes
- Ensuring data quality compliance
- Creating reproducible ETL workflows
- **Do NOT use when**: Data is already validated or cleaning requirements are undefined

## Instructions

### Step 1: Profile Source Data
Before cleaning, establish baseline metrics to track improvements:
- Record original row count, column count, data types
- Identify null patterns (missing completely at random vs. systematic)
- Calculate completeness percentage per column
- Document data quality issues discovered
- Example: "Original: 50K rows, 23 columns, 18% missing values across dataset"

### Step 2: Handle Missing Values
Missing data requires context-specific strategies:

**Deletion (only if < 5% missing)**
```python
# Remove rows where critical columns are null
df_clean = df.dropna(subset=['user_id', 'amount'])
# Remove columns with > 80% missing
df_clean = df.dropna(thresh=len(df)*0.2, axis=1)
```

**Imputation methods:**
- **Mean/Median**: Numeric columns without strong business logic (e.g., temperature)
- **Forward/Backward fill**: Time-series data with temporal continuity
- **Domain value**: Use business context (e.g., missing category = "Other")
- **Predictive imputation**: Train model on complete cases to predict missing values

```python
# Mean imputation for numeric
df['age'].fillna(df['age'].mean(), inplace=True)
# Mode imputation for categorical
df['country'].fillna(df['country'].mode()[0], inplace=True)
# Domain logic
df['payment_method'].fillna('unknown', inplace=True)
```

Document which columns use which strategy and why.

### Step 3: Remove Duplicate Records
Duplicates can inflate metrics and skew analysis:

**Exact duplicates** (identical across all columns):
```python
df_clean = df.drop_duplicates()
# Log: Removed 247 exact duplicates
```

**Fuzzy duplicates** (same entity, slight variations):
```python
# Remove duplicates on key identifier, keep first occurrence
df_clean = df.drop_duplicates(subset=['customer_id'], keep='first')
# For name variations, use fuzzy matching
from fuzzywuzzy import process
# Identify potential duplicates for manual review
```

**Rules-based deduplication:**
- Keep most recent record for repeat transactions
- Prioritize complete records (more non-null values)
- Resolve by timestamp when applicable

### Step 4: Type Coercion and Standardization
Ensure consistent data types and formats:

```python
# Numeric conversion
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
# Handle currency strings: "$1,234.56" → 1234.56
df['price'] = df['price'].str.replace('$', '').str.replace(',', '').astype(float)

# Date standardization (handles multiple formats)
df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True, errors='coerce')

# Categorical standardization
df['status'] = df['status'].str.lower().str.strip()
# Map variations to canonical values
status_map = {'completed': 'completed', 'done': 'completed', 'finished': 'completed'}
df['status'] = df['status'].map(status_map)

# Boolean consistency
df['is_active'] = df['is_active'].astype(bool)
```

Track columns with conversion failures (rows coerced to null).

### Step 5: Outlier Detection and Treatment
Outliers are valid data but require explicit handling:

**Statistical methods:**

```python
# Z-score method (assumes normal distribution)
from scipy import stats
z_scores = np.abs(stats.zscore(df['amount']))
df_no_outliers = df[z_scores < 3]  # Remove extreme outliers

# IQR method (robust, distribution-free)
Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR
df_clean = df[(df['amount'] >= lower_bound) & (df['amount'] <= upper_bound)]

# Isolation Forest (detects multivariate outliers)
from sklearn.ensemble import IsolationForest
iso_forest = IsolationForest(contamination=0.05)
outliers = iso_forest.fit_predict(df[numeric_cols]) == -1
```

**Treatment options:**
- **Flag and retain**: Add outlier_flag column, keep records for transparency
- **Cap/Floor**: Set to 95th/5th percentile (domain-appropriate)
- **Remove**: Only if confirmed erroneous or insufficient business relevance

### Step 6: Normalization and Scaling
Prepare data for analysis or modeling:

```python
# Min-Max scaling (0-1 range)
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
df['amount_scaled'] = scaler.fit_transform(df[['amount']])

# Standardization (mean=0, std=1, Z-score)
df['amount_std'] = (df['amount'] - df['amount'].mean()) / df['amount'].std()

# Log transformation (right-skewed distributions)
df['log_amount'] = np.log1p(df['amount'])  # log1p handles zeros

# Categorical encoding
# One-hot encoding
df_encoded = pd.get_dummies(df['category'], prefix='category')
# Label encoding (ordinal categories)
df['priority_encoded'] = df['priority'].map({'low': 1, 'medium': 2, 'high': 3})
```

Specify which columns require which scaling approach and store scaling parameters for production consistency.

### Step 7: Validation and Quality Assurance
Implement data quality gates before output:

```python
# Validate cleaned data
assert df_clean.isnull().sum().sum() == 0, "Null values remain"
assert len(df_clean) > 0, "No data remaining"
assert df_clean['amount'].dtype in [np.float64, np.float32], "Wrong type"
assert (df_clean['amount'] >= 0).all(), "Invalid negative amounts"
```

Run automated checks and document any violations.

## Output Template

**Cleaned Dataset**: CSV or Parquet with all transformations applied

**Cleaning Report** (structured markdown):
```
# Data Cleaning Report
Date: 2026-03-05
Source: raw_transactions.csv

## Summary Statistics
- Original records: 50,000
- Cleaned records: 48,932 (97.9% retention)
- Rows removed: 1,068 (duplicates: 247, invalid dates: 521, outliers: 300)

## Column-by-Column Actions
| Column | Type | Missing | Strategy | Notes |
|--------|------|---------|----------|-------|
| user_id | int | 0 | None | Valid primary key |
| amount | float | 12 | Mean imputation | 3 extreme outliers capped at 95th percentile |
| date | date | 45 | Removed | Insufficient temporal data |
| category | string | 0 | Mode fill | Unknown mapped to "Other" (23 values) |

## Data Quality Metrics
- Completeness: 95.2% (before: 82.1%)
- Uniqueness: 97.8% (after duplicate removal)
- Validity: 100% (type coercion successful)
- Consistency: Standardized formats applied

## Transformations Applied
1. Removed 247 exact duplicates on (user_id, date)
2. Imputed 12 missing amounts with column median ($145.67)
3. Converted 50K amounts from string to float
4. Identified and capped 300 outliers > $50K to 95th percentile
5. Standardized category names to lowercase
```

## Quality Gates

1. **Null completeness**: Maximum 5% missing values (unless documented exception)
2. **Duplicate rate**: < 1% after deduplication
3. **Type consistency**: 100% successful type coercion (no silent nulls from failed conversion)
4. **Outlier documentation**: All outlier removals/modifications logged with rationale
5. **Audit trail**: Complete record of every transformation with row counts before/after
6. **Data retention**: Minimum 80% of original records (alert if > 20% removed)

## Examples

**Good: Structured cleaning with documentation**
```
Input: 10K customer records with 35% nulls, mixed date formats, currency with symbols
Process:
- Missing: Email (15%) dropped, address (8%) mode-filled to "not_provided"
- Duplicates: 147 removed on customer_id (kept most recent)
- Types: Amounts converted, dates standardized to ISO 8601
- Outliers: 3 orders >$500K flagged (kept but marked for review)
Output: 9,820 clean records (98.2% retention), detailed audit log
```

**Bad: Opaque cleaning with data loss**
```
Input: 50K records
Action: "Cleaned data"
Output: 35K records (30% loss)
Issue: No documentation of removals, rationale unknown, unreproducible
```

## Common Mistakes

1. **Silent data loss**: Removing outliers without flagging or documenting why; analyst assumes all data is valid
2. **Inappropriate imputation**: Using mean for highly skewed data or categorical columns; biases downstream analysis
3. **Type coercion failures**: Converting dates with varied formats without error handling; results in silent nulls
4. **Ignoring missing data patterns**: Treating MCAR (missing completely at random) same as MNAR (missing not at random); bias introduced
5. **Over-aggressive deduplication**: Removing legitimate duplicate transactions; underreports actual business metrics
6. **No scaling consistency**: Fitting scalers on training data then using different parameters in production; model degradation

## Anti-Patterns

1. **"Clean all nulls first"**: Context matters—some nulls are informative (e.g., "no phone number" vs. data entry error)
2. **Removing outliers without investigation**: Real business events (flash sales, high-value customers) are often outliers
3. **Manual one-off scripts**: Building new cleaning logic for each dataset; inconsistent, non-reproducible, brittle
4. **No cleaning metadata**: Discarding scaling parameters, imputation values, or outlier thresholds; prevents production consistency
5. **Cleaning in final analysis code**: Quality issues embedded in jupyter notebooks; difficult to version control or reuse