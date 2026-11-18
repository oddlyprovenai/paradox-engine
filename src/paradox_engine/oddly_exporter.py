# generated-by: gemini-ultra
"""Exporter for oddly-shorts 9:16 episode bundles backed by verified claim receipts."""

from __future__ import annotations

import json
from pathlib import Path
import re

from paradox_engine import ODDLY_PALETTE
from paradox_engine.claims import Claim
from paradox_engine.ingest import SourceSnapshot
from paradox_engine.review import verify_review_gate

_WORD_RE = re.compile(r"\b[A-Za-z]{5,}\b")
_RAW_NUM_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b")

_DIGIT_WORDS = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
    "10": "ten",
    "30": "thirty",
    "32": "thirty-two",
    "64": "sixty-four",
    "333": "three hundred thirty-three",
    "1300": "thirteen hundred",
    "1,300": "thirteen hundred",
    "1626": "sixteen twenty-six",
    "1628": "sixteen twenty-eight",
    "1899": "eighteen ninety-nine",
    "1902": "nineteen oh two",
    "1961": "nineteen sixty-one",
    "2001": "two thousand one",
    "20112": "twenty thousand one hundred twelve",
    "20,112": "twenty thousand one hundred twelve",
}


def _highlight_one_word(sentence: str) -> str:
    if "*" in sentence:
        return sentence
    match = _WORD_RE.search(sentence)
    if not match:
        return sentence
    w = match.group(0)
    return sentence[: match.start()] + f"*{w}*" + sentence[match.end() :]


def _spoken_form(token: str) -> str:
    if token in _DIGIT_WORDS:
        return _DIGIT_WORDS[token]
    clean = token.replace(",", "")
    if clean in _DIGIT_WORDS:
        return _DIGIT_WORDS[clean]
    return " ".join(_DIGIT_WORDS.get(ch, ch) for ch in clean)


def _build_say_map(script_text: str) -> dict[str, str]:
    say: dict[str, str] = {
        "_generated_by": "gemini-ultra",
        "CC BY-SA": "Creative Commons Attribution Share Alike",
    }
    for m in _RAW_NUM_RE.finditer(script_text):
        raw_tok = m.group(0)
        if raw_tok not in say:
            say[raw_tok] = _spoken_form(raw_tok)
    return say


def _build_three_hooks(snapshot: SourceSnapshot, approved_claims: list[Claim]) -> list[str]:
    lead_num = next((n for c in approved_claims for n in c.numbers), None)
    num_tag = f" ({lead_num})" if lead_num else ""
    return [
        f"Hook Variant A: Here is how a well-meaning rule in {snapshot.title}{num_tag} backfired in public.",
        f"Hook Variant B: Every single fact in this {snapshot.title} breakdown carries a timestamped receipt.",
        f"Hook Variant C: Wait until you see what happened right after officials changed the rules in {snapshot.title}.",
    ]


def _build_script_lines(
    snapshot: SourceSnapshot,
    approved_claims: list[Claim],
    human_editorial_take: str,
) -> list[str]:
    lines: list[str] = [
        _highlight_one_word(
            f"Here is how {snapshot.title} turned a seemingly sensible plan into an unintended disaster."
        )
    ]
    for idx, claim in enumerate(approved_claims):
        quote = claim.exact_quote.rstrip(".") + "."
        if idx == 2:
            lines.append("Wait. It *gets* worse.")
        lines.append(_highlight_one_word(quote))

    lines.append(_highlight_one_word(human_editorial_take.rstrip(".") + "."))
    lines.append(
        "Every *fact* in this short links straight to its pinned Wikipedia revision receipt."
    )
    return lines


def _build_plan_json(
    snapshot: SourceSnapshot,
    approved_claims: list[Claim],
) -> dict[str, object]:
    total = 56.0
    segments = [
        {"from": 0.0, "cam": "host"},
        {"from": 4.6, "cam": "wide"},
        {"from": 9.2, "cam": "screen"},
        {"from": 16.5, "cam": "host"},
        {"from": 22.8, "cam": "over"},
        {"from": 30.4, "cam": "screen"},
        {"from": 39.6, "cam": "medium"},
        {"from": 47.2, "cam": "host"},
    ]
    expr = [
        [0.0, "grin"],
        [9.2, "smile"],
        [16.5, "nervous"],
        [30.4, "smile"],
        [47.2, "grin"],
    ]

    numeric_claims = [c for c in approved_claims if c.numbers]
    first_num = numeric_claims[0].numbers[0] if numeric_claims else ""
    second_num = (
        numeric_claims[-1].numbers[-1]
        if len(numeric_claims) >= 2
        else first_num
    )

    screens: list[dict[str, object]] = [
        {
            "from": 0.0,
            "to": 16.5,
            "screen": "main",
            "kind": "terminal",
            "cps": 28,
            "lines": [
                f"lab@mac-studio ~ % paradox extract --snapshot {snapshot.slug}.json",
                f"# pinned oldid {snapshot.revision_id}",
                "lab@mac-studio ~ % paradox approve --review claims_review.json",
                "# human editorial gate: VERIFIED",
            ],
        },
        {
            "from": 16.5,
            "to": 39.6,
            "screen": "main",
            "kind": "terminal",
            "cps": 30,
            "lines": [
                f"lab@mac-studio ~ % paradox qa --bundle out/{snapshot.slug}",
                f"# source anchor: #{approved_claims[0].section_anchor}",
                "# verbatim substring match: PASS",
            ],
        },
        {
            "from": 39.6,
            "to": total,
            "screen": "main",
            "kind": "mock",
            "title": "PARADOX ENGINE",
        },
    ]

    overlays: list[dict[str, object]] = [
        {
            "kind": "lower",
            "from": 0.8,
            "to": 5.2,
            "yPct": 72.0,
            "title": snapshot.title,
            "sub": f"Wikipedia CC BY-SA · oldid {snapshot.revision_id}",
        },
        {
            "kind": "lower",
            "from": 9.5,
            "to": 15.8,
            "yPct": 74.0,
            "title": f"Section #{approved_claims[0].section_anchor}",
            "sub": f"oldid {snapshot.revision_id}",
        },
    ]

    if first_num and second_num:
        overlays.append(
            {
                "kind": "number",
                "from": 23.2,
                "to": 29.8,
                "yPct": 64.0,
                "before": first_num,
                "after": second_num,
                "label": f"verified claim · oldid {snapshot.revision_id}",
            }
        )

    overlays.append(
        {
            "kind": "end",
            "from": 50.5,
            "yPct": 60.0,
            "title": "PARADOX ENGINE",
            "lines": [
                "Every fact in this video has a receipt.",
                "Source: Wikipedia CC BY-SA · AI-assisted animation",
            ],
            "handle": "Link in @oddlyprovenai bio",
        }
    )

    return {
        "_generated_by": "gemini-ultra",
        "total": total,
        "accent": ODDLY_PALETTE["lab_green"],
        "cameo": "cactus",
        "subStyle": "pop",
        "safeZone": {
            "subtitleHeightPct": [55.0, 72.0],
            "overlaySafeHeightPct": [12.0, 80.0],
        },
        "segments": segments,
        "expr": expr,
        "screens": screens,
        "overlays": overlays,
    }


def export_oddly_bundle(
    snapshot: SourceSnapshot,
    review_data: dict[str, object],
    out_dir: str | Path,
) -> Path:
    """Export an oddly-shorts 9:16 bundle only if the human review token is valid."""
    approved_claims = verify_review_gate(review_data, snapshot)
    root = Path(out_dir)
    ep_dir = root / "episodes" / snapshot.slug
    voice_dir = ep_dir / "voice"
    vid_dir = root / "src" / "videos" / snapshot.slug

    voice_dir.mkdir(parents=True, exist_ok=True)
    vid_dir.mkdir(parents=True, exist_ok=True)

    take = str(review_data["human_editorial_take"]).strip()
    angle = str(review_data["narrative_angle"]).strip()
    token = str(review_data["review_token"])

    script_lines = _build_script_lines(snapshot, approved_claims, take)
    narration_body = "\n".join(script_lines)
    script_txt = f"# generated-by: gemini-ultra\n{narration_body}\n"
    (voice_dir / "script.txt").write_text(script_txt, encoding="utf-8")

    say_map = _build_say_map(narration_body)
    (voice_dir / "say.json").write_text(
        json.dumps(say_map, indent=2) + "\n", encoding="utf-8"
    )

    hooks = _build_three_hooks(snapshot, approved_claims)
    claims_md = "\n".join(
        f"- `{c.claim_id}` (`{c.paragraph_id}[{c.char_span[0]}:{c.char_span[1]}]`, "
        f"`#{c.section_anchor}`): \"{c.exact_quote}\" — {c.citation_url}"
        for c in approved_claims
    )
    script_md = (
        "<!-- generated-by: gemini-ultra -->\n"
        f"# Episode Script · {snapshot.title}\n\n"
        "## Hook Variants (A/B Test)\n"
        f"- {hooks[0]}\n"
        f"- {hooks[1]}\n"
        f"- {hooks[2]}\n\n"
        "## Editorial Angle & Human Commentary\n"
        f"- **Angle**: {angle}\n"
        f"- **Human Take**: {take}\n"
        f"- **Review Token**: `{token}`\n\n"
        "## Voiced Narration (`voice/script.txt`)\n"
        f"{narration_body}\n\n"
        "## Pinpointed Wikipedia Receipts\n"
        f"{claims_md}\n"
    )
    (ep_dir / "SCRIPT.md").write_text(script_md, encoding="utf-8")

    short_title = f"{snapshot.title}: When Incentives Backfire"[:58]
    copy_txt = (
        "# generated-by: gemini-ultra\n"
        f"Title: {short_title}\n\n"
        "Every fact in this video has a receipt.\n"
        f"Source: Wikipedia contributors, '{snapshot.title}', licensed under {snapshot.license} "
        f"({snapshot.attribution_url}).\n"
        "Disclosure: AI-assisted animation and local voice synthesis; claims verified and approved by a human editor with oddly-paradox-engine.\n\n"
        "#history #paradox #economics #oddlyproven\n"
    )
    (ep_dir / "copy.txt").write_text(copy_txt, encoding="utf-8")

    plan_obj = _build_plan_json(snapshot, approved_claims)
    (vid_dir / "plan.json").write_text(
        json.dumps(plan_obj, indent=2) + "\n", encoding="utf-8"
    )

    receipts_obj = {
        "_generated_by": "gemini-ultra",
        "slug": snapshot.slug,
        "revision_id": snapshot.revision_id,
        "attribution_url": snapshot.attribution_url,
        "license": snapshot.license,
        "review_token": token,
        "verified_numbers": sorted(
            {num for c in approved_claims for num in c.numbers}
        ),
        "approved_claims": [c.to_dict() for c in approved_claims],
    }
    (ep_dir / "receipts.json").write_text(
        json.dumps(receipts_obj, indent=2) + "\n", encoding="utf-8"
    )

    return root
