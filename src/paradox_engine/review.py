# generated-by: gemini-ultra
"""Mandatory human-review checklist and cryptographic SHA-256 sign-off gate."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import hmac
import json

from paradox_engine.claims import Claim, ClaimVerificationError, verify_claim_alignment
from paradox_engine.ingest import SourceSnapshot, normalize_paragraph_text


class ReviewGateError(ValueError):
    """Raised when human editorial review requirements or tokens fail verification."""


MIN_APPROVED_CLAIMS = 3
MIN_EDITORIAL_TAKE_CHARS = 40
MIN_ANGLE_CHARS = 10


def _compute_review_token(
    revision_id: int,
    narrative_angle: str,
    human_editorial_take: str,
    approved_claims: list[Claim],
) -> str:
    canonical_payload = {
        "revision_id": int(revision_id),
        "narrative_angle": narrative_angle.strip(),
        "human_editorial_take": human_editorial_take.strip(),
        "approved_claims": [
            {
                "claim_id": c.claim_id,
                "paragraph_id": c.paragraph_id,
                "char_span": [c.char_span[0], c.char_span[1]],
                "exact_quote": c.exact_quote,
            }
            for c in sorted(approved_claims, key=lambda x: x.claim_id)
        ],
    }
    encoded = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def init_review_checklist(snapshot: SourceSnapshot, claims: list[Claim]) -> dict[str, object]:
    for claim in claims:
        verify_claim_alignment(claim, snapshot)

    return {
        "_generated_by": "gemini-ultra",
        "slug": snapshot.slug,
        "title": snapshot.title,
        "revision_id": snapshot.revision_id,
        "attribution_url": snapshot.attribution_url,
        "license": snapshot.license,
        "status": "pending_human_review",
        "narrative_angle": "",
        "human_editorial_take": "",
        "reviewer": "",
        "approved_at": None,
        "review_token": None,
        "claims": [
            {
                **claim.to_dict(),
                "approved": False,
            }
            for claim in claims
        ],
    }


def _assert_original_editorial_take(take: str, snapshot: SourceSnapshot) -> None:
    cleaned = normalize_paragraph_text(take)
    if len(cleaned) < MIN_EDITORIAL_TAKE_CHARS:
        raise ReviewGateError(
            f"human_editorial_take must be >= {MIN_EDITORIAL_TAKE_CHARS} chars (got {len(cleaned)})."
        )
    lower_take = cleaned.lower()
    for para in snapshot.paragraphs:
        if lower_take in para.text.lower():
            raise ReviewGateError(
                "human_editorial_take must be original human commentary, not copied verbatim from Wikipedia."
            )


def approve_review(
    review_data: dict[str, object],
    snapshot: SourceSnapshot,
    narrative_angle: str,
    human_editorial_take: str,
    approved_claim_ids: list[str],
    reviewer: str = "editor@oddlyproven.local",
) -> dict[str, object]:
    angle_clean = narrative_angle.strip()
    if len(angle_clean) < MIN_ANGLE_CHARS:
        raise ReviewGateError(f"narrative_angle must be >= {MIN_ANGLE_CHARS} chars.")

    _assert_original_editorial_take(human_editorial_take, snapshot)

    wanted_ids = {cid.strip() for cid in approved_claim_ids if cid.strip()}
    if len(wanted_ids) < MIN_APPROVED_CLAIMS:
        raise ReviewGateError(
            f"Must approve at least {MIN_APPROVED_CLAIMS} claims (got {len(wanted_ids)})."
        )

    updated = copy.deepcopy(review_data)
    raw_claims = updated.get("claims")
    if not isinstance(raw_claims, list):
        raise ReviewGateError("Invalid claims array in review checklist.")

    approved_objs: list[Claim] = []
    found_ids: set[str] = set()
    for entry in raw_claims:
        if not isinstance(entry, dict):
            raise ReviewGateError("Malformed claim entry.")
        claim = Claim.from_dict(entry)
        verify_claim_alignment(claim, snapshot)
        is_selected = claim.claim_id in wanted_ids
        entry["approved"] = is_selected
        if is_selected:
            approved_objs.append(claim)
            found_ids.add(claim.claim_id)

    missing = wanted_ids - found_ids
    if missing:
        raise ReviewGateError(f"Unknown claim_id(s): {sorted(missing)}")

    take_clean = normalize_paragraph_text(human_editorial_take)
    token = _compute_review_token(
        revision_id=snapshot.revision_id,
        narrative_angle=angle_clean,
        human_editorial_take=take_clean,
        approved_claims=approved_objs,
    )

    updated["_generated_by"] = "gemini-ultra"
    updated["revision_id"] = snapshot.revision_id
    updated["status"] = "approved"
    updated["narrative_angle"] = angle_clean
    updated["human_editorial_take"] = take_clean
    updated["reviewer"] = reviewer.strip()
    updated["approved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated["review_token"] = token
    return updated


def verify_review_gate(
    review_data: dict[str, object], snapshot: SourceSnapshot
) -> list[Claim]:
    """Verify human approval status, editorial length, claim alignment, and SHA-256 token."""
    if review_data.get("status") != "approved":
        raise ReviewGateError("Checklist status is not 'approved'. Run `paradox approve` first.")

    token = review_data.get("review_token")
    if not isinstance(token, str) or len(token) != 64:
        raise ReviewGateError("Missing or malformed SHA-256 review_token.")

    rev_id = int(review_data.get("revision_id", -1))  # type: ignore[arg-type]
    if rev_id != snapshot.revision_id:
        raise ReviewGateError(
            f"Review revision_id {rev_id} does not match snapshot {snapshot.revision_id}."
        )

    angle = str(review_data.get("narrative_angle", "")).strip()
    if len(angle) < MIN_ANGLE_CHARS:
        raise ReviewGateError("narrative_angle is too short.")

    take = str(review_data.get("human_editorial_take", "")).strip()
    _assert_original_editorial_take(take, snapshot)

    raw_claims = review_data.get("claims")
    if not isinstance(raw_claims, list):
        raise ReviewGateError("Missing claims list.")

    approved_claims: list[Claim] = []
    for entry in raw_claims:
        if isinstance(entry, dict) and entry.get("approved") is True:
            try:
                claim = Claim.from_dict(entry)
                verify_claim_alignment(claim, snapshot)
            except ClaimVerificationError as exc:
                raise ReviewGateError(f"Approved claim failed source verification: {exc}") from exc
            approved_claims.append(claim)

    if len(approved_claims) < MIN_APPROVED_CLAIMS:
        raise ReviewGateError(
            f"Review requires at least {MIN_APPROVED_CLAIMS} approved claims."
        )

    expected_token = _compute_review_token(
        revision_id=snapshot.revision_id,
        narrative_angle=angle,
        human_editorial_take=take,
        approved_claims=approved_claims,
    )
    if not hmac.compare_digest(token, expected_token):
        raise ReviewGateError(
            "Invalid review_token: checklist content was altered after human approval."
        )

    return approved_claims
