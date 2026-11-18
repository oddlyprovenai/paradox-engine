# generated-by: gemini-ultra
"""Wikipedia snapshot ingestion (offline JSON/HTML and explicit revision-pinned fetch)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request


@dataclass(frozen=True)
class SourceParagraph:
    paragraph_id: str
    section_anchor: str
    text: str
    char_length: int


@dataclass(frozen=True)
class SourceSnapshot:
    slug: str
    title: str
    page_url: str
    revision_id: int
    retrieved_at: str
    license: str
    attribution_url: str
    paragraphs: list[SourceParagraph]


_WS_RE = re.compile(r"\s+")
_CITE_BRACKET_RE = re.compile(r"\[(?:\d+|citation needed|note \d+)\]", re.IGNORECASE)


def normalize_paragraph_text(raw: str) -> str:
    cleaned = _CITE_BRACKET_RE.sub("", raw)
    return _WS_RE.sub(" ", cleaned).strip()


def _build_attribution_url(page_url: str, revision_id: int) -> str:
    sep = "&" if "?" in page_url else "?"
    return f"{page_url}{sep}oldid={revision_id}"


class _MediaWikiHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_anchor = "lead"
        self._in_p = False
        self._p_buf: list[str] = []
        self.raw_paragraphs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag in {"h2", "h3", "span"} and attr_map.get("id"):
            anchor = attr_map["id"] or ""
            if anchor and not anchor.startswith("cite_"):
                self.current_anchor = anchor
        if tag == "p":
            self._in_p = True
            self._p_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._in_p:
            self._in_p = False
            joined = normalize_paragraph_text("".join(self._p_buf))
            if joined:
                self.raw_paragraphs.append((self.current_anchor, joined))
            self._p_buf = []

    def handle_data(self, data: str) -> None:
        if self._in_p:
            self._p_buf.append(data)


def parse_mediawiki_html(
    html_text: str,
    slug: str,
    title: str,
    page_url: str,
    revision_id: int,
    retrieved_at: str | None = None,
    license_name: str = "CC BY-SA 4.0",
) -> SourceSnapshot:
    parser = _MediaWikiHTMLParser()
    parser.feed(html_text)
    paragraphs = [
        SourceParagraph(
            paragraph_id=f"p{idx}",
            section_anchor=anchor,
            text=text,
            char_length=len(text),
        )
        for idx, (anchor, text) in enumerate(parser.raw_paragraphs)
    ]
    if not paragraphs:
        raise ValueError("No readable paragraphs found in MediaWiki HTML snapshot.")
    ts = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return SourceSnapshot(
        slug=slug,
        title=title,
        page_url=page_url,
        revision_id=int(revision_id),
        retrieved_at=ts,
        license=license_name,
        attribution_url=_build_attribution_url(page_url, int(revision_id)),
        paragraphs=paragraphs,
    )


def load_snapshot(path: str | Path) -> SourceSnapshot:
    snap_path = Path(path)
    raw_text = snap_path.read_text(encoding="utf-8")
    if snap_path.suffix.lower() in {".html", ".htm"}:
        slug = snap_path.stem.replace("_", "-")
        return parse_mediawiki_html(
            html_text=raw_text,
            slug=slug,
            title=slug.replace("-", " ").title(),
            page_url=f"https://en.wikipedia.org/wiki/{urllib.parse.quote(slug)}",
            revision_id=1,
        )

    payload = json.loads(raw_text)
    slug = str(payload["slug"])
    title = str(payload["title"])
    page_url = str(payload["page_url"])
    revision_id = int(payload["revision_id"])
    retrieved_at = str(payload.get("retrieved_at", "2026-01-01T00:00:00Z"))
    license_name = str(payload.get("license", "CC BY-SA 4.0"))

    paragraphs: list[SourceParagraph] = []
    idx = 0
    for section in payload.get("sections", []):
        anchor = str(section.get("anchor", "lead"))
        for raw_p in section.get("paragraphs", []):
            norm = normalize_paragraph_text(str(raw_p))
            if norm:
                paragraphs.append(
                    SourceParagraph(
                        paragraph_id=f"p{idx}",
                        section_anchor=anchor,
                        text=norm,
                        char_length=len(norm),
                    )
                )
                idx += 1

    if not paragraphs:
        raise ValueError(f"Snapshot {snap_path} contains zero paragraphs.")

    return SourceSnapshot(
        slug=slug,
        title=title,
        page_url=page_url,
        revision_id=revision_id,
        retrieved_at=retrieved_at,
        license=license_name,
        attribution_url=_build_attribution_url(page_url, revision_id),
        paragraphs=paragraphs,
    )


def fetch_wikipedia_snapshot(title: str, lang: str = "en") -> SourceSnapshot:
    """Explicit opt-in live fetch from MediaWiki parse API with revision pinning."""
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    api_url = (
        f"https://{lang}.wikipedia.org/w/api.php?"
        f"action=parse&page={encoded}&prop=text|revid&format=json&redirects=1"
    )
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "oddly-paradox-engine/0.1 (https://oddlyproven.local)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    parse_obj = data["parse"]
    rev_id = int(parse_obj["revid"])
    canonical_title = str(parse_obj["title"])
    html_body = str(parse_obj["text"]["*"])
    slug = re.sub(r"[^a-z0-9]+", "-", canonical_title.lower()).strip("-")
    page_url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(canonical_title.replace(' ', '_'))}"
    return parse_mediawiki_html(
        html_text=html_body,
        slug=slug,
        title=canonical_title,
        page_url=page_url,
        revision_id=rev_id,
    )
