from __future__ import annotations

import logging
import re
from pathlib import Path

from transformer.models import ExtractedCandidate, SourceValue
from transformer.normalizer import extract_skills_from_text, normalize_email, normalize_location, normalize_name, normalize_phone

LOGGER = logging.getLogger(__name__)


def detect(path: str | Path | None) -> bool:
    if path is None:
        return False
    notes_path = Path(path)
    if not notes_path.exists() or not notes_path.is_file():
        LOGGER.warning("Recruiter notes file not found: %s", notes_path)
        return False
    return True


def extract(path: str | Path, default_phone_region: str = "IN") -> list[ExtractedCandidate]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = [block.strip() for block in re.split(r"\n\s*\n|---+", text) if block.strip()]
    if not blocks and text.strip():
        blocks = [text.strip()]

    records = []
    for index, block in enumerate(blocks, start=1):
        email = _first_email(block)
        name = _extract_name(block)
        candidate_key = email or name or f"notes-block-{index}"
        record = ExtractedCandidate(source="recruiter_notes", candidate_key=str(candidate_key))

        _add_value(record, "full_name", name, "notes:first_named_line", 0.55)
        _add_value(record, "emails", email, "regex:email", 0.8)
        for phone in _phones(block, default_phone_region):
            _add_value(record, "phones", phone, "phonenumbers:phone", 0.75)
        _add_value(record, "location", _extract_location(block), "notes:location_phrase", 0.45)

        for label, field in (("linkedin", "links.linkedin"), ("github", "links.github"), ("portfolio", "links.portfolio")):
            _add_value(record, field, _extract_url(block, label), f"regex:{label}_url", 0.65)

        for skill in extract_skills_from_text(block):
            _add_value(record, "skills", skill, "notes:skill_parse", 0.45)

        experience = _extract_experience(block)
        if experience:
            _add_value(record, "experience", experience, "notes:experience_phrase", 0.45)
        records.append(record)
    return records


def _first_email(text: str) -> str | None:
    match = re.search(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+", text)
    return normalize_email(match.group(0)) if match else None


def _phones(text: str, default_region: str) -> list[str]:
    phones = set()
    for match in re.finditer(r"(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?){2,5}\d{2,5}", text):
        phone = normalize_phone(match.group(0), default_region=default_region)
        if phone:
            phones.add(phone)
    return sorted(phones)


def _extract_name(text: str) -> str | None:
    for line in text.splitlines():
        cleaned = normalize_name(re.sub(r"^(name|candidate)\s*:\s*", "", line.strip(), flags=re.I))
        if not cleaned or "@" in cleaned or len(cleaned.split()) > 5:
            continue
        if re.search(r"\d|https?://", cleaned, flags=re.I):
            continue
        return cleaned
    return None


def _extract_location(text: str) -> dict[str, str | None] | None:
    match = re.search(r"(?:location|from|based in)\s*[:\-]?\s*([A-Za-z .'-]+(?:,\s*[A-Za-z .'-]+){0,2})", text, flags=re.I)
    return normalize_location(match.group(1)) if match else None


def _extract_url(text: str, label: str) -> str | None:
    pattern = {
        "linkedin": r"https?://(?:www\.)?linkedin\.com/[^\s,;]+",
        "github": r"https?://(?:www\.)?github\.com/[^\s,;]+",
        "portfolio": r"https?://[^\s,;]+",
    }[label]
    for match in re.finditer(pattern, text, flags=re.I):
        url = match.group(0).rstrip(").]")
        if label == "portfolio" and ("linkedin.com" in url or "github.com" in url):
            continue
        return url
    return None


def _extract_experience(text: str) -> dict[str, str | None] | None:
    match = re.search(r"(?:at|company)\s+([A-Za-z0-9 .&'-]+)(?:\s+as\s+|\s*[-,]\s*)([A-Za-z0-9 .&'/+-]+)", text, flags=re.I)
    if not match:
        return None
    return {
        "company": normalize_name(match.group(1)),
        "title": normalize_name(match.group(2)),
        "start": None,
        "end": None,
        "summary": None,
    }


def _add_value(record: ExtractedCandidate, field: str, value: object, method: str, confidence: float) -> None:
    if value is None:
        return
    record.values.append(
        SourceValue(
            field=field,
            value=value,
            source=record.source,
            method=method,
            structured=False,
            confidence=confidence,
        )
    )
