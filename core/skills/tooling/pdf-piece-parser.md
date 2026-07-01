# PDF Piece Parser

**Purpose:** Extract piece callouts (marks) from construction PDF drawings and associate them with grid locations.

**Phase:** 1 (PDF Processing)

**Prerequisites:** `pdf-grid-extractor.md` must run first to provide coordinate system

---

## When to Use

- After grid extraction completes
- To identify all precast pieces in construction drawings
- Building piece manifest for family matching

---

## Input

```json
{
  "pdf_path": "C:/Projects/DC-2/DC-2-Progress-Drawings.pdf",
  "grid_manifest_path": ".claude/session/grid_manifest.json",
  "pages": [1, 2],  // Optional: specific pages
  "piece_patterns": ["WP-\\d+", "C-\\d+"]  // Optional: custom regex patterns
}
```

---

## Output: Piece Manifest

**File:** `.claude/session/piece_manifest.json`

```json
{
  "source_file": "DC-2-Progress-Drawings.pdf",
  "extracted_at": "2026-01-30T10:50:00Z",
  "grid_manifest": "grid_manifest.json",

  "pieces": [
    {
      "mark": "WP-101",
      "product_prefix": "WP",
      "sequence": 101,
      "location": {
        "grid_intersection": {"vertical": "A", "horizontal": "1"},
        "position": {"x": 0.0, "y": 0.0},
        "offset": {"x": 0.5, "y": 0.0}
      },
      "dimensions": {
        "width": "10\"",
        "depth": "12'-0\"",
        "length": "20'-0\""
      },
      "page": 1,
      "confidence": 0.95,
      "bounding_box": {"x1": 100, "y1": 200, "x2": 300, "y2": 400}
    },
    {
      "mark": "WP-102",
      "product_prefix": "WP",
      "sequence": 102,
      "location": {
        "grid_intersection": {"vertical": "A", "horizontal": "2"},
        "position": {"x": 0.0, "y": 20.0},
        "offset": {"x": 0.5, "y": 0.0}
      },
      "dimensions": {
        "width": "10\"",
        "depth": "12'-0\"",
        "length": "18'-6\""
      },
      "page": 1,
      "confidence": 0.92
    }
    // ... more pieces
  ],

  "summary": {
    "total_pieces": 182,
    "by_prefix": {
      "WP": 174,
      "C": 8
    },
    "high_confidence": 175,
    "low_confidence": 7
  },

  "validation": {
    "duplicate_marks": [],
    "missing_dimensions": ["WP-156", "WP-157"],
    "uncertain_locations": ["C-7", "C-8"]
  }
}
```

---

## Extraction Algorithm

### Step 1: Load Grid Coordinate System

```python
def load_grid_system(manifest_path):
    with open(manifest_path) as f:
        manifest = json.load(f)

    # Build lookup functions
    def x_from_grid(label):
        for grid in manifest["grids"]["vertical"]:
            if grid["label"] == label:
                return grid["position"]
        return None

    def y_from_grid(label):
        for grid in manifest["grids"]["horizontal"]:
            if grid["label"] == label:
                return grid["position"]
        return None

    return {"x_lookup": x_from_grid, "y_lookup": y_from_grid}
```

### Step 2: Detect Piece Marks

**Standard Precast Mark Patterns:**

| Prefix | Pattern | Examples | Product Type |
|--------|---------|----------|--------------|
| WP | `WP-\d{2,3}` | WP-101, WP-02 | Wall Panels (insulated/solid) |
| C | `C-\d{1,2}` | C-1, C-12 | Columns |
| B | `B-\d{2,3}` | B-01, B-101 | Beams |
| J | `J-\d{2,3}` | J-001, J-102 | Joists |
| DT | `DT-\d{2,3}` | DT-01, DT-50 | Double Tees |
| H | `H-\d{2,3}` | H-01, H-24 | Hollowcore |

```python
def extract_piece_marks(page, patterns=None):
    if patterns is None:
        patterns = [
            r"WP-\d{2,3}",
            r"C-\d{1,2}",
            r"B-\d{2,3}",
            r"J-\d{2,3}",
            r"DT-\d{2,3}",
            r"H-\d{2,3}"
        ]

    text_blocks = page.get_text("dict")["blocks"]
    pieces = []

    for block in text_blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                for pattern in patterns:
                    match = re.match(pattern, text, re.IGNORECASE)
                    if match:
                        pieces.append({
                            "mark": match.group().upper(),
                            "bbox": span["bbox"],
                            "page_position": {
                                "x": (span["bbox"][0] + span["bbox"][2]) / 2,
                                "y": (span["bbox"][1] + span["bbox"][3]) / 2
                            }
                        })

    return pieces
```

### Step 3: Associate Pieces with Grids

```python
def associate_with_grids(pieces, grids, page_scale):
    for piece in pieces:
        # Convert page coordinates to model coordinates
        model_x = piece["page_position"]["x"] * page_scale
        model_y = piece["page_position"]["y"] * page_scale

        # Find nearest grid intersection
        nearest_v = find_nearest_grid(model_x, grids["vertical"])
        nearest_h = find_nearest_grid(model_y, grids["horizontal"])

        piece["location"] = {
            "grid_intersection": {
                "vertical": nearest_v["label"],
                "horizontal": nearest_h["label"]
            },
            "position": {
                "x": nearest_v["position"],
                "y": nearest_h["position"]
            },
            "offset": {
                "x": model_x - nearest_v["position"],
                "y": model_y - nearest_h["position"]
            }
        }

    return pieces
```

### Step 4: Extract Nearby Dimensions

```python
def extract_dimensions(piece, page):
    # Look for dimension text near the piece mark
    search_radius = 100  # pixels
    nearby_text = find_text_near(page, piece["bbox"], search_radius)

    dimensions = {}
    dimension_patterns = [
        (r"(\d+)\"", "width_in"),           # 10"
        (r"(\d+'-\d+\")", "length_ft_in"),  # 20'-0"
        (r"(\d+)'-(\d+)\"", "depth_ft_in")  # 12'-6"
    ]

    for text in nearby_text:
        for pattern, dim_type in dimension_patterns:
            match = re.search(pattern, text)
            if match:
                dimensions[dim_type] = match.group()

    piece["dimensions"] = dimensions
    return piece
```

---

## Validation Gates

### Gate 1: Duplicate Mark Detection

```python
def check_duplicates(pieces):
    marks = [p["mark"] for p in pieces]
    duplicates = [m for m in marks if marks.count(m) > 1]
    return {
        "valid": len(duplicates) == 0,
        "duplicates": list(set(duplicates))
    }
```

### Gate 2: Sequence Gaps

```python
def check_sequence(pieces, prefix):
    prefix_pieces = [p for p in pieces if p["product_prefix"] == prefix]
    sequences = sorted([p["sequence"] for p in prefix_pieces])

    gaps = []
    for i in range(len(sequences) - 1):
        if sequences[i+1] - sequences[i] > 1:
            gaps.append((sequences[i], sequences[i+1]))

    return {
        "valid": len(gaps) == 0,
        "gaps": gaps
    }
```

### Gate 3: Missing Dimensions

```python
def check_dimensions(pieces):
    missing = []
    for piece in pieces:
        if not piece.get("dimensions"):
            missing.append(piece["mark"])
        elif len(piece["dimensions"]) < 2:
            missing.append(piece["mark"])

    return {
        "valid": len(missing) == 0,
        "missing": missing
    }
```

---

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| "No pieces found" | Wrong page or no marks on page | Check page selection, verify PDF content |
| "Duplicate marks" | Same mark appears multiple times | Flag for user review |
| "Missing dimensions" | Dimensions not found near mark | Use default dimensions or prompt user |
| "Uncertain location" | Piece far from any grid | Flag for user review |

---

## Performance

| Operation | Time |
|-----------|------|
| Page text extraction | 100ms |
| Mark detection | 50ms |
| Grid association | 50ms |
| Dimension extraction | 100ms |
| **Total per page** | **300ms** |
| **Total (DC-2, 2 pages)** | **<1s** |

---

## User Confirmation Output

```
PIECE EXTRACTION RESULTS
========================

Source: DC-2-Progress-Drawings.pdf
Grid System: grid_manifest.json (4 vertical, 6 horizontal grids)

Total Pieces Found: 182

By Product Type:
  WP (Wall Panels): 174
    - WP-10" Insulated: 158
    - WP-8" Solid: 16
  C (Columns): 8
    - C-12x12: 8

Location Summary:
  Grid A: 45 pieces
  Grid B: 52 pieces
  Grid C: 48 pieces
  Grid D: 37 pieces

Validation Warnings:
  - 2 pieces missing dimensions: WP-156, WP-157
  - 2 pieces uncertain location: C-7, C-8

Piece manifest saved to: .claude/session/piece_manifest.json

Proceed to product grouping? [Y/n]
```

---

## Integration Points

| Consumes | Produces |
|----------|----------|
| PDF file path | piece_manifest.json |
| grid_manifest.json | Piece locations |
| | Piece dimensions |

| Consumed By |
|-------------|
| `product-grouper.md` (groups pieces by type) |
| `family-matcher.md` (matches pieces to families) |

---

## Related Skills

- `pdf-grid-extractor.md` - Provides coordinate system
- `product-grouper.md` - Groups pieces for iteration
- `pdf.md` - General PDF processing

---

**Skill Version:** 1.0.0
**Created:** 2026-01-30
**Phase:** 1 (PDF Processing)
