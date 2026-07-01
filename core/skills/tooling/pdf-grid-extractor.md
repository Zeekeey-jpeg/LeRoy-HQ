# PDF Grid Extractor

**Purpose:** Extract grid lines and their labels from construction PDF drawings to build a coordinate system.

**Phase:** 1 (PDF Processing)

**Performance Target:** <500ms/page (vector), <8s/page (OCR fallback)

---

## When to Use

- Processing precast construction drawings
- Building coordinate system for element placement
- First step in PDF-to-CAD automation workflow

---

## Input

```json
{
  "pdf_path": "C:/Projects/DC-2/DC-2-Progress-Drawings.pdf",
  "pages": [1, 2],  // Optional: specific pages, defaults to all
  "confidence_threshold": 0.85  // Optional: minimum confidence for grid detection
}
```

---

## Output: Grid Manifest

**File:** `.claude/session/grid_manifest.json`

```json
{
  "source_file": "DC-2-Progress-Drawings.pdf",
  "extracted_at": "2026-01-30T10:45:00Z",
  "extraction_method": "vector",  // or "ocr"
  "page_count": 2,

  "coordinate_system": {
    "origin": {"x": 0, "y": 0},
    "units": "feet",
    "scale": "1/4\" = 1'-0\""
  },

  "grids": {
    "vertical": [
      {"label": "A", "position": 0.0, "confidence": 0.98},
      {"label": "B", "position": 24.0, "confidence": 0.97},
      {"label": "C", "position": 48.0, "confidence": 0.99},
      {"label": "D", "position": 72.0, "confidence": 0.95}
    ],
    "horizontal": [
      {"label": "1", "position": 0.0, "confidence": 0.98},
      {"label": "2", "position": 20.0, "confidence": 0.96},
      {"label": "3", "position": 40.0, "confidence": 0.97},
      {"label": "4", "position": 60.0, "confidence": 0.98},
      {"label": "5", "position": 80.0, "confidence": 0.95},
      {"label": "6", "position": 100.0, "confidence": 0.96}
    ]
  },

  "validation": {
    "total_grids": 10,
    "high_confidence": 9,
    "low_confidence": 1,
    "warnings": ["Grid 5 low confidence - verify position"]
  }
}
```

---

## Extraction Algorithm

### Strategy 1: Vector Extraction (Primary)

Uses PyMuPDF to extract vector graphics directly from PDF.

```python
# Pseudocode - actual implementation in Python script
import fitz  # PyMuPDF

def extract_grids_vector(pdf_path, page_num):
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Get all paths (lines)
    paths = page.get_drawings()

    # Filter for long straight lines (grid candidates)
    grid_lines = []
    for path in paths:
        if is_straight_line(path) and is_long_enough(path, min_length=100):
            grid_lines.append(path)

    # Cluster parallel lines
    vertical_lines = [l for l in grid_lines if is_vertical(l)]
    horizontal_lines = [l for l in grid_lines if is_horizontal(l)]

    # Extract text annotations near line endpoints
    text_blocks = page.get_text("dict")["blocks"]

    # Match labels to lines
    for line in vertical_lines:
        label = find_nearest_label(line, text_blocks, direction="above")
        line["label"] = label

    for line in horizontal_lines:
        label = find_nearest_label(line, text_blocks, direction="left")
        line["label"] = label

    return {
        "vertical": vertical_lines,
        "horizontal": horizontal_lines
    }
```

**Grid Label Detection Patterns:**

| Pattern | Examples | Regex |
|---------|----------|-------|
| Alphabetic | A, B, C, AA, AB | `^[A-Z]{1,2}$` |
| Numeric | 1, 2, 3, 10, 11 | `^\d{1,2}$` |
| Alphanumeric | A1, B2, 1A | `^[A-Z]?\d{1,2}[A-Z]?$` |
| With suffix | A.1, B-2 | `^[A-Z][-.]?\d{1,2}$` |

---

### Strategy 2: OCR Fallback

When vector extraction fails (poor PDF quality, raster images):

```python
def extract_grids_ocr(pdf_path, page_num):
    # Convert page to image
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Use OpenCV for line detection
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100,
                           minLineLength=200, maxLineGap=10)

    # Use Tesseract for label detection
    text_data = pytesseract.image_to_data(img, output_type=Output.DICT)

    # Match labels to detected lines
    # ... (similar to vector approach)

    return grids
```

---

## Validation Gates

### Gate 1: Grid Count Sanity

```python
def validate_grid_count(grids):
    v_count = len(grids["vertical"])
    h_count = len(grids["horizontal"])

    # Typical precast drawings have 3-10 grids per direction
    if v_count < 2 or v_count > 20:
        return {"valid": False, "error": f"Unusual vertical grid count: {v_count}"}
    if h_count < 2 or h_count > 20:
        return {"valid": False, "error": f"Unusual horizontal grid count: {h_count}"}

    return {"valid": True}
```

### Gate 2: Grid Spacing Consistency

```python
def validate_spacing(grids):
    # Check that grid spacing is reasonably consistent
    v_positions = [g["position"] for g in grids["vertical"]]
    v_spacings = [v_positions[i+1] - v_positions[i] for i in range(len(v_positions)-1)]

    # Flag if spacing varies by more than 50%
    avg_spacing = sum(v_spacings) / len(v_spacings)
    for spacing in v_spacings:
        if abs(spacing - avg_spacing) / avg_spacing > 0.5:
            return {"valid": False, "warning": "Inconsistent grid spacing detected"}

    return {"valid": True}
```

### Gate 3: Label Sequence

```python
def validate_labels(grids):
    # Check alphabetic sequence (A, B, C, D)
    v_labels = [g["label"] for g in grids["vertical"]]
    expected = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:len(v_labels)]
    if v_labels != expected:
        return {"valid": False, "warning": f"Non-sequential labels: {v_labels}"}

    # Check numeric sequence (1, 2, 3, 4, 5, 6)
    h_labels = [g["label"] for g in grids["horizontal"]]
    expected = [str(i) for i in range(1, len(h_labels)+1)]
    if h_labels != expected:
        return {"valid": False, "warning": f"Non-sequential labels: {h_labels}"}

    return {"valid": True}
```

---

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| "No grids detected" | Poor PDF quality or no grids on page | Try OCR fallback, prompt user for manual entry |
| "Low confidence extraction" | Ambiguous grid lines | Mark low-confidence grids for user review |
| "Missing labels" | Labels not detected | Use default sequence (A, B, C...) with warning |
| "File not found" | Invalid path | Return clear error message |

---

## Performance Benchmarks

| Operation | Vector | OCR |
|-----------|--------|-----|
| Page load | 50ms | 50ms |
| Line extraction | 100ms | 2000ms |
| Text extraction | 100ms | 3000ms |
| Label matching | 50ms | 500ms |
| **Total per page** | **300ms** | **5500ms** |

---

## Integration Points

| Consumes | Produces |
|----------|----------|
| PDF file path | grid_manifest.json |
| Page range (optional) | Coordinate system |
| | Grid labels + positions |

| Consumed By |
|-------------|
| `pdf-piece-parser.md` (uses grid coordinate system) |
| `shape-builder.md` (creates grids in your BIM tool) |

---

## User Confirmation Output

```
GRID EXTRACTION RESULTS
=======================

Source: DC-2-Progress-Drawings.pdf (pages 1-2)
Method: Vector extraction
Confidence: 98%

Vertical Grids (4):
  A -------- 0'-0"    (confidence: 98%)
  B -------- 24'-0"   (confidence: 97%)
  C -------- 48'-0"   (confidence: 99%)
  D -------- 72'-0"   (confidence: 95%)

Horizontal Grids (6):
  1 -------- 0'-0"    (confidence: 98%)
  2 -------- 20'-0"   (confidence: 96%)
  3 -------- 40'-0"   (confidence: 97%)
  4 -------- 60'-0"   (confidence: 98%)
  5 -------- 80'-0"   (confidence: 95%)  [!] LOW CONFIDENCE
  6 -------- 100'-0"  (confidence: 96%)

Grid manifest saved to: .claude/session/grid_manifest.json

Proceed to piece extraction? [Y/n]
```

---

## CRITICAL: Unit Conversion (CAD to your tool)

**Pattern Reference:** `memory/Patterns/CAD-unit-conversion.md`

### The Problem

CAD drawings display dimensions in **architectural units** (feet-inches-fractions):
- `1'-10 1/8"` on the drawing

your app's API requires **decimal feet**:
- `1.843750` for your BIM connector commands

PDF extraction produces **pixel coordinates**:
- `185` pixels between grids

**All three must be reconciled before grid creation.**

---

### Architectural Unit Parser

```python
import re

def parse_architectural_to_decimal(dimension_str: str) -> float:
    """
    Convert architectural dimension string to decimal feet.

    Examples:
      1'-10 1/8"  -> 1.843750
      24'-0"      -> 24.000000
      0'-6 1/2"   -> 0.541667
    """
    s = dimension_str.strip().upper().replace('"', '').replace("''", "'")

    feet = 0.0
    inches = 0.0
    fraction = 0.0

    pattern = r"^(\d+)'?\s*[-\s]?\s*(\d+(?:\.\d+)?)?(?:\s+(\d+)/(\d+))?"
    match = re.match(pattern, s)

    if match:
        feet = float(match.group(1)) if match.group(1) else 0.0
        if match.group(2):
            inches = float(match.group(2))
        if match.group(3) and match.group(4):
            fraction = float(match.group(3)) / float(match.group(4))

    decimal_feet = feet + (inches / 12.0) + (fraction / 12.0)
    return round(decimal_feet, 6)
```

---

### Scale Factor Calibration (MANDATORY)

**Before finalizing grid manifest, MUST calibrate scale:**

1. User provides one known dimension from CAD: `"F to G is 1'-10 1/8\""`
2. Parse to decimal feet: `1.843750`
3. Measure pixel distance between F and G: `185 pixels`
4. Calculate scale: `1.843750 / 185 = 0.009966 feet/pixel`
5. Apply scale to all grid positions

```python
def calibrate_grid_manifest(manifest, from_grid, to_grid, known_dimension_str):
    """
    Calibrate grid positions using known CAD dimension.
    """
    known_feet = parse_architectural_to_decimal(known_dimension_str)

    # Find grids
    all_grids = manifest["grids"]["vertical"] + manifest["grids"]["horizontal"]
    from_g = next((g for g in all_grids if g["label"] == from_grid), None)
    to_g = next((g for g in all_grids if g["label"] == to_grid), None)

    if not from_g or not to_g:
        raise ValueError(f"Grid {from_grid} or {to_grid} not found")

    # Calculate scale factor
    pixel_distance = abs(to_g["position"] - from_g["position"])
    scale_factor = known_feet / pixel_distance

    # Apply to all grids
    for grid in manifest["grids"]["vertical"]:
        grid["position"] = round(grid["position"] * scale_factor, 6)
    for grid in manifest["grids"]["horizontal"]:
        grid["position"] = round(grid["position"] * scale_factor, 6)

    # Record calibration
    manifest["coordinate_system"]["units"] = "decimal_feet"
    manifest["coordinate_system"]["scale_factor"] = scale_factor
    manifest["coordinate_system"]["calibration"] = {
        "from_grid": from_grid,
        "to_grid": to_grid,
        "known_dimension": known_dimension_str,
        "known_decimal": known_feet
    }

    return manifest
```

---

### User Prompt for Calibration

```
SCALE CALIBRATION REQUIRED
==========================

I've extracted grid lines from the PDF. To ensure correct spacing,
please provide ONE known dimension from the CAD drawing.

Format: "[Grid] to [Grid] is [dimension]"

Examples:
  - "F to G is 1'-10 1/8\""
  - "A to B is 24'-0\""

Your input:
```

---

### Updated Output Format

```json
{
  "coordinate_system": {
    "origin": {"x": 0, "y": 0},
    "units": "decimal_feet",
    "scale_factor": 0.009966,
    "calibration": {
      "from_grid": "F",
      "to_grid": "G",
      "known_dimension": "1'-10 1/8\"",
      "known_decimal": 1.843750
    }
  },
  "grids": {
    "vertical": [
      {"label": "A", "position": 0.000000, "confidence": 0.98},
      {"label": "B", "position": 24.000000, "confidence": 0.97}
    ]
  }
}
```

---

### Validation Gate

**MUST run `grid-spacing-validator.md` before proceeding to grid creation.**

---

## Related Skills

- `pdf-piece-parser.md` - Uses grid manifest to locate pieces
- `shape-builder.md` - Creates grids in your BIM tool from manifest
- `grid-spacing-validator.md` - Validates scale factor (MANDATORY)
- `pdf.md` - General PDF processing patterns
- `memory/Patterns/CAD-unit-conversion.md` - Conversion formulas

---

**Skill Version:** 1.1.0
**Created:** 2026-01-30
**Updated:** 2026-01-31 (Added architectural unit parsing and scale calibration)
**Phase:** 1 (PDF Processing)
