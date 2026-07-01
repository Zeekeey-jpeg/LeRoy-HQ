---
name: pdf
description: |
  Comprehensive PDF manipulation toolkit.

  Use when working with:
  - Extracting text and tables from PDFs
  - OCR on scanned PDFs (pytesseract)
  - Creating new PDFs
  - Merging/splitting documents
  - Filling PDF forms
  - Converting to/from PDF
  - Command-line batch operations

  Includes: pypdf, pdfplumber, PyMuPDF, ReportLab, pytesseract, CLI tools (qpdf, pdftotext, pdftk).
---

# PDF Processing Guide v2.0

## Quick Reference

| Task | Best Tool | Notes |
|------|-----------|-------|
| Merge PDFs | pypdf or qpdf | pypdf for Python, qpdf for CLI |
| Split PDFs | pypdf or qpdf | One page per file |
| Extract text | pdfplumber | Best layout preservation |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | ReportLab | Canvas or Platypus |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | pypdf | See Forms section |
| CLI batch ops | qpdf/pdftotext | Fast, scriptable |

---

# PDF Manipulation

## Reading/Extracting

### Text Extraction with pdfplumber
```python
import pdfplumber

with pdfplumber.open('file.pdf') as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)

        # Extract tables
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)
```

### PyMuPDF (fitz) - Fast and Feature-rich
```python
import fitz  # PyMuPDF

doc = fitz.open('file.pdf')

for page in doc:
    # Get text
    text = page.get_text()

    # Get text with layout
    text = page.get_text("text")

    # Get images
    images = page.get_images()

    # Get links
    links = page.get_links()

doc.close()
```

### Extract to Structured Data
```python
import pdfplumber
import pandas as pd

with pdfplumber.open('file.pdf') as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            df = pd.DataFrame(table[1:], columns=table[0])
            all_tables.append(df)

    combined = pd.concat(all_tables, ignore_index=True)
```

---

## OCR for Scanned PDFs

### Prerequisites
```bash
# Install Tesseract OCR engine
# Windows: choco install tesseract
# Mac: brew install tesseract
# Linux: apt install tesseract-ocr

# Python dependencies
pip install pytesseract pdf2image Pillow
```

### Basic OCR Extraction
```python
import pytesseract
from pdf2image import convert_from_path

# Convert PDF pages to images
images = convert_from_path('scanned.pdf', dpi=300)

# OCR each page
text = ""
for i, image in enumerate(images):
    text += f"\n--- Page {i+1} ---\n"
    text += pytesseract.image_to_string(image)

print(text)
```

### OCR with Language Support
```python
# For non-English documents
text = pytesseract.image_to_string(image, lang='deu')  # German
text = pytesseract.image_to_string(image, lang='fra')  # French
text = pytesseract.image_to_string(image, lang='spa')  # Spanish

# Multiple languages
text = pytesseract.image_to_string(image, lang='eng+deu')
```

### OCR to Searchable PDF
```python
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Convert to images
images = convert_from_path('scanned.pdf', dpi=300)

# Create searchable PDF
pdf_bytes = pytesseract.image_to_pdf_or_hocr(images[0], extension='pdf')

with open('searchable.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

### Batch OCR with Progress
```python
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path

def ocr_pdf(pdf_path, output_path=None):
    """OCR a PDF and return text or save to file."""
    images = convert_from_path(pdf_path, dpi=300)

    all_text = []
    for i, image in enumerate(images):
        print(f"Processing page {i+1}/{len(images)}...")
        page_text = pytesseract.image_to_string(image)
        all_text.append(f"--- Page {i+1} ---\n{page_text}")

    full_text = "\n\n".join(all_text)

    if output_path:
        Path(output_path).write_text(full_text, encoding='utf-8')
        print(f"Saved to {output_path}")

    return full_text

# Usage
text = ocr_pdf('scanned.pdf', 'output.txt')
```

### OCR Quality Tips

1. **Use 300 DPI minimum** - Lower resolution = worse results
2. **Preprocess images** - Deskew, denoise, increase contrast
3. **Specify language** - Improves accuracy significantly
4. **Check orientation** - Use `--psm 1` for auto-rotate

```python
# Image preprocessing for better OCR
from PIL import Image, ImageEnhance, ImageFilter

def preprocess_for_ocr(image):
    # Convert to grayscale
    image = image.convert('L')

    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    # Sharpen
    image = image.filter(ImageFilter.SHARPEN)

    return image

# Apply preprocessing
images = convert_from_path('scanned.pdf', dpi=300)
for image in images:
    processed = preprocess_for_ocr(image)
    text = pytesseract.image_to_string(processed)
```

---

## Creating PDFs

### ReportLab - Programmatic Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

c = canvas.Canvas('output.pdf', pagesize=letter)

# Add text
c.setFont('Helvetica', 12)
c.drawString(1*inch, 10*inch, "Hello World")

# Add rectangle
c.rect(1*inch, 9*inch, 2*inch, 0.5*inch)

# Add image
c.drawImage('image.png', 1*inch, 7*inch, width=2*inch, height=2*inch)

# New page
c.showPage()

# Save
c.save()
```

### From HTML (WeasyPrint)
```python
from weasyprint import HTML

# From HTML string
HTML(string='<h1>Hello</h1><p>World</p>').write_pdf('output.pdf')

# From HTML file
HTML('report.html').write_pdf('output.pdf')

# From URL
HTML('http://example.com').write_pdf('output.pdf')
```

### From Markdown
```bash
# Using pandoc
pandoc input.md -o output.pdf

# With custom styling
pandoc input.md --pdf-engine=weasyprint -o output.pdf
```

## Merging/Splitting

> **Note**: Use `pypdf` (not PyPDF2). pypdf is the maintained fork.

### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()

# Append entire PDFs
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

### Split PDF (One Page Per File)
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")

for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

### Extract Page Range
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

# Pages 3-5 (0-indexed: 2, 3, 4)
for i in range(2, 5):
    writer.add_page(reader.pages[i])

with open("pages3-5.pdf", "wb") as output:
    writer.write(output)
```

### Extract Specific Pages
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

# Pages 1, 3, 5 (0-indexed: 0, 2, 4)
pages_to_extract = [0, 2, 4]
for page_num in pages_to_extract:
    writer.add_page(reader.pages[page_num])

with open("extracted.pdf", "wb") as output:
    writer.write(output)
```

### Extract Metadata
```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
meta = reader.metadata

print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
print(f"Pages: {len(reader.pages)}")
```

### Rotate Pages
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.rotate(90)  # 90° clockwise (use -90 for counter-clockwise)
    writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

## Form Filling

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("form.pdf")
writer = PdfWriter()

# Clone the form
writer.append(reader)

# Get form fields (inspect available fields)
fields = reader.get_fields()
for field_name, field_data in fields.items():
    print(f"{field_name}: {field_data}")

# Fill fields
writer.update_page_form_field_values(
    writer.pages[0],
    {
        "field_name": "value",
        "another_field": "another value",
        "checkbox_field": "/Yes"  # For checkboxes
    }
)

with open("filled.pdf", "wb") as output:
    writer.write(output)
```

### Flatten Form (Make Fields Uneditable)
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("filled.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Flatten all form fields
for page in writer.pages:
    for annot in page.get("/Annots", []):
        annot.update({"/Ff": 1})  # Read-only flag

with open("flattened.pdf", "wb") as output:
    writer.write(output)
```

## Annotations and Modifications

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
watermark = PdfReader("watermark.pdf")
writer = PdfWriter()

watermark_page = watermark.pages[0]

for page in reader.pages:
    page.merge_page(watermark_page)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Add Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Encrypt with user and owner passwords
writer.encrypt(
    user_password="userpass",      # Required to open
    owner_password="ownerpass",    # Required to edit
    permissions_flag=0b0100        # Restrict permissions
)

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

### Decrypt Password-Protected PDF
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("encrypted.pdf")

if reader.is_encrypted:
    reader.decrypt("password")

writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)

with open("decrypted.pdf", "wb") as output:
    writer.write(output)
```

## PDF to Images

```bash
# Using pdftoppm (poppler-utils)
pdftoppm -jpeg -r 150 input.pdf page

# Using ImageMagick
convert -density 150 input.pdf page-%03d.png
```

```python
# Using pdf2image
from pdf2image import convert_from_path

images = convert_from_path('input.pdf', dpi=150)
for i, image in enumerate(images):
    image.save(f'page_{i+1}.png', 'PNG')
```

---

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Basic text extraction
pdftotext input.pdf output.txt

# Preserve layout (columns, spacing)
pdftotext -layout input.pdf output.txt

# Extract specific pages (1-5)
pdftotext -f 1 -l 5 input.pdf output.txt

# Output to stdout
pdftotext input.pdf -
```

### qpdf (Swiss Army Knife)
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf file3.pdf -- merged.pdf

# Split: extract pages 1-5
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf

# Split: extract pages 6 to end
qpdf input.pdf --pages . 6-z -- pages6-end.pdf

# Split: every page to separate file
qpdf --split-pages input.pdf output-%d.pdf

# Rotate page 1 by 90 degrees clockwise
qpdf input.pdf output.pdf --rotate=+90:1

# Rotate all pages
qpdf input.pdf output.pdf --rotate=+90

# Decrypt (remove password)
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf

# Encrypt with passwords
qpdf --encrypt userpass ownerpass 256 -- input.pdf encrypted.pdf

# Linearize (optimize for web)
qpdf --linearize input.pdf web-optimized.pdf

# Check PDF validity
qpdf --check input.pdf
```

### pdftk (PDF Toolkit)
```bash
# Merge PDFs
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split into individual pages
pdftk input.pdf burst

# Extract pages 1-5
pdftk input.pdf cat 1-5 output pages1-5.pdf

# Rotate page 1 east (90° clockwise)
pdftk input.pdf rotate 1east output rotated.pdf

# Rotate all pages
pdftk input.pdf rotate 1-endeast output rotated.pdf

# Add background/watermark
pdftk input.pdf background watermark.pdf output watermarked.pdf

# Stamp (overlay)
pdftk input.pdf stamp stamp.pdf output stamped.pdf

# Get metadata
pdftk input.pdf dump_data output metadata.txt

# Fill form fields
pdftk form.pdf fill_form data.fdf output filled.pdf

# Flatten form (make fields uneditable)
pdftk filled.pdf output flat.pdf flatten
```

### pdfimages (poppler-utils)
```bash
# Extract all images as JPEG
pdfimages -j input.pdf output_prefix
# Creates: output_prefix-000.jpg, output_prefix-001.jpg, etc.

# Extract as PNG
pdfimages -png input.pdf output_prefix

# List images without extracting
pdfimages -list input.pdf
```

### gs (Ghostscript)
```bash
# Compress PDF (reduce file size)
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH -sOutputFile=compressed.pdf input.pdf

# Quality settings:
# /screen   - lowest quality, smallest size
# /ebook    - medium quality
# /printer  - high quality
# /prepress - highest quality

# Convert PDF to grayscale
gs -sDEVICE=pdfwrite -dProcessColorModel=/DeviceGray \
   -dColorConversionStrategy=/Gray -dNOPAUSE -dBATCH \
   -sOutputFile=grayscale.pdf input.pdf
```

### Batch Processing Scripts

```bash
#!/bin/bash
# Merge all PDFs in directory
qpdf --empty --pages *.pdf -- merged.pdf

# Convert all PDFs to text
for f in *.pdf; do
    pdftotext -layout "$f" "${f%.pdf}.txt"
done

# OCR all scanned PDFs (using ocrmypdf)
for f in *.pdf; do
    ocrmypdf "$f" "ocr_$f"
done
```

### ocrmypdf (Advanced OCR)
```bash
# Basic OCR (adds text layer, keeps original quality)
ocrmypdf input.pdf output.pdf

# Force OCR even if text exists
ocrmypdf --force-ocr input.pdf output.pdf

# Specify language
ocrmypdf -l deu input.pdf output.pdf  # German

# Clean up scanned pages (deskew, remove noise)
ocrmypdf --clean --deskew input.pdf output.pdf

# Optimize file size after OCR
ocrmypdf --optimize 3 input.pdf output.pdf

# Skip pages that already have text
ocrmypdf --skip-text input.pdf output.pdf
```

---

## ReportLab Tips

### Unicode Subscript/Superscript Warning

**IMPORTANT**: Never use Unicode subscript/superscript characters (₀₁₂₃₄₅₆₇₈₉, ⁰¹²³⁴⁵⁶⁷⁸⁹) in ReportLab PDFs. Built-in fonts don't include these glyphs - they render as black boxes.

**Use XML markup instead:**
```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()

# Subscripts: use <sub> tag
chemical = Paragraph("H<sub>2</sub>O", styles['Normal'])

# Superscripts: use <super> tag
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])

# Combined
formula = Paragraph("CO<sub>2</sub> at 10<super>6</super> ppm", styles['Normal'])
```

---

## Best Practices

### Library Selection
| Use Case | Best Tool |
|----------|-----------|
| Text/table extraction | pdfplumber |
| Fast reading, images | PyMuPDF (fitz) |
| PDF creation | ReportLab |
| Merge/split/forms | pypdf |
| HTML to PDF | WeasyPrint |
| CLI batch ops | qpdf |
| OCR | pytesseract + pdf2image or ocrmypdf |

### General Guidelines
1. Use `pypdf` (not PyPDF2) - it's the maintained fork
2. Always close files/documents when done
3. Use 300 DPI minimum for OCR
4. Handle encrypted PDFs with proper password handling
5. Validate output with `qpdf --check`
6. For large files, process page-by-page to save memory

---

*PDF Skill v2.0 | OCR + CLI Tools | pypdf, pdfplumber, qpdf, pytesseract*
