#!/usr/bin/env python3
"""
OutreachBot CRM Engagement Scorer

Scores prior CRM warm-engagement behavior for a contact/company on a 0-25 scale,
combining email engagement (opens/clicks/replies) with deal stage. Standalone CLI /
importable module for OutreachBot automation -- not part of the larger 0-100
warmth-scorer system described in memory/Projects/OutreachBot/warmth-scorer-spec.md
(this script ports and rescales that spec's signal #7 logic, and additionally folds
in deal stage, which signal #7 did not cover).

Usage:
    python OutreachBot-engagement-score.py --contact-id 12345
    python OutreachBot-engagement-score.py --company-id 67890 --json
    python OutreachBot-engagement-score.py --contact-id 12345 --company-id 67890 --stage-map-file stage_map.json

Importable:
    from importlib import import_module
    scorer = import_module("OutreachBot-engagement-score")
    result = scorer.score_engagement(contact_id="12345", company_id="67890")
"""

import argparse
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# Config
# ============================================================================

CONTACT_PROPERTIES = [
    "firstname",
    "lastname",
    "email",
    "hs_email_open",
    "hs_email_click",
    "hs_sales_email_last_replied",
    "notes_last_contacted",
    "num_contacted_notes",
]

COMPANY_PROPERTIES = [
    "name",
    "domain",
    "hs_lastmodifieddate",
]

DEAL_PROPERTIES = [
    "dealname",
    "dealstage",
    "amount",
    "closedate",
    "hs_lastmodifieddate",
]

# Component A (engagement behavior) point values -- max 18
POINTS_REPLY = 18
POINTS_CLICK = 13
POINTS_OPENS_3_PLUS = 8
POINTS_OPENS_1_2 = 4
POINTS_CONTACT_LOGGED_FALLBACK = 2
POINTS_NO_ENGAGEMENT = 0

# Component B (deal stage) point values -- max 7
POINTS_CLOSED_WON = 7
POINTS_OPEN_LATE = 5
POINTS_OPEN_UNCLASSIFIED = 3
POINTS_NO_DEAL = 0

MAX_TOTAL_SCORE = 25

BAND_THRESHOLDS = (
    (17, "Warm"),
    (8, "Lukewarm"),
    (0, "Cold"),
)


# ============================================================================
# MCP invocation (mirrors scripts/CRM-leadership-report.py's run_mcp_command)
# ============================================================================

def run_mcp_command(tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Execute an MCP tool via `mcp call-tool CRM <tool_name> <json-args>` and return
    the parsed JSON result. Unlike CRM-leadership-report.py's version, this NEVER
    raises or exits the process on failure -- any subprocess error, non-zero exit, or
    malformed JSON is logged to stderr and treated as "no data" (returns None) so a
    single flaky/missing CRM record can't crash the whole engagement score. This
    mirrors the "neutral fallback, don't crash" note in warmth-scorer-spec.md.
    """
    cmd = ["mcp", "call-tool", "CRM", tool_name, json.dumps(arguments)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"[warn] Failed to launch MCP command for {tool_name}: {exc}", file=sys.stderr)
        return None

    if result.returncode != 0:
        stderr_snippet = (result.stderr or "").strip()
        print(f"[warn] MCP command '{tool_name}' exited {result.returncode}: {stderr_snippet}", file=sys.stderr)
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"[warn] Could not parse JSON from '{tool_name}': {exc}", file=sys.stderr)
        return None


def fetch_contact(contact_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a CRM contact. Returns None (not an exception) if unavailable."""
    return run_mcp_command(
        "hubspot_get_contact",
        {"contactId": contact_id, "properties": CONTACT_PROPERTIES},
    )


def fetch_company(company_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a CRM company. Returns None (not an exception) if unavailable."""
    return run_mcp_command(
        "hubspot_get_company",
        {"companyId": company_id, "properties": COMPANY_PROPERTIES},
    )


def fetch_associated_deal_ids(object_type: str, object_id: str) -> List[str]:
    """
    Look up deal IDs associated with a contact or company via hubspot_get_associations.
    object_type must be "contacts" or "companies" (the CRM MCP's ObjectTypeSchema).
    Returns an empty list on any failure or when no associations exist -- never raises.
    """
    response = run_mcp_command(
        "hubspot_get_associations",
        {"objectType": object_type, "objectId": object_id, "toObjectType": "deals"},
    )
    if not response or "results" not in response:
        return []
    deal_ids = []
    for item in response["results"]:
        deal_id = item.get("id") or item.get("toObjectId")
        if deal_id:
            deal_ids.append(str(deal_id))
    return deal_ids


def fetch_deal(deal_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single CRM deal. Returns None (not an exception) if unavailable."""
    return run_mcp_command(
        "hubspot_get_deal",
        {"dealId": deal_id, "properties": DEAL_PROPERTIES},
    )


# ============================================================================
# Helpers
# ============================================================================

def safe_int(value: Any) -> int:
    """Parse a CRM numeric property (often a string or None) into an int, defaulting to 0."""
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def is_present(value: Any) -> bool:
    """CRM returns absent/empty properties as None or "" -- treat both as absent."""
    return value is not None and str(value).strip() != ""


# ============================================================================
# Component A: Engagement behavior (max 18, + up to 2 fallback = capped at 18)
# ============================================================================

def score_engagement_behavior(contact_properties: Dict[str, Any]) -> Tuple[int, str]:
    """
    Score email engagement behavior from contact properties. Ports the sub-score
    ordering from warmth-scorer-spec.md signal #7 (reply > click > 3+ opens > 1-2
    opens > none), rescaled from that spec's 0-1 normalized sub-score to this
    script's 0-18 point range, with an added weak fallback signal (notes_last_contacted
    / num_contacted_notes) for records where no email-engagement fields are populated
    at all -- per the CRM data-completeness audit, these fields are only
    37-95% populated across records, so missing must mean "no signal", not an error.
    """
    open_count = safe_int(contact_properties.get("hs_email_open"))
    click_count = safe_int(contact_properties.get("hs_email_click"))
    replied = is_present(contact_properties.get("hs_sales_email_last_replied"))

    if replied:
        return POINTS_REPLY, "reply_received"
    if click_count >= 1:
        return POINTS_CLICK, "click_present_no_reply"
    if open_count >= 3:
        return POINTS_OPENS_3_PLUS, "3_plus_opens_no_click_no_reply"
    if open_count >= 1:
        return POINTS_OPENS_1_2, "1_to_2_opens_no_click_no_reply"

    # No email-engagement data at all -- fall back to a weak "contact logged" signal.
    notes_last_contacted = is_present(contact_properties.get("notes_last_contacted"))
    num_contacted_notes = safe_int(contact_properties.get("num_contacted_notes"))
    if notes_last_contacted or num_contacted_notes > 0:
        return POINTS_CONTACT_LOGGED_FALLBACK, "contact_logged_no_email_engagement_data"

    return POINTS_NO_ENGAGEMENT, "no_engagement_data"


# ============================================================================
# Component B: Deal stage (max 7)
# ============================================================================

def classify_deal(dealstage: str, stage_map: Optional[Dict[str, str]]) -> Tuple[int, str]:
    """
    Classify a single deal's stage into a point value + reason code.

    IMPORTANT LIMITATION: CRM dealstage values are opaque, pipeline-specific
    internal IDs (see STAGE_5_ID / STAGE_6_ID / CLOSED_WON_ID in
    scripts/CRM-leadership-report.py for how this repo already treats them as
    opaque strings rather than human labels). This function does NOT hardcode this
    repo's specific stage IDs. Classification works as follows:
      1. If the stage string case-insensitively contains both "closed" and "won"
         (CRM's default pipeline labels stages this way), it's Closed Won.
      2. Else if it contains "closed" (without "won"), treat as closed-lost/other
         and award 0 -- a closed-lost deal is not a live warmth signal.
      3. Else if the caller supplied a stage_map (dict of dealstage-id -> "early"/
         "late", loaded via --stage-map-file), look up the bucket for precise
         early/late classification.
      4. Otherwise, default to a neutral "has an open deal, stage unclassifiable"
         signal (3 points) -- this is a deliberate default, not an oversight, since
         without a stage_map this script cannot know this pipeline's stage ordering.
    """
    stage = (dealstage or "").strip()
    stage_lower = stage.lower()

    if "closed" in stage_lower and "won" in stage_lower:
        return POINTS_CLOSED_WON, "closed_won"
    if "closed" in stage_lower:
        return POINTS_NO_DEAL, "closed_lost_or_other_not_won"

    if stage_map and stage in stage_map:
        bucket = stage_map[stage]
        if bucket == "late":
            return POINTS_OPEN_LATE, "open_late_stage_mapped"
        if bucket == "early":
            return POINTS_OPEN_UNCLASSIFIED, "open_early_stage_mapped"

    return POINTS_OPEN_UNCLASSIFIED, "open_unclassified_stage"


def score_deal_stage(
    deals: List[Dict[str, Any]], stage_map: Optional[Dict[str, str]]
) -> Tuple[int, str, Optional[str]]:
    """
    Score the deal-stage component from a list of fetched deal records. When multiple
    deals are associated, the BEST (highest-scoring) classifiable deal wins -- e.g. a
    closed-won deal outranks a stale open deal, even if the open deal was touched more
    recently. Returns (points, reason, deal_id_used_for_the_score).
    """
    if not deals:
        return POINTS_NO_DEAL, "no_deal_found", None

    best_points = -1
    best_reason = "no_deal_found"
    best_deal_id = None

    for deal in deals:
        if not deal:
            continue
        properties = deal.get("properties", {}) or {}
        points, reason = classify_deal(properties.get("dealstage", ""), stage_map)
        if points > best_points:
            best_points = points
            best_reason = reason
            best_deal_id = deal.get("id")

    if best_points < 0:
        # All fetched deal records were None/unusable -- treat as no deal found.
        return POINTS_NO_DEAL, "no_deal_found", None

    return best_points, best_reason, best_deal_id


# ============================================================================
# Band mapping
# ============================================================================

def score_to_band(score: int) -> str:
    for threshold, band in BAND_THRESHOLDS:
        if score >= threshold:
            return band
    return "Cold"


# ============================================================================
# Main entry point
# ============================================================================

def score_engagement(
    contact_id: Optional[str] = None,
    company_id: Optional[str] = None,
    stage_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Score prior CRM warm engagement for a contact and/or company on a 0-25 scale.

    At least one of contact_id / company_id should be provided. If only one is given,
    the other's contribution to the deal-associations lookup is skipped gracefully
    (fewer deal IDs to check, not an error).

    Returns:
        {
            "score": int,               # 0-25
            "band": str,                # "Cold" | "Lukewarm" | "Warm"
            "breakdown": {
                "engagement_points": int,
                "engagement_reason": str,
                "deal_points": int,
                "deal_reason": str,
                "deal_id_used": str | None,
            },
            "signals_used": { ...raw property values that fed the score... },
        }
    """
    contact_properties: Dict[str, Any] = {}
    company_properties: Dict[str, Any] = {}
    company_name: Optional[str] = None

    if contact_id:
        contact = fetch_contact(contact_id)
        if contact:
            contact_properties = contact.get("properties", {}) or {}
        else:
            print(f"[warn] No contact record for contact_id={contact_id}; treating engagement signals as absent.", file=sys.stderr)

    if company_id:
        company = fetch_company(company_id)
        if company:
            company_properties = company.get("properties", {}) or {}
            company_name = company_properties.get("name")
        else:
            print(f"[warn] No company record for company_id={company_id}; treating company context as absent.", file=sys.stderr)

    # Gather associated deal IDs from whichever of contact/company was provided.
    deal_ids: List[str] = []
    if contact_id:
        deal_ids.extend(fetch_associated_deal_ids("contacts", contact_id))
    if company_id:
        deal_ids.extend(fetch_associated_deal_ids("companies", company_id))
    deal_ids = sorted(set(deal_ids))

    deals: List[Dict[str, Any]] = []
    for deal_id in deal_ids:
        deal = fetch_deal(deal_id)
        if deal:
            deals.append(deal)
        else:
            print(f"[warn] Could not fetch deal_id={deal_id}; excluding from deal-stage scoring.", file=sys.stderr)

    engagement_points, engagement_reason = score_engagement_behavior(contact_properties)
    deal_points, deal_reason, deal_id_used = score_deal_stage(deals, stage_map)

    total_score = min(MAX_TOTAL_SCORE, engagement_points + deal_points)
    band = score_to_band(total_score)

    return {
        "score": total_score,
        "band": band,
        "breakdown": {
            "engagement_points": engagement_points,
            "engagement_reason": engagement_reason,
            "deal_points": deal_points,
            "deal_reason": deal_reason,
            "deal_id_used": deal_id_used,
        },
        "signals_used": {
            "contact_id": contact_id,
            "company_id": company_id,
            "company_name": company_name,
            "hs_email_open": contact_properties.get("hs_email_open"),
            "hs_email_click": contact_properties.get("hs_email_click"),
            "hs_sales_email_last_replied": contact_properties.get("hs_sales_email_last_replied"),
            "notes_last_contacted": contact_properties.get("notes_last_contacted"),
            "num_contacted_notes": contact_properties.get("num_contacted_notes"),
            "deal_ids_checked": deal_ids,
            "deals_fetched_count": len(deals),
        },
    }


# ============================================================================
# CLI
# ============================================================================

def print_human_summary(result: Dict[str, Any]) -> None:
    breakdown = result["breakdown"]
    signals = result["signals_used"]

    print("=" * 60)
    print("OutreachBot ENGAGEMENT SCORE")
    print("=" * 60)
    if signals.get("company_name"):
        print(f"Company: {signals['company_name']}")
    if signals.get("contact_id"):
        print(f"Contact ID: {signals['contact_id']}")
    if signals.get("company_id"):
        print(f"Company ID: {signals['company_id']}")
    print("-" * 60)
    print(f"Score: {result['score']} / 25")
    print(f"Band:  {result['band']}")
    print("-" * 60)
    print("Breakdown:")
    print(f"  Engagement behavior: {breakdown['engagement_points']} / 18  ({breakdown['engagement_reason']})")
    print(f"  Deal stage:          {breakdown['deal_points']} / 7   ({breakdown['deal_reason']})")
    if breakdown.get("deal_id_used"):
        print(f"  Deal used for score: {breakdown['deal_id_used']}")
    print("-" * 60)
    print("Raw signals:")
    print(f"  hs_email_open: {signals.get('hs_email_open')}")
    print(f"  hs_email_click: {signals.get('hs_email_click')}")
    print(f"  hs_sales_email_last_replied: {signals.get('hs_sales_email_last_replied')}")
    print(f"  notes_last_contacted: {signals.get('notes_last_contacted')}")
    print(f"  num_contacted_notes: {signals.get('num_contacted_notes')}")
    print(f"  deal_ids_checked: {signals.get('deal_ids_checked')}")
    print("=" * 60)


def load_stage_map(path: Optional[str]) -> Optional[Dict[str, str]]:
    """Load an optional {dealstage_id: 'early'|'late'} mapping from a JSON file."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        print(f"[warn] Stage map file {path} did not contain a JSON object; ignoring.", file=sys.stderr)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[warn] Could not load stage map file {path}: {exc}", file=sys.stderr)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score prior CRM warm engagement (opens/clicks/replies + deal stage) on a 0-25 scale."
    )
    parser.add_argument("--contact-id", dest="contact_id", default=None, help="CRM contact ID")
    parser.add_argument("--company-id", dest="company_id", default=None, help="CRM company ID")
    parser.add_argument(
        "--stage-map-file",
        dest="stage_map_file",
        default=None,
        help="Optional JSON file mapping dealstage IDs to 'early'/'late' for precise deal-stage classification",
    )
    parser.add_argument("--json", dest="as_json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    if not args.contact_id and not args.company_id:
        parser.error("At least one of --contact-id or --company-id is required.")

    stage_map = load_stage_map(args.stage_map_file)
    result = score_engagement(contact_id=args.contact_id, company_id=args.company_id, stage_map=stage_map)

    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        print_human_summary(result)


if __name__ == "__main__":
    main()
