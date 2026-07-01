---
name: xlsx
version: "2.0"
description: |
  Professional spreadsheet creation, editing, and analysis.

  Use when working with:
  - Excel files (.xlsx, .xlsm)
  - CSV/TSV files
  - Creating spreadsheets with formulas
  - Financial models and reports
  - Data analysis and visualization
  - Recalculating and validating formulas

  Includes: pandas, openpyxl, formula patterns, color coding, professional formatting,
  LibreOffice recalculation, CLI tools, formula verification.
---

# Excel/Spreadsheet Operations v2.0

## Quick Reference

| Task | Tool | Example |
|------|------|---------|
| Read data | pandas | `pd.read_excel('file.xlsx')` |
| Read with formulas | openpyxl | `load_workbook('file.xlsx')` |
| Create spreadsheet | openpyxl | `Workbook()` |
| Bulk data ops | pandas | `df.to_excel()` |
| Recalculate | LibreOffice | `recalc.py file.xlsx` |
| CSV to XLSX | csvkit | `in2csv file.xlsx > out.csv` |
| Validate formulas | openpyxl | Check for #REF!, #DIV/0! |
| Merge files | pandas | `pd.concat([df1, df2])` |

---

## Critical Rules (MANDATORY)

### 1. Zero Formula Errors
Every Excel file MUST have ZERO errors before delivery:
- `#REF!` - Invalid cell reference
- `#DIV/0!` - Division by zero
- `#VALUE!` - Wrong value type
- `#N/A` - Value not available
- `#NAME?` - Unrecognized formula name
- `#NUM!` - Invalid numeric value
- `#NULL!` - Incorrect range reference

**Verification:** Run formula check BEFORE saving final file.

### 2. Use Formulas, Not Hardcodes
```python
# WRONG - Hardcoding calculated values
total = df['Sales'].sum()
sheet['B10'] = total  # Hardcodes 5000

# CORRECT - Using Excel formulas
sheet['B10'] = '=SUM(B2:B9)'
```

### 3. Professional Fonts (Financial Models)
| Element | Font | Size |
|---------|------|------|
| Headers | Arial Bold | 10-11pt |
| Data cells | Arial | 10pt |
| Titles | Arial Bold | 12-14pt |
| Notes | Arial Italic | 9pt |

**Rule:** Use Arial or Calibri exclusively. No decorative fonts.

---

## Rationalizations (Do Not Skip)

| Rationalization | Why It's Wrong | Required Action |
|-----------------|----------------|-----------------|
| "I'll fix formulas later" | Broken formulas propagate errors | Zero errors BEFORE delivery |
| "Hardcoded values are faster" | Lose auditability and refresh capability | ALWAYS use formulas |
| "Color coding is optional" | Reviewers can't distinguish inputs from calcs | Follow color standards |
| "Close enough formatting" | Unprofessional, signals low quality | Match industry standards |
| "I validated visually" | Human eye misses errors in large sheets | Run automated verification |
| "Recalc takes too long" | Wrong values = wrong decisions | Always recalc before delivery |

---

## Color Coding Standards (Financial Models)

Industry-standard color coding for financial models:

| Color | Usage | Example |
|-------|-------|---------|
| **Blue text** | Hardcoded inputs (user-editable) | Revenue assumptions |
| **Black text** | ALL formulas (calculated) | =SUM(), =VLOOKUP() |
| **Green text** | Links from other worksheets | ='Summary'!B10 |
| **Red text** | External links to other files | ='[Budget.xlsx]Sheet1'!A1 |
| **Yellow background** | Key assumptions | Growth rate, discount rate |

```python
from openpyxl.styles import Font, PatternFill

# Color definitions
BLUE_INPUT = Font(color='0000FF')       # Hardcoded inputs
BLACK_FORMULA = Font(color='000000')    # Formulas
GREEN_INTERNAL = Font(color='008000')   # Internal links
RED_EXTERNAL = Font(color='FF0000')     # External links
YELLOW_ASSUMPTION = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

# Apply to cells
sheet['B2'].font = BLUE_INPUT           # Input cell
sheet['B10'].font = BLACK_FORMULA       # Formula cell
sheet['C5'].font = GREEN_INTERNAL       # Link to other sheet
sheet['D5'].font = RED_EXTERNAL         # External file link
sheet['B3'].fill = YELLOW_ASSUMPTION    # Key assumption
```

---

## Number Formatting Standards

| Data Type | Format Code | Display Example |
|-----------|-------------|-----------------|
| Currency | `'$#,##0.00'` | $1,234.56 |
| Currency (thousands) | `'$#,##0,"K"'` | $1,234K |
| Currency (millions) | `'$#,##0.0,,"M"'` | $1.2M |
| Percentage | `'0.0%'` | 12.5% |
| Percentage (whole) | `'0%'` | 13% |
| Integer | `'#,##0'` | 1,234 |
| Decimal (2 places) | `'#,##0.00'` | 1,234.56 |
| Zero as dash | `'#,##0;(#,##0);"-"'` | - (for zero) |
| Negative in parens | `'#,##0;(#,##0)'` | (1,234) |
| Date | `'YYYY-MM-DD'` | 2024-03-15 |
| Date (display) | `'MMM DD, YYYY'` | Mar 15, 2024 |

```python
# Apply number formats
sheet['B2'].number_format = '$#,##0.00'           # Currency
sheet['C2'].number_format = '0.0%'                # Percentage
sheet['D2'].number_format = '#,##0;(#,##0);"-"'   # Zero as dash
sheet['E2'].number_format = 'YYYY-MM-DD'          # Date
```

### Zero Display Rule
**CRITICAL:** Zeros should display as "-" (dash), not "0" or blank.
```python
ZERO_AS_DASH = '#,##0;(#,##0);"-"'
```

---

## Reading Data

### With pandas
```python
import pandas as pd

# Read single sheet
df = pd.read_excel('file.xlsx')

# Read specific sheet
df = pd.read_excel('file.xlsx', sheet_name='Data')

# Read all sheets (returns dict)
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)

# Read with options
df = pd.read_excel(
    'file.xlsx',
    sheet_name='Data',
    header=0,           # Row index for headers
    usecols='A:E',      # Columns to read
    skiprows=2,         # Skip first N rows
    nrows=100,          # Read only N rows
    dtype={'ID': str}   # Force column types
)

# Basic statistics
print(df.describe())
print(df.info())
print(df.head())
```

### With openpyxl
```python
from openpyxl import load_workbook

wb = load_workbook('file.xlsx')
sheet = wb.active

# Read cell value
value = sheet['A1'].value

# Read cell with formula (returns formula string)
formula = sheet['B10'].value  # '=SUM(B2:B9)'

# Read range
for row in sheet['A1:C10']:
    for cell in row:
        print(cell.value)

# Read entire sheet to list
data = []
for row in sheet.iter_rows(values_only=True):
    data.append(row)

# WARNING: data_only=True reads calculated values but LOSES formulas!
wb_values = load_workbook('file.xlsx', data_only=True)
```

---

## Creating/Editing

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Create new workbook
wb = Workbook()
sheet = wb.active
sheet.title = 'Sales Data'

# Write headers with formatting
headers = ['Product', 'Sales', 'Cost', 'Margin']
for col, header in enumerate(headers, 1):
    cell = sheet.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True, size=11)
    cell.alignment = Alignment(horizontal='center')

# Write data
data = [
    ['Widget A', 1000, 600],
    ['Widget B', 1500, 900],
    ['Widget C', 800, 480],
]
for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        cell = sheet.cell(row=row_idx, column=col_idx, value=value)
        if col_idx >= 2:  # Numeric columns
            cell.number_format = '$#,##0.00'
            cell.font = BLUE_INPUT  # Inputs in blue

# Add formulas (NOT hardcoded values!)
for row in range(2, 5):
    margin_cell = sheet.cell(row=row, column=4)
    margin_cell.value = f'=(B{row}-C{row})/B{row}'
    margin_cell.number_format = '0.0%'
    margin_cell.font = BLACK_FORMULA  # Formulas in black

# Add totals row
sheet['A5'] = 'Total'
sheet['B5'] = '=SUM(B2:B4)'
sheet['C5'] = '=SUM(C2:C4)'
sheet['D5'] = '=(B5-C5)/B5'

# Column widths
sheet.column_dimensions['A'].width = 15
sheet.column_dimensions['B'].width = 12
sheet.column_dimensions['C'].width = 12
sheet.column_dimensions['D'].width = 10

# Freeze header row
sheet.freeze_panes = 'A2'

# Save
wb.save('output.xlsx')
```

---

## Common Formulas

```python
# Arithmetic
sheet['B10'] = '=SUM(B2:B9)'
sheet['B11'] = '=AVERAGE(B2:B9)'
sheet['B12'] = '=COUNT(B2:B9)'
sheet['B13'] = '=MAX(B2:B9)'
sheet['B14'] = '=MIN(B2:B9)'

# Conditional
sheet['C2'] = '=IF(B2>100,"High","Low")'
sheet['C3'] = '=IF(B3>100,"High",IF(B3>50,"Medium","Low"))'  # Nested IF
sheet['D2'] = '=IFERROR(A2/B2,0)'  # Handle divide by zero

# Lookups
sheet['D2'] = '=VLOOKUP(A2,Products!A:B,2,FALSE)'  # Exact match
sheet['E2'] = '=INDEX(Data!B:B,MATCH(A2,Data!A:A,0))'  # INDEX/MATCH
sheet['F2'] = '=XLOOKUP(A2,Products!A:A,Products!B:B,"Not Found")'  # Modern

# Conditional aggregation
sheet['B15'] = '=SUMIF(A:A,"Widget",B:B)'
sheet['B16'] = '=SUMIFS(B:B,A:A,"Widget",C:C,">100")'
sheet['B17'] = '=COUNTIF(A:A,"Widget")'
sheet['B18'] = '=AVERAGEIF(A:A,"Widget",B:B)'

# References
sheet['C2'] = '=B2/B$10'        # Mixed reference (row absolute)
sheet['D2'] = '=$A2&" - "&B2'   # Mixed reference (column absolute)
sheet['E2'] = '=$A$1'           # Absolute reference

# Cross-sheet references
sheet['F2'] = "='Summary'!B10"              # Same workbook
sheet['G2'] = "='[Budget.xlsx]Sheet1'!A1"   # External workbook
```

---

## Professional Formatting

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle

# Define reusable styles
header_style = NamedStyle(name='header')
header_style.font = Font(bold=True, size=11, name='Arial')
header_style.alignment = Alignment(horizontal='center', vertical='center')
header_style.fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
header_style.border = Border(bottom=Side(style='medium'))

input_style = NamedStyle(name='input')
input_style.font = Font(color='0000FF', name='Arial', size=10)  # Blue for inputs

formula_style = NamedStyle(name='formula')
formula_style.font = Font(color='000000', name='Arial', size=10)  # Black for formulas

# Register styles
wb.add_named_style(header_style)
wb.add_named_style(input_style)
wb.add_named_style(formula_style)

# Apply styles
sheet['A1'].style = 'header'
sheet['B2'].style = 'input'
sheet['B10'].style = 'formula'

# Borders
thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Apply border to range
for row in sheet['A1:D10']:
    for cell in row:
        cell.border = thin_border

# Alignment
sheet['A1'].alignment = Alignment(
    horizontal='center',  # left, center, right
    vertical='center',    # top, center, bottom
    wrap_text=True,       # Wrap long text
    indent=1              # Indentation level
)
```

---

## Data Validation

```python
from openpyxl.worksheet.datavalidation import DataValidation

# Dropdown list
dv_list = DataValidation(
    type='list',
    formula1='"Option1,Option2,Option3"',
    allow_blank=True,
    showDropDown=False  # False shows the dropdown arrow
)
dv_list.error = 'Please select from the list'
dv_list.errorTitle = 'Invalid Selection'
sheet.add_data_validation(dv_list)
dv_list.add('A2:A100')

# Number range
dv_num = DataValidation(
    type='whole',
    operator='between',
    formula1='1',
    formula2='100'
)
dv_num.error = 'Enter a number between 1 and 100'
sheet.add_data_validation(dv_num)
dv_num.add('B2:B100')

# Date validation
dv_date = DataValidation(
    type='date',
    operator='greaterThan',
    formula1='2024-01-01'
)
sheet.add_data_validation(dv_date)
dv_date.add('C2:C100')

# Custom formula validation
dv_custom = DataValidation(
    type='custom',
    formula1='=AND(LEN(A2)>=5,LEN(A2)<=10)'  # String length 5-10
)
sheet.add_data_validation(dv_custom)
dv_custom.add('D2:D100')
```

---

## Charts

```python
from openpyxl.chart import BarChart, LineChart, PieChart, Reference

# Bar Chart
bar_chart = BarChart()
bar_chart.title = "Sales by Product"
bar_chart.style = 10  # Built-in style
bar_chart.y_axis.title = "Sales ($)"
bar_chart.x_axis.title = "Product"

data = Reference(sheet, min_col=2, min_row=1, max_col=2, max_row=10)
categories = Reference(sheet, min_col=1, min_row=2, max_row=10)

bar_chart.add_data(data, titles_from_data=True)
bar_chart.set_categories(categories)
bar_chart.shape = 4  # Rectangle bars
sheet.add_chart(bar_chart, "E2")

# Line Chart
line_chart = LineChart()
line_chart.title = "Monthly Trend"
line_chart.style = 12
line_chart.y_axis.crossAx = 500
line_chart.x_axis.tickLblPos = "low"

data = Reference(sheet, min_col=2, min_row=1, max_col=4, max_row=13)
line_chart.add_data(data, titles_from_data=True)
sheet.add_chart(line_chart, "E15")

# Pie Chart
pie_chart = PieChart()
pie_chart.title = "Market Share"
labels = Reference(sheet, min_col=1, min_row=2, max_row=5)
data = Reference(sheet, min_col=2, min_row=1, max_row=5)
pie_chart.add_data(data, titles_from_data=True)
pie_chart.set_categories(labels)
sheet.add_chart(pie_chart, "E28")
```

---

## LibreOffice Recalculation

**CRITICAL:** Python cannot evaluate Excel formulas. Use LibreOffice for recalculation.

### recalc.py Script
```python
#!/usr/bin/env python3
"""
Recalculate Excel formulas using LibreOffice.
Usage: python recalc.py input.xlsx [output.xlsx]
"""

import subprocess
import sys
import os
from pathlib import Path

def recalc_xlsx(input_path: str, output_path: str = None) -> bool:
    """Recalculate Excel file using LibreOffice headless mode."""
    input_path = Path(input_path).resolve()

    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path).resolve()

    # LibreOffice paths by platform
    lo_paths = [
        r'C:\Program Files\LibreOffice\program\soffice.exe',  # Windows
        '/usr/bin/soffice',                                     # Linux
        '/Applications/LibreOffice.app/Contents/MacOS/soffice'  # macOS
    ]

    soffice = None
    for path in lo_paths:
        if os.path.exists(path):
            soffice = path
            break

    if not soffice:
        print("ERROR: LibreOffice not found")
        return False

    # Convert to calc-compatible format, forcing recalculation
    cmd = [
        soffice,
        '--headless',
        '--calc',
        '--convert-to', 'xlsx',
        '--outdir', str(output_path.parent),
        str(input_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"Recalculated: {output_path}")
            return True
        else:
            print(f"ERROR: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("ERROR: Recalculation timed out")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python recalc.py input.xlsx [output.xlsx]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    success = recalc_xlsx(input_file, output_file)
    sys.exit(0 if success else 1)
```

### Usage
```bash
# Recalculate in place
python scripts/recalc.py output.xlsx

# Recalculate to new file
python scripts/recalc.py input.xlsx recalculated.xlsx
```

---

## CLI Tools

### csvkit (CSV Swiss Army Knife)
```bash
# Install
pip install csvkit

# Convert Excel to CSV
in2csv data.xlsx > data.csv
in2csv data.xlsx --sheet "Sheet2" > sheet2.csv

# CSV statistics
csvstat data.csv

# Query CSV with SQL
csvsql --query "SELECT * FROM data WHERE sales > 1000" data.csv

# Convert CSV to Excel
# (Use pandas for this)
```

### xlsx2csv
```bash
# Install
pip install xlsx2csv

# Convert single sheet
xlsx2csv data.xlsx data.csv

# Convert specific sheet
xlsx2csv -s 2 data.xlsx sheet2.csv

# Convert all sheets
xlsx2csv -a data.xlsx output_dir/
```

### ssconvert (Gnumeric)
```bash
# Convert formats
ssconvert input.xlsx output.csv
ssconvert input.csv output.xlsx

# Recalculate (limited)
ssconvert --recalc input.xlsx output.xlsx
```

---

## Formula Verification Checklist

Run this verification BEFORE delivering any Excel file:

```python
def verify_excel_formulas(filepath: str) -> dict:
    """
    Verify Excel file has zero formula errors.
    Returns dict with error details.
    """
    from openpyxl import load_workbook
    import re

    # Load with data_only to see calculated values
    wb = load_workbook(filepath, data_only=True)

    errors = {
        '#REF!': [],
        '#DIV/0!': [],
        '#VALUE!': [],
        '#N/A': [],
        '#NAME?': [],
        '#NUM!': [],
        '#NULL!': [],
    }

    error_pattern = re.compile(r'#(REF!|DIV/0!|VALUE!|N/A|NAME\?|NUM!|NULL!)')

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    match = error_pattern.search(cell.value)
                    if match:
                        error_type = '#' + match.group(1)
                        errors[error_type].append(f"{sheet_name}!{cell.coordinate}")

    # Summary
    total_errors = sum(len(v) for v in errors.values())

    return {
        'total_errors': total_errors,
        'errors': {k: v for k, v in errors.items() if v},
        'passed': total_errors == 0
    }

# Usage
result = verify_excel_formulas('output.xlsx')
if not result['passed']:
    print(f"FAILED: {result['total_errors']} errors found")
    for error_type, locations in result['errors'].items():
        print(f"  {error_type}: {locations}")
else:
    print("PASSED: Zero formula errors")
```

### Manual Verification Steps
1. **Open in Excel** - Check for any error indicators
2. **Ctrl+`** - Toggle formula view, scan for errors
3. **Go To Special** (Ctrl+G > Special > Formulas > Errors) - Find all errors
4. **Verify color coding** - Blue=inputs, Black=formulas
5. **Check totals** - Do summary numbers make sense?
6. **Spot check formulas** - Random sample verification

---

## Best Practices

| Practice | Rationale |
|----------|-----------|
| Use formulas, not hardcodes | Auditability, refresh capability |
| Zero formula errors | Data integrity |
| Color code consistently | Reviewer can distinguish inputs vs calcs |
| Professional fonts (Arial) | Industry standard, prints well |
| Zeros as dashes | Cleaner appearance, easier scanning |
| Freeze header rows | Navigation in large sheets |
| Named ranges | Self-documenting formulas |
| Document assumptions | Yellow highlight key inputs |
| Recalc before delivery | Ensure calculated values are current |
| Verify before sending | Automated + manual checks |

### When to Use Which Tool

| Task | Best Tool |
|------|-----------|
| Data analysis, aggregation | pandas |
| Creating formatted Excel | openpyxl |
| Simple CSV processing | csvkit |
| Bulk data transforms | pandas |
| Complex formulas | openpyxl + LibreOffice recalc |
| Financial models | openpyxl with all standards |
| Quick conversions | xlsx2csv, in2csv |
| Formula recalculation | LibreOffice (recalc.py) |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Formulas show as text | Remove leading apostrophe, or recreate cell |
| data_only loses formulas | Don't use data_only for editing |
| Colors don't appear | Check color format (RGB vs indexed) |
| Numbers as text | Force number format or multiply by 1 |
| Date serial numbers | Apply date format to cells |
| #REF! errors | Fix broken cell references |
| LibreOffice hangs | Kill soffice.bin process, retry |
| Large file slow | Use read_only=True mode for reading |

---

## Template: Financial Report

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle

def create_financial_report(data: list, output_path: str):
    """Create professionally formatted financial report."""
    wb = Workbook()
    sheet = wb.active
    sheet.title = 'Financial Summary'

    # Styles
    BLUE_INPUT = Font(color='0000FF', name='Arial', size=10)
    BLACK_FORMULA = Font(color='000000', name='Arial', size=10)
    HEADER_FONT = Font(bold=True, name='Arial', size=11)
    HEADER_FILL = PatternFill(start_color='D9E1F2', fill_type='solid')
    YELLOW_ASSUMPTION = PatternFill(start_color='FFFF00', fill_type='solid')

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Headers
    headers = ['Description', 'Amount', '% of Total']
    for col, header in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Data rows
    for row_idx, (desc, amount) in enumerate(data, 2):
        # Description
        sheet.cell(row=row_idx, column=1, value=desc).border = thin_border

        # Amount (input - blue)
        amount_cell = sheet.cell(row=row_idx, column=2, value=amount)
        amount_cell.font = BLUE_INPUT
        amount_cell.number_format = '$#,##0.00'
        amount_cell.border = thin_border

        # Percentage (formula - black)
        pct_cell = sheet.cell(row=row_idx, column=3)
        total_row = len(data) + 2
        pct_cell.value = f'=B{row_idx}/B${total_row}'
        pct_cell.font = BLACK_FORMULA
        pct_cell.number_format = '0.0%'
        pct_cell.border = thin_border

    # Total row
    total_row = len(data) + 2
    sheet.cell(row=total_row, column=1, value='Total').font = HEADER_FONT

    total_cell = sheet.cell(row=total_row, column=2)
    total_cell.value = f'=SUM(B2:B{total_row-1})'
    total_cell.font = Font(bold=True, name='Arial', size=10)
    total_cell.number_format = '$#,##0.00'
    total_cell.border = thin_border

    sheet.cell(row=total_row, column=3, value=1).number_format = '0.0%'

    # Column widths
    sheet.column_dimensions['A'].width = 25
    sheet.column_dimensions['B'].width = 15
    sheet.column_dimensions['C'].width = 12

    # Freeze header
    sheet.freeze_panes = 'A2'

    wb.save(output_path)
    print(f"Created: {output_path}")

# Usage
data = [
    ('Revenue', 100000),
    ('Cost of Goods', 45000),
    ('Operating Expenses', 30000),
    ('Net Income', 25000),
]
create_financial_report(data, 'financial_report.xlsx')
```

---

*xlsx skill v2.0 | Professional formatting | Zero-error mandate | LibreOffice recalc | Formula verification*
