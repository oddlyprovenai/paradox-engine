# generated-by: gemini-ultra
"""Command-line interface for oddly-paradox-engine (`paradox` / `paradox-engine`)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from paradox_engine.claims import ClaimVerificationError, extract_claims
from paradox_engine.ingest import load_snapshot
from paradox_engine.oddly_exporter import export_oddly_bundle
from paradox_engine.qa import run_qa_gate
from paradox_engine.review import ReviewGateError, approve_review, init_review_checklist


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paradox",
        description="Source-grounded paradox claim verifier and oddly-shorts 9:16 exporter.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="Extract verbatim-verified claims from snapshot")
    p_extract.add_argument("--snapshot", required=True, help="Path to Wikipedia JSON/HTML snapshot")
    p_extract.add_argument("--out", required=True, help="Output claims_review.json path")

    p_approve = sub.add_parser("approve", help="Record human angle, commentary, and SHA-256 sign-off")
    p_approve.add_argument("--snapshot", required=True, help="Path to Wikipedia snapshot")
    p_approve.add_argument("--review", required=True, help="Path to claims_review.json")
    p_approve.add_argument("--angle", required=True, help="Narrative angle (>= 10 chars)")
    p_approve.add_argument(
        "--take",
        required=True,
        help="Original human editorial take (>= 40 chars, non-copied)",
    )
    p_approve.add_argument(
        "--claims",
        required=True,
        help="Comma-separated approved claim IDs (at least 3, e.g. c01,c02,c03)",
    )
    p_approve.add_argument(
        "--reviewer",
        default="editor@oddlyproven.local",
        help="Reviewer identifier",
    )

    p_export = sub.add_parser("export", help="Export verified oddly-shorts 9:16 episode bundle")
    p_export.add_argument("--snapshot", required=True, help="Path to Wikipedia snapshot")
    p_export.add_argument("--review", required=True, help="Path to approved claims_review.json")
    p_export.add_argument("--out-dir", required=True, help="Output directory for oddly-shorts bundle")

    p_qa = sub.add_parser("qa", help="Run fact-number, OPSEC/PII, and safe-zone QA gate on bundle")
    p_qa.add_argument("--bundle", required=True, help="Bundle directory created by `paradox export`")
    p_qa.add_argument("--snapshot", required=True, help="Path to Wikipedia snapshot")
    p_qa.add_argument("--review", required=True, help="Path to approved claims_review.json")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "extract":
            snap = load_snapshot(args.snapshot)
            claims = extract_claims(snap)
            checklist = init_review_checklist(snap, claims)
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(checklist, indent=2) + "\n", encoding="utf-8")
            print(
                f"[paradox] Extracted {len(claims)} verbatim-aligned claims "
                f"(oldid={snap.revision_id}) -> {out_path.name}"
            )
            for c in claims:
                nums = ",".join(c.numbers) if c.numbers else "-"
                print(
                    f"  {c.claim_id} | {c.paragraph_id}[{c.char_span[0]}:{c.char_span[1]}] "
                    f"| nums=[{nums}] | #{c.section_anchor}"
                )
            return 0

        if args.command == "approve":
            snap = load_snapshot(args.snapshot)
            review_path = Path(args.review)
            review_data = json.loads(review_path.read_text(encoding="utf-8"))
            claim_ids = [x.strip() for x in str(args.claims).split(",") if x.strip()]
            approved = approve_review(
                review_data,
                snapshot=snap,
                narrative_angle=args.angle,
                human_editorial_take=args.take,
                approved_claim_ids=claim_ids,
                reviewer=args.reviewer,
            )
            review_path.write_text(json.dumps(approved, indent=2) + "\n", encoding="utf-8")
            token_short = str(approved["review_token"])[:16]
            print(
                f"[paradox] Approved {len(claim_ids)} claims for '{snap.title}' "
                f"(token={token_short}...)"
            )
            return 0

        if args.command == "export":
            snap = load_snapshot(args.snapshot)
            review_data = json.loads(Path(args.review).read_text(encoding="utf-8"))
            bundle_root = export_oddly_bundle(snap, review_data, args.out_dir)
            print(
                f"[paradox] Exported oddly-shorts 9:16 bundle for '{snap.slug}' -> {bundle_root.name}/"
            )
            return 0

        if args.command == "qa":
            snap = load_snapshot(args.snapshot)
            review_data = json.loads(Path(args.review).read_text(encoding="utf-8"))
            report = run_qa_gate(args.bundle, snap, review_data)
            if not report.passed:
                for err in report.errors:
                    print(f"[paradox QA FAIL] {err}", file=sys.stderr)
                return 1
            print(
                f"[paradox QA PASS] {len(report.checked_files)} files verified · "
                "0 unverified numbers · 0 PII/OPSEC leaks · safe zones [12%..80%] OK"
            )
            return 0

    except (ClaimVerificationError, ReviewGateError, ValueError, KeyError) as exc:
        print(f"[paradox ERROR] {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
