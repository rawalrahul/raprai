---
name: openpyxl-spreadsheet-engine
description: "Professional spreadsheet creation with formulas, conditional formatting, data validation, charts, and financial model color coding using openpyxl"
category: office
difficulty: intermediate
model_boost: "Weak models hardcode formula results as static values, ignore data validation and conditional formatting, create charts without proper series configuration, and don't implement color coding conventions. This engine uses formulas (SUM, VLOOKUP, SUMIFS), dynamic charts, and financial model standards."
---

# OpenPyXL Spreadsheet Generation Engine

## Purpose
Generate professional Excel spreadsheets (.xlsx) programmatically with formulas (not hardcoded values), data validation, conditional formatting, charts, and financial model conventions. Create spreadsheets that update dynamically when input cells change, enforce data quality, and follow accounting/finance color-coding standards (blue=inputs, yellow=assumptions, black=formulas, green=links).

## When to Use
- Generating financial models, budgets, or forecasts from data sources
- Creating data entry templates with validation and conditional formatting
- Building analytics dashboards with dynamic formulas and charts
- **Do NOT use when**: Editing existing complex spreadsheets (use Excel app), analyzing large datasets (use Pandas/SQL), or building interactive applications (use web frameworks)

## Instructions

### Step 1: Install and Import
```bash
pip install openpyxl
```

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, numbers
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.utils import get_column_letter
```

### Step 2: Define Color-Coding Convention
Financial model color scheme for cell types:

```python
# Financial Model Color Convention
COLOR_SCHEME = {
    'input': {           # User input values (light blue)
        'fill': 'FFB4C7E7',
        'font': '000000',
        'description': 'User Input'
    },
    'assumption': {      # Model assumptions (light yellow)
        'fill': 'FFFFFFE0',
        'font': '000000',
        'description': 'Assumption'
    },
    'formula': {         # Calculated values (no fill, bold black)
        'fill': 'FFFFFFFF',
        'font': '000000',
        'bold': True,
        'description': 'Formula'
    },
    'link': {            # Links to other sheets (light green)
        'fill': 'FFC6EFCE',
        'font': '000000',
        'description': 'Link'
    },
    'header': {          # Column/row headers (dark blue)
        'fill': 'FF2F5496',
        'font': 'FFFFFFFF',
        'bold': True,
        'description': 'Header'
    },
    'total': {           # Summary/total rows (dark gray)
        'fill': 'FF4F4F4F',
        'font': 'FFFFFFFF',
        'bold': True,
        'description': 'Total'
    }
}

def apply_cell_style(cell, style_type):
    """Apply color convention to cell."""
    style = COLOR_SCHEME[style_type]

    # Fill
    cell.fill = PatternFill(start_color=style['fill'], end_color=style['fill'], fill_type='solid')

    # Font
    cell.font = Font(
        color=style['font'],
        bold=style.get('bold', False),
        size=11
    )
```

### Step 3: Setup Workbook and Sheets
Initialize workbook with proper formatting:

```python
def setup_workbook():
    """Create workbook with default formatting."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Model'

    # Set default column width
    ws.column_dimensions['A'].width = 20
    for col in range(2, 26):
        ws.column_dimensions[get_column_letter(col)].width = 14

    # Set default row height
    ws.row_dimensions[1].height = 25

    return wb, ws
```

### Step 4: Helper Function - Add Header Row
Create formatted column headers:

```python
def add_header_row(ws, headers, start_col=1, start_row=1):
    """
    Add header row with standard formatting.

    headers: list of header strings
    Returns: row number after headers
    """
    for idx, header_text in enumerate(headers):
        cell = ws.cell(row=start_row, column=start_col + idx)
        cell.value = header_text
        apply_cell_style(cell, 'header')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    return start_row + 1
```

### Step 5: Helper Function - Add Input Cells
Mark cells for user input:

```python
def add_input_cell(ws, row, col, value=None, number_format='0.00'):
    """
    Add an input cell with proper formatting and validation hint.

    Returns: cell object
    """
    cell = ws.cell(row=row, column=col)
    cell.value = value
    apply_cell_style(cell, 'input')
    cell.number_format = number_format
    cell.alignment = Alignment(horizontal='right')

    return cell
```

### Step 6: Helper Function - Add Formula Cell
Insert formulas (not hardcoded values):

```python
def add_formula_cell(ws, row, col, formula, number_format='0.00'):
    """
    Add a formula cell (NOT static value).

    formula: Excel formula string, e.g., '=SUM(A1:A10)'
    Returns: cell object
    """
    cell = ws.cell(row=row, column=col)
    cell.value = formula
    apply_cell_style(cell, 'formula')
    cell.number_format = number_format
    cell.alignment = Alignment(horizontal='right')

    return cell
```

### Step 7: Create Named Ranges
Enable formula readability:

```python
def create_named_range(wb, ws, name, cell_range):
    """
    Create a named range for use in formulas.

    name: string name for range
    cell_range: e.g., 'A1:A10' or 'Model!B5'
    """
    try:
        wb.named_ranges[name] = f"{ws.title}!{cell_range}"
    except:
        # Skip if named range already exists
        pass
```

### Step 8: Data Validation
Add dropdown lists and range constraints:

```python
def add_data_validation_list(ws, cell_range, options):
    """
    Add dropdown validation to cells.

    cell_range: e.g., 'A2:A100'
    options: list of valid values
    """
    dv = DataValidation(type='list', formula1=f'"{",".join(options)}"', allow_blank=False)
    dv.error = 'Please select a valid option'
    dv.errorTitle = 'Invalid Entry'
    ws.add_data_validation(dv)
    dv.add(cell_range)

def add_data_validation_range(ws, cell_range, min_val, max_val):
    """
    Add numeric range validation.

    cell_range: e.g., 'B2:B100'
    min_val, max_val: numeric bounds
    """
    dv = DataValidation(type='decimal', operator='between', formula1=min_val, formula2=max_val, allow_blank=False)
    dv.error = f'Value must be between {min_val} and {max_val}'
    dv.errorTitle = 'Out of Range'
    ws.add_data_validation(dv)
    dv.add(cell_range)
```

### Step 9: Conditional Formatting
Apply rules to highlight data:

```python
def add_conditional_formatting(ws, cell_range, rule_type='value_above_average'):
    """
    Add conditional formatting to cells.

    rule_type: 'value_above_average', 'value_below_average', 'duplicate', etc.
    """
    if rule_type == 'value_above_average':
        ws.conditional_formatting.add(cell_range, CellIsRule(
            operator='greaterThan',
            formula=['100'],
            fill=PatternFill(start_color='FFC6EFCE', end_color='FFC6EFCE', fill_type='solid'),
            font=Font(color='00070C27')
        ))

def add_color_scale_formatting(ws, cell_range):
    """Add red-yellow-green color scale."""
    from openpyxl.formatting.rule import ColorScaleRule
    color_scale_rule = ColorScaleRule(
        start_type='min', start_color='FFFFEB9C',
        mid_type='percentile', mid_value=50, mid_color='FFFFEB9C',
        end_type='max', end_color='FFC6EFCE'
    )
    ws.conditional_formatting.add(cell_range, color_scale_rule)
```

### Step 10: Create Charts
Add visualizations linked to data:

```python
def add_bar_chart(ws, title, data_range, categories_range=None, insert_row=2, insert_col=10):
    """
    Create and insert a bar chart.

    data_range: e.g., 'B2:D10'
    categories_range: e.g., 'A2:A10' for labels
    """
    chart = BarChart()
    chart.type = 'col'
    chart.title = title
    chart.x_axis.title = 'Category'
    chart.y_axis.title = 'Value'

    # Add data series
    data = Reference(ws, min_col=2, min_row=1, max_row=10, max_col=4)
    categories = Reference(ws, min_col=1, min_row=2, max_row=10)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)

    # Style
    chart.height = 10  # Height in cm
    chart.width = 16   # Width in cm

    ws.add_chart(chart, f'{get_column_letter(insert_col)}{insert_row}')

def add_line_chart(ws, title, data_range, categories_range=None, insert_row=2, insert_col=10):
    """Create and insert a line chart."""
    chart = LineChart()
    chart.title = title
    chart.x_axis.title = 'Period'
    chart.y_axis.title = 'Value'

    data = Reference(ws, min_col=2, min_row=1, max_row=10, max_col=4)
    categories = Reference(ws, min_col=1, min_row=2, max_row=10)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)

    chart.height = 10
    chart.width = 16

    ws.add_chart(chart, f'{get_column_letter(insert_col)}{insert_row}')
```

### Step 11: Freeze Panes
Lock headers in place:

```python
def freeze_panes(ws, freeze_row=2, freeze_col=2):
    """
    Freeze panes to lock rows and columns.

    freeze_row: freeze rows 1 to N
    freeze_col: freeze columns A to N
    """
    cell = ws.cell(row=freeze_row, column=freeze_col)
    ws.freeze_panes = cell
```

### Step 12: Print Setup
Configure page layout:

```python
def setup_print_settings(ws, header_row=1):
    """
    Configure print settings for professional output.

    header_row: row to repeat at top of each printed page
    """
    ws.page_setup.orientation = 'landscape'
    ws.page_margins.left = 0.5
    ws.page_margins.right = 0.5
    ws.page_margins.top = 0.75
    ws.page_margins.bottom = 0.75

    # Repeat header row on each page
    ws.print_rows = f'1:{header_row}'

    # Set print area
    ws.print_area = f'A1:H100'

    # Fit to one page wide
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.print_options.horizontalCentered = False
```

## Complete Working Boilerplate

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

# Color scheme
COLOR_SCHEME = {
    'input': {'fill': 'FFB4C7E7', 'font': '000000'},
    'formula': {'fill': 'FFFFFFFF', 'font': '000000', 'bold': True},
    'header': {'fill': 'FF2F5496', 'font': 'FFFFFFFF', 'bold': True},
    'total': {'fill': 'FF4F4F4F', 'font': 'FFFFFFFF', 'bold': True},
}

def apply_cell_style(cell, style_type):
    style = COLOR_SCHEME[style_type]
    cell.fill = PatternFill(start_color=style['fill'], end_color=style['fill'], fill_type='solid')
    cell.font = Font(color=style['font'], bold=style.get('bold', False), size=11)

def setup_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Budget'
    ws.column_dimensions['A'].width = 20
    for col in range(2, 6):
        ws.column_dimensions[get_column_letter(col)].width = 14
    return wb, ws

def add_header_row(ws, headers, start_row=1):
    for idx, header in enumerate(headers):
        cell = ws.cell(row=start_row, column=idx + 1)
        cell.value = header
        apply_cell_style(cell, 'header')
        cell.alignment = Alignment(horizontal='center')
    return start_row + 1

def add_formula_cell(ws, row, col, formula):
    cell = ws.cell(row=row, column=col)
    cell.value = formula
    apply_cell_style(cell, 'formula')
    cell.number_format = '0.00'
    cell.alignment = Alignment(horizontal='right')

# Build spreadsheet
wb, ws = setup_workbook()

# Headers
row = add_header_row(ws, ['Item', 'Q1', 'Q2', 'Q3', 'Q4', 'Total'])

# Data rows
ws.cell(row=row, column=1).value = 'Revenue'
apply_cell_style(ws.cell(row=row, column=1), 'input')

# Input cells
ws.cell(row=row, column=2).value = 100000
apply_cell_style(ws.cell(row=row, column=2), 'input')
ws.cell(row=row, column=2).number_format = '0'

ws.cell(row=row, column=3).value = 120000
apply_cell_style(ws.cell(row=row, column=3), 'input')
ws.cell(row=row, column=3).number_format = '0'

# Formula for total (SUM)
add_formula_cell(ws, row, 6, '=SUM(B2:E2)')

row += 1

# Costs row
ws.cell(row=row, column=1).value = 'Costs'
apply_cell_style(ws.cell(row=row, column=1), 'input')

ws.cell(row=row, column=2).value = 50000
apply_cell_style(ws.cell(row=row, column=2), 'input')
ws.cell(row=row, column=2).number_format = '0'

ws.cell(row=row, column=3).value = 60000
apply_cell_style(ws.cell(row=row, column=3), 'input')
ws.cell(row=row, column=3).number_format = '0'

add_formula_cell(ws, row, 6, '=SUM(B3:E3)')

row += 1

# Profit row (uses formulas)
ws.cell(row=row, column=1).value = 'Profit'
apply_cell_style(ws.cell(row=row, column=1), 'total')

add_formula_cell(ws, row, 2, '=B2-B3')
add_formula_cell(ws, row, 3, '=C2-C3')
add_formula_cell(ws, row, 6, '=F2-F3')

# Freeze panes
ws.freeze_panes = ws['A2']

# Save
wb.save('financial_model.xlsx')
print('Spreadsheet created: financial_model.xlsx')
```

## Output Template
```
Expected .xlsx file with:
- Color-coded cells: blue input, yellow assumptions, white formula cells, green links, dark headers/totals
- Formulas (not hardcoded values): =SUM(B2:B10), =VLOOKUP(...), =IF(...), =SUMIFS(...)
- Number formats: currency ($), percentages (%), general (0 decimals)
- Data validation: dropdown lists, numeric ranges
- Conditional formatting: color scales, above/below average highlighting
- Charts: bar/line/pie with dynamic data references
- Frozen header rows and columns for navigation
- Print settings: landscape, 0.5" margins, repeating headers
- Named ranges for formula clarity
- Working formulas that recalculate when inputs change
```

## Quality Gates
1. **Formula Verification**: Inspect cells using formulas (=SUM, =VLOOKUP, etc.) NOT static values. Check formula bar in Excel to confirm.
2. **Color Scheme Consistency**: Verify input cells are light blue (FFB4C7E7), formula cells are white with bold black font, headers are dark blue with white text.
3. **Number Format Accuracy**: Confirm currency shows as $X,XXX.XX, percentages show as X.X%, and formulas inherit proper formatting.
4. **Data Validation**: Test dropdown cells accept only listed values; test range validation rejects out-of-bounds numbers.
5. **Chart Binding**: Click on chart and verify data series references worksheet cells (not static values); resize data and check chart updates.
6. **Recalculation**: Change an input cell value and confirm all dependent formulas update automatically.
7. **Print Layout**: Print preview should show frozen header rows at top, proper margins, and page breaks in logical places.

## Examples

### Good Example
```python
# Define assumptions at top
ws.cell(row=2, column=1).value = 'Growth Rate'
ws.cell(row=2, column=2).value = 0.10
apply_cell_style(ws.cell(row=2, column=2), 'assumption')

# Year 1 actual input
ws.cell(row=5, column=2).value = 100000
apply_cell_style(ws.cell(row=5, column=2), 'input')

# Year 2 calculated from Year 1 * Growth
add_formula_cell(ws, 5, 3, '=B5*(1+B$2)')

# Total row sums the years
add_formula_cell(ws, 6, 2, '=SUM(B5:D5)')

# Data validation on input range
dv = DataValidation(type='decimal', operator='greaterThan', formula1='0')
ws.add_data_validation(dv)
dv.add('B5:B7')

wb.save('projection_model.xlsx')
```

### Bad Example
```python
# Hardcoded values instead of formulas
ws.cell(row=5, column=2).value = 100000
ws.cell(row=5, column=3).value = 110000  # Should be =B5*1.1, not hardcoded
ws.cell(row=5, column=4).value = 121000  # Should be =C5*1.1, not hardcoded

# No color coding
for cell in ws['A2':'D5']:
    for c in cell:
        c.font = Font(size=11)  # Same for everything

# Manual totals instead of formulas
ws.cell(row=6, column=2).value = 331000  # Should be =SUM(B5:D5)

# No data validation
# Input cells have no constraints

# No frozen panes
# Headers scroll with data

# Missing number formats
# Currency shows as 100000 instead of $100,000.00

wb.save('bad_model.xlsx')
```

## Common Mistakes

1. **Hardcoding Formula Results**: Entering `100 + 110 = 210` as a value instead of `=SUM(A1:A2)`. File becomes static; changes to inputs don't propagate. Always use formulas.

2. **Inconsistent Number Formats**: Mixing `0`, `0.00`, and currency formats in the same column. Use consistent formatting: `'#,##0.00'` for currency, `'0.0%'` for percentages, `'0'` for integers.

3. **Ignoring Color Scheme**: Leaving all cells white except headers. Color coding (blue input, yellow assumption, white formula) makes financial models self-documenting and reduces errors.

4. **No Data Validation**: Accepting any text/number in input cells causes errors downstream. Always use `DataValidation` to restrict inputs to valid ranges or lists.

5. **Hardcoded Named Ranges**: Using `=SUM(B2:B100)` instead of `=SUM(revenue_range)`. Named ranges make formulas readable and maintainable.

## Anti-Patterns

1. **Creating Charts Without Proper Binding**: Copying and pasting chart images instead of using Excel chart objects. Charts become static. Always create charts with `BarChart()`, `LineChart()`, etc., and bind to cell references.

2. **Multiple Formulas in One Cell**: Using `=IF(A1>100, B1*C1, D1*E1)` when readability suffers. Break into helper columns or use intermediate cells for clarity.

3. **Not Freezing Header Rows**: Scrolling data without frozen headers makes it impossible to know what columns mean. Always use `freeze_panes` on the first data row.

4. **Manual Calculations**: Computing totals by hand and entering as values instead of using `=SUM()`. Defeats the purpose of spreadsheets; changes break everything.

5. **No Print Configuration**: Printing without `setup_print_settings()` results in poorly formatted output with cut-off columns or headers. Always configure orientation, margins, and repeating rows.

6. **Mixing Direct Formatting and Styles**: Some cells bold, some italic, some underlined—no consistency. Use color scheme and `apply_cell_style()` function for maintainability.

7. **VLOOKUP Without Error Handling**: Using `=VLOOKUP(...)` without `=IFERROR()` wrapper shows `#N/A` errors. Always wrap lookups: `=IFERROR(VLOOKUP(...), 0)` or `=IFERROR(VLOOKUP(...), "Not Found")`.
