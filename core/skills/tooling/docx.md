---
name: docx
description: |
  Comprehensive Word document creation, editing, and analysis.

  Use when working with:
  - Word documents (.docx)
  - Tracked changes and comments
  - Document formatting
  - Text extraction
  - Redlining workflow

  Includes: python-docx, pandoc, OOXML patterns.
---

# Word Document Operations

## Decision Tree

### Reading/Analyzing
```bash
pandoc --track-changes=all file.docx -o output.md
```

### Creating New Document
Use **python-docx**:
```python
from docx import Document
from docx.shared import Pt, Inches

doc = Document()
doc.add_heading('Title', 0)
doc.add_paragraph('Content here.')
doc.save('output.docx')
```

### Editing Existing Document
```python
from docx import Document

doc = Document('existing.docx')
# Modify content
doc.save('modified.docx')
```

## Creating Documents

```python
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Create new document
doc = Document()

# Add heading
doc.add_heading('Document Title', level=0)

# Add paragraph
para = doc.add_paragraph('This is a paragraph.')
para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

# Add formatted text
para = doc.add_paragraph()
run = para.add_run('Bold text')
run.bold = True
run = para.add_run(' and ')
run = para.add_run('italic text')
run.italic = True

# Add bullet list
doc.add_paragraph('First item', style='List Bullet')
doc.add_paragraph('Second item', style='List Bullet')

# Add numbered list
doc.add_paragraph('First item', style='List Number')
doc.add_paragraph('Second item', style='List Number')

# Add table
table = doc.add_table(rows=3, cols=3)
table.style = 'Table Grid'
for i, row in enumerate(table.rows):
    for j, cell in enumerate(row.cells):
        cell.text = f'Row {i+1}, Col {j+1}'

# Add image
doc.add_picture('image.png', width=Inches(4))

# Add page break
doc.add_page_break()

# Save
doc.save('output.docx')
```

## Reading Documents

```python
from docx import Document

doc = Document('file.docx')

# Read all paragraphs
for para in doc.paragraphs:
    print(para.text)

# Read tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)

# Read headers/footers
for section in doc.sections:
    header = section.header
    for para in header.paragraphs:
        print(para.text)
```

## Formatting

```python
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Font styling
run = para.add_run('Styled text')
run.font.size = Pt(12)
run.font.name = 'Arial'
run.font.color.rgb = RGBColor(0, 0, 255)  # Blue
run.bold = True
run.italic = True
run.underline = True

# Paragraph formatting
para.alignment = WD_ALIGN_PARAGRAPH.CENTER
para.paragraph_format.space_before = Pt(12)
para.paragraph_format.space_after = Pt(12)
para.paragraph_format.line_spacing = 1.5
para.paragraph_format.first_line_indent = Inches(0.5)
```

## Using Pandoc

```bash
# DOCX to Markdown (with track changes)
pandoc --track-changes=all input.docx -o output.md

# Markdown to DOCX
pandoc input.md -o output.docx

# With reference template
pandoc input.md --reference-doc=template.docx -o output.docx

# Extract images
pandoc input.docx --extract-media=./media -o output.md
```

## Redlining Workflow (Tracked Changes)

For legal/business documents:

1. **Get markdown** with tracked changes:
```bash
pandoc --track-changes=all file.docx -o current.md
```

2. **Review changes** in markdown format

3. **Make modifications** using python-docx

4. **Verify** by converting back to markdown

## Minimal Edit Principle

Only mark text that actually changes:
```python
# BAD - Replaces entire sentence
# 'The term is 30 days.' -> 'The term is 60 days.'

# GOOD - Only change what's different
# Change '30' to '60', keep rest unchanged
```

## Find and Replace

```python
def find_and_replace(doc, find_text, replace_text):
    for para in doc.paragraphs:
        if find_text in para.text:
            for run in para.runs:
                if find_text in run.text:
                    run.text = run.text.replace(find_text, replace_text)
    return doc

doc = Document('file.docx')
find_and_replace(doc, 'old text', 'new text')
doc.save('modified.docx')
```

## Convert to Images

```bash
# Convert DOCX to PDF first
soffice --headless --convert-to pdf document.docx

# Then PDF to images
pdftoppm -jpeg -r 150 document.pdf page
```

## Best Practices

1. **python-docx** for creating/editing
2. **pandoc** for format conversion
3. Preserve formatting when editing
4. Use styles consistently
5. Test with actual Word to verify rendering
6. Back up original before modifications
