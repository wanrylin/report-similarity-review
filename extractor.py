"""Extract text from a PDF or DOCX, optionally limiting it to named sections."""

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pdfplumber


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

_NUMBERED_HEADING = re.compile(
    r"^(?:(?:chapter|section)\s+)?(\d{1,2}(?:\.\d{1,2})*)"
    r"(?:\s*[.):–—-]\s*|\s+)([^\d\s].*)$",
    re.IGNORECASE,
)
_WORD_HEADING_STYLE = re.compile(r"heading\s*([1-9])", re.IGNORECASE)
_WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_BACK_MATTER = {"references", "bibliography", "appendix", "appendices"}
_STANDARD_HEADINGS = {
    "abstract", "acknowledgments", "acknowledgements", "analysis", "background",
    "conclusion", "conclusions", "discussion", "evaluation", "experimental setup",
    "implementation", "introduction", "limitations", "literature review", "method",
    "methods", "methodology", "objective", "objectives", "overview", "related work",
    "results", "results and discussion", "discussion and conclusion", "future work",
    "table of contents",
} | _BACK_MATTER


def _pdf_lines(path):
    with pdfplumber.open(path) as pdf:
        return [
            (line, None)
            for page in pdf.pages
            for line in (page.extract_text() or "").splitlines()
        ]


def _docx_lines(path):
    with ZipFile(path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))

    lines = []
    for paragraph in document.iter(_WORD + "p"):
        text = "".join(node.text or "" for node in paragraph.iter(_WORD + "t"))
        style = paragraph.find(f"{_WORD}pPr/{_WORD}pStyle")
        style_name = style.get(_WORD + "val", "") if style is not None else ""
        match = _WORD_HEADING_STYLE.fullmatch(style_name)
        level = int(match[1]) if match else None
        lines.append((text, level))
    return lines


def _normalize_heading(text):
    text = " ".join(text.strip().rstrip(":").casefold().split())
    return "conclusion" if text == "conclusions" else text


def _is_back_matter(key):
    return key in _BACK_MATTER or bool(re.match(r"^appendix\s+[a-z0-9]\b", key))


def _identify_heading(text, style_level, requested):
    raw = text.strip().rstrip(":").strip()
    numbered = _NUMBERED_HEADING.match(raw)
    title = numbered[2] if numbered else raw
    key = _normalize_heading(title)

    numbered_title = (
        numbered is not None and 0 < len(title) <= 80
        and not title.endswith((".", "?", "!")) and len(title.split()) <= 12
    )
    combined_heading = key in {"results and discussion", "discussion and conclusion"}
    matches = key in requested or (
        combined_heading and any(part in requested for part in key.split(" and "))
    )
    back_matter = _is_back_matter(key)
    if style_level is None and not (
        numbered_title or matches or back_matter or key in _STANDARD_HEADINGS
    ):
        return None
    level = style_level or (numbered[1].count(".") + 1 if numbered else 1)
    return level, title, matches, back_matter


def _select_sections(lines, sections):
    requested = {_normalize_heading(title) for title in sections}
    headings = []
    found = {}
    selected = []
    for text, level in lines:
        heading = _identify_heading(text, level, requested)
        if heading is not None:
            while headings and headings[-1][0] >= heading[0]:
                headings.pop()
            headings.append(heading)
        elif not any(blocked for _, _, _, blocked in headings):
            matches = [title for _, title, include, _ in headings if include]
            if matches:
                selected.append(text)
                if text.strip():
                    found.update(dict.fromkeys(matches))
    return "\n".join(selected).strip(), list(found)


def extract_document(path: Path, sections: list[str] | None, filename: str) -> dict:
    """Read the main document text and keep the requested sections, if supplied."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document type {suffix or '(no extension)'}")

    try:
        lines = _pdf_lines(path) if suffix == ".pdf" else _docx_lines(path)
    except Exception as exc:
        raise ValueError(f"Could not read {suffix[1:].upper()}: {exc}") from exc

    if sections is None:
        text = "\n".join(line for line, _ in lines).strip()
        found = []
    else:
        text, found = _select_sections(lines, sections)
    return {"filename": filename, "text": text, "sections_found": found}
