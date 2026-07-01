# Product Grouper

**Purpose:** Group extracted pieces by product type to enable product-by-product iteration workflow.

**Phase:** 1 (PDF Processing)

**Prerequisites:** `pdf-piece-parser.md` must run first to provide piece manifest

---

## When to Use

- After piece extraction completes
- To organize pieces for systematic placement
- Before family matching and placement workflow

---

## Input

```json
{
  "piece_manifest_path": ".claude/session/piece_manifest.json",
  "sort_by": "count_descending",  // Options: count_descending, alphabetical, sequence
  "parameter_mappings_path": ".claude/session/parameter-mappings.json"  // Optional
}
```

---

## Output: Product Groups

**File:** `.claude/session/product_groups.json`

```json
{
  "source_manifest": "piece_manifest.json",
  "grouped_at": "2026-01-30T10:55:00Z",
  "total_pieces": 182,
  "total_groups": 3,

  "groups": [
    {
      "group_id": 1,
      "product_prefix": "WP",
      "product_variant": "10\"",
      "description": "Wall Panels - 10\" Insulated",
      "piece_count": 158,
      "sort_order": 1,

      "common_dimensions": {
        "width": "10\"",
        "typical_depth": "12'-0\" to 20'-0\"",
        "typical_length": "18'-0\" to 24'-0\""
      },

      "discovered_family": "Insulated Wall Panel",
      "discovered_type": "10\" Type",

      "pieces": [
        {"mark": "WP-101", "grid": "A-1", "depth": "12'-0\"", "length": "20'-0\""},
        {"mark": "WP-102", "grid": "A-2", "depth": "12'-0\"", "length": "18'-6\""},
        // ... 156 more pieces
      ],

      "status": "pending",
      "placement_progress": 0
    },
    {
      "group_id": 2,
      "product_prefix": "WP",
      "product_variant": "8\"",
      "description": "Wall Panels - 8\" Solid",
      "piece_count": 16,
      "sort_order": 2,

      "common_dimensions": {
        "width": "8\"",
        "typical_depth": "10'-0\" to 15'-0\"",
        "typical_length": "16'-0\" to 20'-0\""
      },

      "discovered_family": "Solid Wall Panel",
      "discovered_type": "8\" Type",

      "pieces": [
        {"mark": "WP-201", "grid": "B-3", "depth": "10'-0\"", "length": "16'-0\""},
        // ... 15 more pieces
      ],

      "status": "pending",
      "placement_progress": 0
    },
    {
      "group_id": 3,
      "product_prefix": "C",
      "product_variant": "12x12",
      "description": "Columns - 12\"x12\"",
      "piece_count": 8,
      "sort_order": 3,

      "common_dimensions": {
        "width": "12\"",
        "depth": "12\"",
        "typical_height": "15'-0\" to 20'-0\""
      },

      "discovered_family": "Precast Column 12x12",
      "discovered_type": "Type A",

      "pieces": [
        {"mark": "C-1", "grid": "A-1", "height": "18'-0\""},
        {"mark": "C-2", "grid": "A-4", "height": "18'-0\""},
        // ... 6 more pieces
      ],

      "status": "pending",
      "placement_progress": 0
    }
  ],

  "iteration_order": [1, 2, 3]  // IDs in recommended processing order
}
```

---

## Grouping Algorithm

### Step 1: Parse Product Prefix and Variant

```python
def parse_product_info(piece):
    mark = piece["mark"]

    # Extract prefix (letters before dash or number)
    prefix_match = re.match(r"([A-Z]+)", mark)
    prefix = prefix_match.group(1) if prefix_match else "UNKNOWN"

    # Determine variant from dimensions
    variant = determine_variant(piece, prefix)

    return {
        "prefix": prefix,
        "variant": variant,
        "group_key": f"{prefix}-{variant}"
    }

def determine_variant(piece, prefix):
    dims = piece.get("dimensions", {})

    if prefix == "WP":
        # Wall panels: variant is thickness
        width = dims.get("width_in", dims.get("width", ""))
        if "10" in str(width):
            return "10\""
        elif "8" in str(width):
            return "8\""
        elif "12" in str(width):
            return "12\""
        else:
            return "unknown"

    elif prefix == "C":
        # Columns: variant is cross-section
        width = dims.get("width_in", "12")
        depth = dims.get("depth_in", "12")
        return f"{width}x{depth}"

    elif prefix == "DT":
        # Double tees: variant is depth x width
        depth = dims.get("depth_in", "24")
        width = dims.get("width_ft", "10")
        return f"{depth}x{width}"

    else:
        return "standard"
```

### Step 2: Group Pieces

```python
def group_pieces(pieces):
    groups = {}

    for piece in pieces:
        info = parse_product_info(piece)
        key = info["group_key"]

        if key not in groups:
            groups[key] = {
                "product_prefix": info["prefix"],
                "product_variant": info["variant"],
                "pieces": [],
                "dimensions": []
            }

        groups[key]["pieces"].append(piece)
        groups[key]["dimensions"].append(piece.get("dimensions", {}))

    # Calculate common dimensions per group
    for key, group in groups.items():
        group["common_dimensions"] = calculate_common_dims(group["dimensions"])
        group["piece_count"] = len(group["pieces"])

    return groups
```

### Step 3: Apply Discovered Mappings

```python
def apply_mappings(groups, mappings):
    for key, group in groups.items():
        prefix = group["product_prefix"]

        if prefix in mappings["product_types"]:
            mapping = mappings["product_types"][prefix]
            group["discovered_family"] = mapping.get("discovered_family")
            group["discovered_type"] = mapping.get("discovered_type")
        else:
            group["discovered_family"] = None
            group["discovered_type"] = None

    return groups
```

### Step 4: Sort Groups

```python
def sort_groups(groups, sort_by="count_descending"):
    group_list = list(groups.values())

    if sort_by == "count_descending":
        # Largest groups first (more efficient placement)
        group_list.sort(key=lambda g: g["piece_count"], reverse=True)
    elif sort_by == "alphabetical":
        # A-Z by prefix
        group_list.sort(key=lambda g: g["product_prefix"])
    elif sort_by == "sequence":
        # By first piece sequence number
        group_list.sort(key=lambda g: g["pieces"][0]["sequence"])

    # Assign sort order
    for i, group in enumerate(group_list):
        group["sort_order"] = i + 1
        group["group_id"] = i + 1

    return group_list
```

---

## Grouping Strategies

### By Count (Default)

Process largest groups first for efficiency. Good when:
- Similar product types have similar families
- Want to minimize your BIM tool transactions

```
Iteration Order:
1. WP-10" (158 pieces) - largest group first
2. WP-8" (16 pieces)
3. C-12x12 (8 pieces) - smallest last
```

### By Prefix

Process all of one product type before moving to next. Good when:
- Different products use different families
- Want to minimize family switching

```
Iteration Order:
1. C-12x12 (8 pieces) - columns first
2. WP-10" (158 pieces) - then wall panels
3. WP-8" (16 pieces)
```

### By Location

Process by grid area. Good when:
- Want visual progress across model
- Debugging placement issues in specific areas

```
Iteration Order:
1. Grid A pieces (45 total)
2. Grid B pieces (52 total)
3. Grid C pieces (48 total)
4. Grid D pieces (37 total)
```

---

## User Confirmation Output

```
PRODUCT GROUPING RESULTS
========================

Total Pieces: 182
Total Groups: 3

Processing Order (by piece count):

+-------+----------------+--------+---------------------------+
| Order | Product Type   | Count  | Discovered Family         |
+-------+----------------+--------+---------------------------+
|   1   | WP-10"         |  158   | Insulated Wall Panel      |
|   2   | WP-8"          |   16   | Solid Wall Panel          |
|   3   | C-12x12        |    8   | Precast Column 12x12      |
+-------+----------------+--------+---------------------------+

Grouping Details:

Group 1: WP-10" (158 pieces)
  Typical dimensions: 10" x 12'-0" to 20'-0" x 18'-0" to 24'-0"
  Grid distribution: A(40), B(45), C(40), D(33)
  Family: Insulated Wall Panel - 10" Type

Group 2: WP-8" (16 pieces)
  Typical dimensions: 8" x 10'-0" to 15'-0" x 16'-0" to 20'-0"
  Grid distribution: B(8), C(8)
  Family: Solid Wall Panel - 8" Type

Group 3: C-12x12 (8 pieces)
  Typical dimensions: 12"x12" x 15'-0" to 20'-0" height
  Grid distribution: A(2), B(2), C(2), D(2)
  Family: Precast Column 12x12 - Type A

Product groups saved to: .claude/session/product_groups.json

Begin product-by-product placement workflow? [Y/n]
```

---

## Workflow Integration

This skill outputs the data structure that drives the product-by-product iteration:

```
FOR each group IN product_groups.iteration_order:
    1. Load group data
    2. Run family-matcher.md for this group
    3. Present family-confirmation-ui.md
    4. User confirms family + parameters
    5. Run shape-builder.md (first group only)
    6. Run piece-placer.md for all pieces in group
    7. Run placement-validator.md
    8. Update group.status = "complete"
    9. Update group.placement_progress = 100%
NEXT group
```

---

## Integration Points

| Consumes | Produces |
|----------|----------|
| piece_manifest.json | product_groups.json |
| parameter-mappings.json (optional) | Iteration order |
| | Group-level metadata |

| Consumed By |
|-------------|
| `family-matcher.md` (per-group matching) |
| `builder` (orchestrates iteration) |
| `piece-placer.md` (places by group) |

---

## Related Skills

- `pdf-piece-parser.md` - Provides piece manifest
- `bim-parameter-discovery.md` - Provides family mappings
- `family-matcher.md` - Next step in workflow

---

**Skill Version:** 1.0.0
**Created:** 2026-01-30
**Phase:** 1 (PDF Processing)
