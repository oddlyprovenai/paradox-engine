# generated-by: gemini-ultra
"""TDD test suite for oddly-paradox-engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paradox_engine.claims import (
    Claim,
    ClaimVerificationError,
    extract_claims,
    verify_all_claims,
    verify_claim_alignment,
)
from paradox_engine.cli import main as cli_main
from paradox_engine.ingest import load_snapshot, parse_mediawiki_html
from paradox_engine.oddly_exporter import export_oddly_bundle
from paradox_engine.qa import run_qa_gate
from paradox_engine.review import (
    ReviewGateError,
    approve_review,
    init_review_checklist,
    verify_review_gate,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
COBRA_FIXTURE = REPO_ROOT / "fixtures" / "cobra_effect_wiki.json"
VASA_FIXTURE = REPO_ROOT / "fixtures" / "vasa_ship_wiki.json"


def test_load_snapshot_json_cobra_effect() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    assert snap.slug == "cobra-effect"
    assert snap.title == "Perverse incentive"
    assert snap.revision_id == 1254091820
    assert snap.license == "CC BY-SA 4.0"
    assert "oldid=1254091820" in snap.attribution_url
    assert len(snap.paragraphs) == 5
    assert snap.paragraphs[0].paragraph_id == "p0"
    assert snap.paragraphs[0].section_anchor == "The_original_cobra_effect"


def test_load_snapshot_vasa_ship() -> None:
    snap = load_snapshot(VASA_FIXTURE)
    assert snap.slug == "vasa-ship"
    assert snap.revision_id == 1253884105
    assert len(snap.paragraphs) == 5
    anchors = {p.section_anchor for p in snap.paragraphs}
    assert anchors == {"Construction_and_armament", "Maiden_voyage_and_salvage"}


def test_parse_mediawiki_html_snapshot() -> None:
    raw_html = """
    <div class="mw-parser-output">
      <h2 id="Background">Background</h2>
      <p>In 1899 municipal engineers built 4 drainage tunnels[1] to divert floodwater.</p>
      <p>Instead, silt blocked 3 tunnels within 18 months[2], doubling street flooding.</p>
    </div>
    """
    snap = parse_mediawiki_html(
        html_text=raw_html,
        slug="tunnel-paradox",
        title="Tunnel paradox",
        page_url="https://en.wikipedia.org/wiki/Tunnel_paradox",
        revision_id=11002200,
    )
    assert len(snap.paragraphs) == 2
    assert "[1]" not in snap.paragraphs[0].text
    assert "1899" in snap.paragraphs[0].text
    assert snap.paragraphs[1].section_anchor == "Background"


def test_extract_claims_verbatim_alignment() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    assert len(claims) >= 4
    verify_all_claims(claims, snap)
    para_map = {p.paragraph_id: p.text for p in snap.paragraphs}
    for claim in claims:
        start, end = claim.char_span
        assert para_map[claim.paragraph_id][start:end] == claim.exact_quote
        assert f"oldid={snap.revision_id}#{claim.section_anchor}" in claim.citation_url


def test_extract_claims_vasa_numbers() -> None:
    snap = load_snapshot(VASA_FIXTURE)
    claims = extract_claims(snap)
    verify_all_claims(claims, snap)
    all_numbers = {num for c in claims for num in c.numbers}
    for expected in ("1626", "1628", "64", "2", "1300", "32", "30", "1961", "333"):
        assert expected in all_numbers


def test_verify_claim_rejects_fabricated_quote() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    original = claims[0]
    forged = Claim(
        claim_id=original.claim_id,
        paragraph_id=original.paragraph_id,
        section_anchor=original.section_anchor,
        revision_id=original.revision_id,
        claim_type=original.claim_type,
        summary=original.summary,
        exact_quote=original.exact_quote.replace("2001", "2004"),
        char_span=original.char_span,
        numbers=["2004"],
        citation_url=original.citation_url,
    )
    with pytest.raises(ClaimVerificationError, match="Verbatim mismatch"):
        verify_claim_alignment(forged, snap)


def test_verify_claim_rejects_wrong_char_offsets() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    original = extract_claims(snap)[0]
    shifted = Claim(
        claim_id=original.claim_id,
        paragraph_id=original.paragraph_id,
        section_anchor=original.section_anchor,
        revision_id=original.revision_id,
        claim_type=original.claim_type,
        summary=original.summary,
        exact_quote=original.exact_quote,
        char_span=(original.char_span[0] + 1, original.char_span[1]),
        numbers=original.numbers,
        citation_url=original.citation_url,
    )
    with pytest.raises(ClaimVerificationError):
        verify_claim_alignment(shifted, snap)


def test_verify_claim_rejects_revision_mismatch() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    original = extract_claims(snap)[0]
    stale = Claim(
        claim_id=original.claim_id,
        paragraph_id=original.paragraph_id,
        section_anchor=original.section_anchor,
        revision_id=999999,
        claim_type=original.claim_type,
        summary=original.summary,
        exact_quote=original.exact_quote,
        char_span=original.char_span,
        numbers=original.numbers,
        citation_url=original.citation_url,
    )
    with pytest.raises(ClaimVerificationError, match="revision_id"):
        verify_claim_alignment(stale, snap)


def test_verify_claim_rejects_phantom_number_in_claim_metadata() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    original = extract_claims(snap)[0]
    injected = Claim(
        claim_id=original.claim_id,
        paragraph_id=original.paragraph_id,
        section_anchor=original.section_anchor,
        revision_id=original.revision_id,
        claim_type=original.claim_type,
        summary=original.summary,
        exact_quote=original.exact_quote,
        char_span=original.char_span,
        numbers=[*original.numbers, "7777"],
        citation_url=original.citation_url,
    )
    with pytest.raises(ClaimVerificationError, match="7777"):
        verify_claim_alignment(injected, snap)


def test_init_review_checklist_defaults_unapproved() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    assert checklist["_generated_by"] == "gemini-ultra"
    assert checklist["status"] == "pending_human_review"
    assert checklist["review_token"] is None
    assert all(item["approved"] is False for item in checklist["claims"])


def test_approve_review_rejects_short_human_take() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    ids = [c.claim_id for c in claims[:3]]
    with pytest.raises(ReviewGateError, match="40"):
        approve_review(
            checklist,
            snapshot=snap,
            narrative_angle="Incentives measure proxies instead of outcomes",
            human_editorial_take="Too short editorial note.",
            approved_claim_ids=ids,
        )


def test_approve_review_rejects_copied_wikipedia_sentence() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    ids = [c.claim_id for c in claims[:3]]
    copied = snap.paragraphs[0].text[:80]
    with pytest.raises(ReviewGateError, match="original"):
        approve_review(
            checklist,
            snapshot=snap,
            narrative_angle="Incentives measure proxies instead of outcomes",
            human_editorial_take=copied,
            approved_claim_ids=ids,
        )


def test_approve_review_rejects_fewer_than_three_claims() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    with pytest.raises(ReviewGateError, match="at least 3"):
        approve_review(
            checklist,
            snapshot=snap,
            narrative_angle="Incentives measure proxies instead of outcomes",
            human_editorial_take="Paying for a proxy metric turns your target metric into a business model.",
            approved_claim_ids=[claims[0].claim_id, claims[1].claim_id],
        )


def test_approve_review_generates_deterministic_sha256_token() -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    ids = [c.claim_id for c in claims[:4]]
    approved = approve_review(
        checklist,
        snapshot=snap,
        narrative_angle="Proxy metrics become factories when rewards detach from real outcomes",
        human_editorial_take="Whenever you pay for dead tails instead of clean sewers, people build tail farms.",
        approved_claim_ids=ids,
    )
    assert approved["status"] == "approved"
    assert isinstance(approved["review_token"], str)
    assert len(approved["review_token"]) == 64
    verified_claims = verify_review_gate(approved, snap)
    assert len(verified_claims) == 4


def test_export_blocks_unapproved_review(tmp_path: Path) -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    with pytest.raises(ReviewGateError):
        export_oddly_bundle(snap, checklist, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def test_export_blocks_tampered_review_token(tmp_path: Path) -> None:
    snap = load_snapshot(COBRA_FIXTURE)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    approved = approve_review(
        checklist,
        snapshot=snap,
        narrative_angle="Proxy metrics become factories when rewards detach from real outcomes",
        human_editorial_take="Whenever you pay for dead tails instead of clean sewers, people build tail farms.",
        approved_claim_ids=[c.claim_id for c in claims[:4]],
    )
    approved["human_editorial_take"] = (
        "Tampered post-approval commentary without re-signing the token."
    )
    with pytest.raises(ReviewGateError, match="token"):
        export_oddly_bundle(snap, approved, tmp_path / "bundle")


def _build_approved_bundle(fixture: Path, out_dir: Path) -> tuple[object, dict]:
    snap = load_snapshot(fixture)
    claims = extract_claims(snap)
    checklist = init_review_checklist(snap, claims)
    approved = approve_review(
        checklist,
        snapshot=snap,
        narrative_angle="Rewarding the proxy metric manufactures the exact hazard you tried to erase",
        human_editorial_take="Every KPI bounty fails the moment harvesting the metric pays more than solving the root problem.",
        approved_claim_ids=[c.claim_id for c in claims],
    )
    export_oddly_bundle(snap, approved, out_dir)
    return snap, approved


def test_export_generates_complete_oddly_shorts_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "cobra-bundle"
    snap, _ = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    ep_dir = out_dir / "episodes" / snap.slug
    vid_dir = out_dir / "src" / "videos" / snap.slug

    assert (ep_dir / "voice" / "script.txt").is_file()
    assert (ep_dir / "voice" / "say.json").is_file()
    assert (ep_dir / "SCRIPT.md").is_file()
    assert (ep_dir / "copy.txt").is_file()
    assert (ep_dir / "receipts.json").is_file()
    assert (vid_dir / "plan.json").is_file()

    script_md = (ep_dir / "SCRIPT.md").read_text(encoding="utf-8")
    assert "Hook Variant A" in script_md
    assert "Hook Variant B" in script_md
    assert "Hook Variant C" in script_md

    plan = json.loads((vid_dir / "plan.json").read_text(encoding="utf-8"))
    assert plan["_generated_by"] == "gemini-ultra"
    assert plan["accent"] == "#88D445"
    assert plan["cameo"] == "cactus"
    assert plan["subStyle"] == "pop"
    assert len(plan["segments"]) >= 6
    assert len(plan["expr"]) >= 4
    assert any(o["kind"] == "lower" for o in plan["overlays"])
    assert any(o["kind"] == "end" for o in plan["overlays"])
    term_lines = [
        line
        for s in plan["screens"]
        if s.get("kind") == "terminal"
        for line in s.get("lines", [])
    ]
    assert any("lab@mac-studio ~ %" in line for line in term_lines)


def test_qa_passes_clean_exported_bundles(tmp_path: Path) -> None:
    for idx, fixture in enumerate((COBRA_FIXTURE, VASA_FIXTURE)):
        out_dir = tmp_path / f"bundle-{idx}"
        snap, approved = _build_approved_bundle(fixture, out_dir)
        report = run_qa_gate(out_dir, snap, approved)
        assert report.passed is True, report.errors
        assert report.errors == []


def test_qa_rejects_unverified_number_injected_into_script(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    snap, approved = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    script_path = out_dir / "episodes" / snap.slug / "voice" / "script.txt"
    script_path.write_text(
        script_path.read_text(encoding="utf-8") + "\nOver 9,450 clerks resigned overnight.\n",
        encoding="utf-8",
    )
    report = run_qa_gate(out_dir, snap, approved)
    assert report.passed is False
    assert any("UNVERIFIED_NUMBER" in err and "9450" in err for err in report.errors)


def test_qa_rejects_unverified_number_in_plan_overlay(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    snap, approved = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    plan_path = out_dir / "src" / "videos" / snap.slug / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["overlays"].insert(
        1,
        {
            "kind": "number",
            "from": 14.0,
            "to": 17.5,
            "before": "10",
            "after": "8888",
            "label": "invented stat",
            "yPct": 64.0,
        },
    )
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    report = run_qa_gate(out_dir, snap, approved)
    assert report.passed is False
    assert any("UNVERIFIED_NUMBER" in err and "8888" in err for err in report.errors)


def test_qa_rejects_pii_home_path_and_email_leak(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    snap, approved = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    script_path = out_dir / "episodes" / snap.slug / "voice" / "script.txt"
    forged_path = "/" + "Users" + "/alex/private_notes.txt"
    forged_mail = "alex@" + "gm" + "ail.com"
    script_path.write_text(
        script_path.read_text(encoding="utf-8") + f"\nLoaded from {forged_path} by {forged_mail}.\n",
        encoding="utf-8",
    )
    report = run_qa_gate(out_dir, snap, approved)
    assert report.passed is False
    assert any("PII_LEAK" in err for err in report.errors)


def test_qa_rejects_api_key_and_forbidden_hype_words(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    snap, approved = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    copy_path = out_dir / "episodes" / snap.slug / "copy.txt"
    fake_token = "s" + "k-" + "Proj99887766554433221100"
    hype = "rev" + "olutionary"
    copy_path.write_text(
        copy_path.read_text(encoding="utf-8") + f"\nToken {fake_token} for {hype} pipeline.\n",
        encoding="utf-8",
    )
    report = run_qa_gate(out_dir, snap, approved)
    assert report.passed is False
    assert any("OPSEC_VIOLATION" in err for err in report.errors)


def test_qa_rejects_safe_zone_violation_in_overlays(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    snap, approved = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    plan_path = out_dir / "src" / "videos" / snap.slug / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["overlays"][0]["yPct"] = 5.0
    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    report = run_qa_gate(out_dir, snap, approved)
    assert report.passed is False
    assert any("SAFE_ZONE_VIOLATION" in err for err in report.errors)


def test_qa_rejects_missing_cc_by_sa_or_ai_disclosure(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    snap, approved = _build_approved_bundle(COBRA_FIXTURE, out_dir)
    copy_path = out_dir / "episodes" / snap.slug / "copy.txt"
    copy_path.write_text("# generated-by: gemini-ultra\nTitle: Cobra Effect\nJust hashtags #history\n", encoding="utf-8")
    report = run_qa_gate(out_dir, snap, approved)
    assert report.passed is False
    assert any("ATTRIBUTION_MISSING" in err for err in report.errors)


def test_cli_end_to_end_pipeline(tmp_path: Path) -> None:
    review_path = tmp_path / "claims_review.json"
    bundle_dir = tmp_path / "vasa-bundle"

    rc_extract = cli_main(
        ["extract", "--snapshot", str(VASA_FIXTURE), "--out", str(review_path)]
    )
    assert rc_extract == 0
    review_raw = json.loads(review_path.read_text(encoding="utf-8"))
    claim_ids = ",".join(item["claim_id"] for item in review_raw["claims"])

    rc_approve = cli_main(
        [
            "approve",
            "--snapshot",
            str(VASA_FIXTURE),
            "--review",
            str(review_path),
            "--angle",
            "Top-heavy prestige requirements sank Vasa 1,300 meters into her maiden voyage",
            "--take",
            "Adding firepower without recalculating hull stability sinks warships and software launches alike.",
            "--claims",
            claim_ids,
        ]
    )
    assert rc_approve == 0

    rc_export = cli_main(
        [
            "export",
            "--snapshot",
            str(VASA_FIXTURE),
            "--review",
            str(review_path),
            "--out-dir",
            str(bundle_dir),
        ]
    )
    assert rc_export == 0

    rc_qa = cli_main(
        [
            "qa",
            "--bundle",
            str(bundle_dir),
            "--snapshot",
            str(VASA_FIXTURE),
            "--review",
            str(review_path),
        ]
    )
    assert rc_qa == 0
