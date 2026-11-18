# generated-by: gemini-ultra
"""Source-grounded atomic claim extraction and verbatim character-offset verification."""

from __future__ import annotations

from dataclasses import dataclass
import re

from paradox_engine.ingest import SourceSnapshot


class ClaimVerificationError(ValueError):
    """Raised when a claim fails verbatim substring or metadata alignment."""


@dataclass(frozen=True)
class Claim:
    claim_id: str
    paragraph_id: str
    section_anchor: str
    revision_id: int
    claim_type: str
    summary: str
    exact_quote: str
    char_span: tuple[int, int]
    numbers: list[str]
    citation_url: str

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "paragraph_id": self.paragraph_id,
            "section_anchor": self.section_anchor,
            "revision_id": self.revision_id,
            "claim_type": self.claim_type,
            "summary": self.summary,
            "exact_quote": self.exact_quote,
            "char_span": [self.char_span[0], self.char_span[1]],
            "numbers": list(self.numbers),
            "citation_url": self.citation_url,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Claim":
        span_raw = payload["char_span"]
        if not isinstance(span_raw, (list, tuple)) or len(span_raw) != 2:
            raise ClaimVerificationError("char_span must be a 2-element [start, end] pair.")
        nums_raw = payload.get("numbers", [])
        if not isinstance(nums_raw, list):
            raise ClaimVerificationError("numbers must be a list of strings.")
        return cls(
            claim_id=str(payload["claim_id"]),
            paragraph_id=str(payload["paragraph_id"]),
            section_anchor=str(payload["section_anchor"]),
            revision_id=int(payload["revision_id"]),  # type: ignore[arg-type]
            claim_type=str(payload["claim_type"]),
            summary=str(payload["summary"]),
            exact_quote=str(payload["exact_quote"]),
            char_span=(int(span_raw[0]), int(span_raw[1])),
            numbers=[str(x) for x in nums_raw],
            citation_url=str(payload["citation_url"]),
        )


_NUMBER_TOKEN_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_CAUSAL_CUES = (
    "however",
    "instead",
    "yet",
    "once",
    "scrapped",
    "released",
    "worsen",
    "sank",
    "flooded",
    "breeding",
    "breed",
    "roaming",
    "top-heavy",
    "intact",
)


def extract_normalized_numbers(text: str) -> list[str]:
    seen: list[str] = []
    for match in _NUMBER_TOKEN_RE.finditer(text):
        norm = match.group(0).replace(",", "")
        if norm not in seen:
            seen.append(norm)
    return seen


def _classify_sentence(sentence: str, nums: list[str]) -> str | None:
    lower = sentence.lower()
    has_causal = any(cue in lower for cue in _CAUSAL_CUES)
    if nums and has_causal:
        return "causal_turn"
    if any(re.fullmatch(r"1[5-9]\d{2}|20\d{2}", n) for n in nums):
        return "date"
    if nums:
        return "quantity"
    if has_causal:
        return "causal_turn"
    return None


def _summarize_quote(quote: str) -> str:
    trimmed = quote.strip()
    if len(trimmed) <= 120:
        return trimmed
    return trimmed[:117].rsplit(" ", 1)[0] + "..."


def extract_claims(snapshot: SourceSnapshot) -> list[Claim]:
    """Deterministically extract source-grounded factual claims with exact offsets."""
    claims: list[Claim] = []
    counter = 1
    for para in snapshot.paragraphs:
        cursor = 0
        for sentence in _SENTENCE_SPLIT_RE.split(para.text):
            sent = sentence.strip()
            if len(sent) < 20:
                continue
            start = para.text.find(sent, cursor)
            if start == -1:
                start = para.text.find(sent)
            if start == -1:
                continue
            end = start + len(sent)
            cursor = end

            nums = extract_normalized_numbers(sent)
            claim_type = _classify_sentence(sent, nums)
            if claim_type is None:
                continue

            claim = Claim(
                claim_id=f"c{counter:02d}",
                paragraph_id=para.paragraph_id,
                section_anchor=para.section_anchor,
                revision_id=snapshot.revision_id,
                claim_type=claim_type,
                summary=_summarize_quote(sent),
                exact_quote=sent,
                char_span=(start, end),
                numbers=nums,
                citation_url=f"{snapshot.attribution_url}#{para.section_anchor}",
            )
            verify_claim_alignment(claim, snapshot)
            claims.append(claim)
            counter += 1
    return claims


def verify_claim_alignment(claim: Claim, snapshot: SourceSnapshot) -> None:
    """Hard-fail if a claim does not literally align with its source paragraph."""
    if claim.revision_id != snapshot.revision_id:
        raise ClaimVerificationError(
            f"Claim {claim.claim_id} revision_id {claim.revision_id} != snapshot {snapshot.revision_id}."
        )

    para_map = {p.paragraph_id: p for p in snapshot.paragraphs}
    if claim.paragraph_id not in para_map:
        raise ClaimVerificationError(
            f"Claim {claim.claim_id} references missing paragraph_id '{claim.paragraph_id}'."
        )
    para = para_map[claim.paragraph_id]

    if claim.section_anchor != para.section_anchor:
        raise ClaimVerificationError(
            f"Claim {claim.claim_id} section_anchor '{claim.section_anchor}' != '{para.section_anchor}'."
        )

    start, end = claim.char_span
    if start < 0 or end > len(para.text) or start >= end:
        raise ClaimVerificationError(
            f"Claim {claim.claim_id} char_span [{start}, {end}] out of bounds for length {len(para.text)}."
        )

    if len(claim.exact_quote.strip()) < 12:
        raise ClaimVerificationError(f"Claim {claim.claim_id} exact_quote is too short.")

    actual_slice = para.text[start:end]
    if actual_slice != claim.exact_quote:
        raise ClaimVerificationError(
            f"Verbatim mismatch on {claim.claim_id}: slice '{actual_slice}' != exact_quote '{claim.exact_quote}'."
        )

    quote_numbers = set(extract_normalized_numbers(claim.exact_quote))
    for num in claim.numbers:
        norm_num = num.replace(",", "")
        if norm_num not in quote_numbers:
            raise ClaimVerificationError(
                f"Claim {claim.claim_id} lists phantom number '{num}' absent from exact_quote."
            )


def verify_all_claims(claims: list[Claim], snapshot: SourceSnapshot) -> None:
    if not claims:
        raise ClaimVerificationError("Claim list cannot be empty.")
    for claim in claims:
        verify_claim_alignment(claim, snapshot)
