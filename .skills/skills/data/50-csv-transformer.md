---
name: csv-transformer
description: "Parse, validate, transform, and reshape CSVs at scale. Handle encoding, delimiter detection, header cleanup, pivot/unpivot operations, and data aggregation."
category: data
difficulty: intermediate
model_boost: "Weak model struggles with malformed CSVs or data transformation operations"
---

# CSV Transformer

## Purpose
CSVs are ubiquitous in data work but notoriously messy—encodings vary, delimiters differ, headers contain special characters. This skill systematizes CSV handling from detection and parsing through transformation and validation. The output is a clean, properly-structured dataset ready for analysis.

## When to Use
- Ingesting CSV files from external sources or exports
- Cleaning datasets received from non-technical users
- Reshaping data for analytics (pivot, unpivot, aggregations)
- Merging multiple CSV sources
- **Do NOT use when**: Streaming data (use ETL pipelines), or data already in database

## Instructions

### Step 1: Detect Encoding and Delimiter
Diagnose CSV structure before parsing:

**Encoding detection:**

```python
import chardet
import pandas as pd

# Detect file encoding
def detect_encoding(file_path, sample_size=10000):
    """
    Determine encoding by sampling file bytes.
    Handles: UTF-8, ISO-8859-1, Windows-1252, etc.
    """
    with open(file_path, 'rb') as f:
        raw = f.read(sample_size)

    result = chardet.detect(raw)
    encoding = result['encoding']
    confidence = result['confidence']

    print(f"Detected encoding: {encoding} (confidence: {confidence:.1%})")

    # If confidence < 70%, try common encodings
    if confidence < 0.7:
        return try_encodings(file_path, ['utf-8', 'iso-8859-1', 'windows-1252'])
    return encoding

# COMMON ENCODINGS:
# UTF-8: Unicode standard, safe default for new data
# ISO-8859-1 (Latin-1): Western European, older systems
# Windows-1252: Microsoft encoding, common in Excel exports
# GB2312/GBK: Chinese characters
# Shift-JIS: Japanese characters

# ENCODING ERRORS:
# When reading with wrong encoding:
# ├─ Mojibake: Garbled characters (é becomes é¡)
# ├─ UnicodeDecodeError: Python raises error (better than silent corruption)
# └─ Fix: Try alternative encodings until one succeeds

df = pd.read_csv('data.csv', encoding='iso-8859-1', on_error='coerce')
```

**Delimiter detection:**

```python
import csv
from io import TextIOWrapper

def detect_delimiter(file_path, encoding, sample_lines=5):
    """
    Test common delimiters against sample of file.
    Returns most likely delimiter.
    """
    with open(file_path, 'r', encoding=encoding) as f:
        sample = [f.readline() for _ in range(sample_lines)]

    delimiters_to_test = [',', ';', '\t', '|', ':']

    for delim in delimiters_to_test:
        # Count fields per line (should be consistent)
        field_counts = [len(line.split(delim)) for line in sample]

        if len(set(field_counts)) == 1:  # Consistent count
            return delim, field_counts[0]

    # Fallback: Use CSV Sniffer (infers from structure)
    with open(file_path, 'r', encoding=encoding) as f:
        dialect = csv.Sniffer().sniff(f.read(1024))
    return dialect.delimiter

# COMMON DELIMITERS:
# , (comma): Most common, CSV standard
# ; (semicolon): European Excel exports (locale-dependent)
# \t (tab): Tab-separated values (TSV)
# | (pipe): Legacy systems, unambiguous
# Space: Rare, ambiguous (splits on any whitespace)

# DETECTION TIPS:
# └─ Look for consistent column count across lines
# └─ Avoid space as delimiter (natural language contains spaces)
# └─ If delimiter in data, must be quoted: "Smith, Jr.",350
```

### Step 2: Parse CSV with Error Handling
Read file robustly, handling malformed rows:

```python
import pandas as pd
import numpy as np

# BASIC LOADING (with error handling)
def load_csv_safe(file_path, encoding='utf-8', delimiter=','):
    """
    Load CSV with graceful error handling.
    Returns data + quality report.
    """
    try:
        # Attempt normal read
        df = pd.read_csv(
            file_path,
            encoding=encoding,
            delimiter=delimiter,
            dtype=str,  # Read all as strings initially (safer)
            on_bad_lines='skip',  # Skip unparseable rows
            engine='python'  # Slower but handles edge cases
        )

        # Report what was skipped
        print(f"Loaded: {len(df)} rows, {len(df.columns)} columns")
        return df

    except UnicodeDecodeError:
        # Encoding error detected
        print(f"Failed with {encoding}, trying alternatives...")
        for alt_encoding in ['iso-8859-1', 'windows-1252', 'latin1']:
            try:
                df = pd.read_csv(file_path, encoding=alt_encoding, delimiter=delimiter, on_bad_lines='skip')
                print(f"Success with {alt_encoding}")
                return df
            except:
                continue
        raise ValueError("Could not decode file with any standard encoding")

# ADVANCED PARSING (fixing specific issues)
def load_csv_advanced(file_path):
    """
    Handle specific issues: quoted fields, escaped quotes, etc.
    """
    df = pd.read_csv(
        file_path,
        encoding='utf-8',
        delimiter=',',
        quotechar='"',  # Character indicating quoted fields
        escapechar='\\',  # Character escaping quotes within fields
        skipinitialspace=True,  # Remove leading whitespace after delimiter
        na_values=['NA', 'N/A', 'null', ''],  # Treat as missing
        skip_blank_lines=True,
        dtype=str  # Read as strings first
    )
    return df

# EXAMPLE ISSUES HANDLED:

# Issue: Quoted fields containing delimiters
# Raw: "Smith, Inc.",500
# Parsed correctly: Smith, Inc. | 500

# Issue: Quoted fields containing quotes (escaped)
# Raw: "Mr. ""Bob"" Smith",500
# Parsed correctly: Mr. "Bob" Smith | 500

# Issue: Inconsistent line endings (Windows \r\n vs. Unix \n)
# Pandas handles automatically

# Issue: BOM (Byte Order Mark) at file start
# Add: encoding='utf-8-sig' to strip BOM
```

### Step 3: Validate and Clean Headers
Fix common header issues:

```python
def clean_headers(df):
    """
    Standardize column names for analysis.
    """
    df.columns = (
        df.columns
        .str.strip()  # Remove leading/trailing whitespace
        .str.lower()  # Lowercase (avoid case mismatches)
        .str.replace(' ', '_')  # Replace spaces with underscores
        .str.replace(r'[^\w_]', '', regex=True)  # Remove special chars
        .str.replace(r'_+', '_', regex=True)  # Collapse multiple underscores
    )

    # Handle duplicates (e.g., two "name" columns)
    duplicates = df.columns[df.columns.duplicated()].unique()
    if len(duplicates) > 0:
        print(f"WARNING: Duplicate column names: {duplicates}")
        # Add suffix to duplicates: name, name_2, name_3
        df.columns = pd.Series(df.columns).mask(
            df.columns.duplicated(keep=False),
            df.columns.astype(str) + '_dup'
        )

    return df

# EXAMPLES:
# "Customer Name" → customer_name
# "Order $Amount" → order_amount
# "Date (YYYY-MM-DD)" → date_yyyy_mm_dd
# "% Complete" → complete
# "Customer#ID" → customer_id (if multiple special chars)

# HEADER VALIDATION:
# ├─ Check: No whitespace (leading/trailing)
# ├─ Check: No special characters (except underscore)
# ├─ Check: All lowercase (consistency)
# ├─ Check: No duplicates
# └─ Check: Descriptive (not "Column1", "Column2")
```

### Step 4: Type Inference and Coercion
Convert string columns to appropriate types:

```python
def infer_and_coerce_types(df):
    """
    Automatically detect and convert column types.
    """
    for col in df.columns:
        # Skip if already non-string type
        if df[col].dtype != 'object':
            continue

        # Sample non-null values
        sample = df[col].dropna().head(100)
        if len(sample) == 0:
            continue

        # Try conversions in order

        # 1. BOOLEAN
        if set(sample.unique().lower()) <= {'true', 'false', 'yes', 'no', '1', '0'}:
            df[col] = df[col].map({
                'true': True, 'yes': True, '1': True,
                'false': False, 'no': False, '0': False
            })
            continue

        # 2. INTEGER
        try:
            test = pd.to_numeric(sample, errors='coerce')
            if test.notna().mean() > 0.9 and (test % 1 == 0).all():  # 90%+ coercible, all whole numbers
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')  # Int64 handles nulls
                continue
        except:
            pass

        # 3. FLOAT
        try:
            test = pd.to_numeric(sample, errors='coerce')
            if test.notna().mean() > 0.9:  # 90%+ coercible
                df[col] = pd.to_numeric(df[col], errors='coerce')
                continue
        except:
            pass

        # 4. DATETIME
        try:
            test = pd.to_datetime(sample, errors='coerce', infer_datetime_format=True)
            if test.notna().mean() > 0.9:  # 90%+ coercible
                df[col] = pd.to_datetime(df[col], errors='coerce')
                continue
        except:
            pass

        # 5. CATEGORY (if < 50 unique values)
        if df[col].nunique() < 50:
            df[col] = df[col].astype('category')

        # Otherwise: remains string

    return df

# QUALITY CHECKS POST-COERCION:
# ├─ Check: Expected type conversions successful
# ├─ Check: Nulls after coercion (strings that didn't convert)
# ├─ Check: Outliers (extreme values post-conversion)
# └─ Check: No silent data loss
```

### Step 5: Reshape Data (Pivot/Unpivot)
Reorganize structure for analysis:

```python
import pandas as pd

# UNPIVOT (Wide to Long format)
# Before: Each month in separate column
#   Customer | Jan | Feb | Mar
#   Alice    | 100 | 150 | 200
#   Bob      | 80  | 120 | 160

# After: One row per customer-month
#   Customer | Month | Revenue
#   Alice    | Jan   | 100
#   Alice    | Feb   | 150
#   Bob      | Jan   | 80

df_long = pd.melt(
    df_wide,
    id_vars=['Customer'],  # Columns that identify observation
    value_vars=['Jan', 'Feb', 'Mar'],  # Columns to unpivot
    var_name='Month',  # New column for variable names
    value_name='Revenue'  # New column for values
)

# PIVOT (Long to Wide format)
# Before: One row per customer-segment
#   Customer | Segment | Revenue
#   Alice    | Online  | 500
#   Alice    | Retail  | 300
#   Bob      | Online  | 600

# After: Segments as columns
#   Customer | Online | Retail
#   Alice    | 500    | 300
#   Bob      | 600    | NaN

df_wide = df_long.pivot(
    index='Customer',  # Row identifiers
    columns='Segment',  # Column names
    values='Revenue'  # Cell values
)

# CROSSTAB (Pivot with aggregation)
# Useful when multiple rows per cell (need to aggregate)

pd.crosstab(
    index=df['Customer'],
    columns=df['Product'],
    values=df['Amount'],
    aggfunc='sum',  # Aggregate duplicates by summing
    margins=True  # Add row/column totals
)
```

### Step 6: Aggregate and Transform
Summarize data for analysis:

```python
# AGGREGATION (GROUP BY operations)

# Count records by category
df.groupby('Status').size()
# Output: Pending | 1000
#         Shipped | 500
#         Delivered | 2000

# Multiple aggregations on same group
df.groupby(['Country', 'Product']).agg({
    'Amount': ['sum', 'mean', 'count'],
    'Date': 'max',  # Most recent date per group
    'Customer': 'nunique'  # Unique customers
}).round(2)

# JOINS (Combine multiple CSVs)

# Customers + Orders on customer_id
merged = customers.merge(
    orders,
    on='customer_id',
    how='left'  # Keep all customers, even without orders
)

# Multiple joins
result = (
    orders
    .merge(customers, on='customer_id', how='left')
    .merge(products, on='product_id', how='left')
    .merge(regions, on='country', how='left')
)

# DEDUPLICATION
# Remove exact duplicates
df_clean = df.drop_duplicates()

# Remove duplicates on specific columns (keep first)
df_clean = df.drop_duplicates(subset=['order_id', 'customer_id'], keep='first')

# FILTERING
df_filtered = df[
    (df['amount'] > 100) &  # AND
    (df['status'].isin(['pending', 'shipped'])) &
    (df['date'] >= '2026-01-01')
]

# COMPUTED COLUMNS
df['revenue_per_unit'] = df['total_amount'] / df['quantity']
df['is_large_order'] = df['total_amount'] > 1000
df['year'] = pd.to_datetime(df['date']).dt.year
```

### Step 7: Validate and Export
Ensure output quality before delivery:

```python
def validate_and_export(df, output_path):
    """
    Quality checks before saving transformed data.
    """
    print("Validation Report")
    print("=" * 50)

    # CHECK 1: Dimensions
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    # CHECK 2: Completeness
    nulls = df.isnull().sum()
    if (nulls > 0).any():
        print(f"Missing values: {nulls[nulls > 0].to_dict()}")

    # CHECK 3: Data types
    print(f"Data types:\n{df.dtypes}")

    # CHECK 4: Duplicates
    dups = df.duplicated().sum()
    print(f"Exact duplicates: {dups}")

    # CHECK 5: Numeric ranges
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        print(f"{col}: min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.2f}")

    # CHECK 6: Samples
    print(f"\nFirst few rows:\n{df.head()}")

    # EXPORT (choose format based on use case)

    # CSV (most compatible)
    df.to_csv(
        output_path,
        index=False,  # Don't include row index
        encoding='utf-8',  # Standard encoding
        quotechar='"',
        lineterminator='\n'
    )

    # Parquet (faster for big data)
    df.to_parquet(output_path, index=False, compression='snappy')

    # Excel (for distribution to non-technical users)
    df.to_excel(
        output_path,
        index=False,
        sheet_name='Data'
    )

    print(f"\nExported to: {output_path}")

# EXPORT BEST PRACTICES:
# ├─ CSV: Ubiquitous, slow on large files (100M+ rows)
# ├─ Parquet: Fast, columnar, good compression (big data)
# ├─ Excel: Readable, limited to 1M rows, slow
# └─ Database: Most efficient for large volumes
```

## Output Template

**CSV Transformation Log:**

```markdown
# CSV Transform Report

**Source file**: customers_export.csv
**Date processed**: 2026-03-05
**Processed by**: Analytics pipeline

## Detection
- Encoding: UTF-8 (confidence: 95%)
- Delimiter: Comma
- File size: 45.3 MB
- Original rows: 1,000,500

## Issues Found and Fixed
1. **Encoding**: Original file was ISO-8859-1, detected and converted
2. **Headers**: Cleaned "Customer Name" → "customer_name" (10 columns standardized)
3. **Types**: Inferred 23 numeric, 5 datetime, 8 categorical, 2 string
4. **Duplicates**: Removed 234 exact duplicate rows (on customer_id)
5. **Nulls**: 1.2% missing in email, 0% in customer_id (acceptable)

## Transformations Applied
- Unpivoted 12 monthly revenue columns to long format
- Merged with product_lookup.csv (left join on product_id)
- Aggregated revenue by customer and product
- Filtered to transactions >= $100 (removed 15% of rows)

## Output Quality
✓ Rows: 850,127 (15% reduction from deduplication + filtering)
✓ Columns: 18 (9 original + 5 derived)
✓ Data types: All correct
✓ Completeness: 99.8%
✓ Duplicates: 0

**Output file**: customers_clean.parquet
**Export time**: 23 seconds
**Export size**: 12.4 MB (Parquet compression)
```

## Quality Gates

1. **Encoding detected**: File successfully readable
2. **Delimiter identified**: Column parsing correct
3. **Headers cleaned**: All lowercase, no special chars, no duplicates
4. **Types inferred**: Data converted to appropriate types
5. **Nulls documented**: Missing values explained or acceptable
6. **Output validated**: Quality checks passed before export

## Examples

**Good: Complete transformation with quality report**
```
Input: Wide CSV with mixed encodings and messy headers
Operations:
- Detected ISO-8859-1 encoding
- Standardized headers (cleaned special chars)
- Unpivoted monthly columns to long format
- Inferred numeric and date types
- Removed 50 exact duplicates
- Aggregated by customer

Output:
- Format: Parquet (12MB, compressed)
- Rows: 50,000 (0.5% removed as duplicates)
- Quality: 100% valid types, 99.9% complete
- Report: Documented all transformations
```

**Bad: Minimal effort, quality unknown**
```
"Loaded the CSV, removed some duplicates, saved it"
Issues: Encoding unknown, headers not cleaned, types not validated,
missing data not counted, no documentation of changes
```

## Common Mistakes

1. **Wrong encoding assumption**: Assuming UTF-8, file is ISO-8859-1; mojibake results
2. **Delimiter detection failure**: Assuming comma, file uses semicolon; columns merge
3. **Type inference errors**: Numeric column read as string (0.1% non-numeric)
4. **Silent data loss**: Coercing to int loses decimals without warning
5. **Header duplication**: Two "ID" columns, analysis uses wrong one
6. **Join data loss**: Left merge loses rows where key missing

## Anti-Patterns

1. **Manual fixes in Excel**: "I'll just fix this in Excel" (not reproducible, error-prone)
2. **Type specification too strict**: Declaring all columns as int, missing values become null
3. **Pivot without aggregation**: Two rows per cell after pivot, which value to show?
4. **No validation output**: Transform completed but quality unknown
5. **One-off scripts**: Each CSV gets custom code; inconsistent results