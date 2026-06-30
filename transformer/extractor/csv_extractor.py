from __future__ import annotations

import csv
import logging
from pathlib import Path

from transformer.models import ExtractedCandidate, SourceValue
from transformer.normalizer import (
    extract_skills_from_text,
    normalize_email,
    normalize_location,
    normalize_name,
    normalize_phone,
    normalize_skill,
)

LOGGER = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"name", "email", "phone", "current_company", "title"}
OPTIONAL_COLUMNS = {
    "location",
    "linkedin_url",
    "github_username",
    "github_url",
    "portfolio_url",
    "skills",
    "years_experience",
    "resume_url",
    "source",
    "status",
}


def detect(path: str | Path) -> bool:
    csv_path = Path(path)
    if not csv_path.exists() or not csv_path.is_file():
        LOGGER.warning("Recruiter CSV not found: %s", csv_path)
        return False
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            return reader.fieldnames is not None
    except OSError as exc:
        LOGGER.warning("Recruiter CSV is not readable: %s", exc)
        return False


def extract(path: str | Path, default_phone_region: str = "IN") -> list[ExtractedCandidate]:
    """Extract recruiter CSV rows into the shared internal representation.

    Unknown columns are ignored so upstream exports can add fields without
    breaking deterministic behavior. Missing expected columns simply produce
    null/missing values later in the pipeline.
    """

    csv_path = Path(path)
    candidates: list[ExtractedCandidate] = []
    seen_emails: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        known_columns = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        extra = set(reader.fieldnames or []) - known_columns
        if missing:
            LOGGER.warning("Recruiter CSV missing columns: %s", sorted(missing))
        if extra:
            LOGGER.info("Recruiter CSV extra columns ignored: %s", sorted(extra))

        for row_number, row in enumerate(reader, start=2):
            email = normalize_email(row.get("email"))
            if email and email in seen_emails:
                LOGGER.warning("Duplicate CSV candidate skipped by email on row %s: %s", row_number, email)
                continue
            if email:
                seen_emails.add(email)

            name = normalize_name(row.get("name"))
            candidate_key = email or normalize_name(row.get("name")) or f"csv-row-{row_number}"
            record = ExtractedCandidate(source="recruiter_csv", candidate_key=str(candidate_key))

            _add_value(record, "full_name", name, "csv_column:name", 0.75)
            _add_value(record, "emails", email, "csv_column:email", 0.75)
            phone = normalize_phone(row.get("phone"), default_region=default_phone_region)
            _add_value(record, "phones", phone, "csv_column:phone", 0.75)
            _add_value(record, "location", normalize_location(row.get("location")), "csv_column:location", 0.75)
            _add_value(record, "links.linkedin", _clean_url(row.get("linkedin_url")), "csv_column:linkedin_url", 0.75)
            _add_value(record, "links.github", _github_url(row), "csv_column:github_url", 0.75)
            _add_value(record, "identity.github_username", _github_username(row), "csv_column:github_username", 0.95)
            _add_value(record, "links.portfolio", _clean_url(row.get("portfolio_url")), "csv_column:portfolio_url", 0.75)
            _add_value(record, "links.other", _clean_url(row.get("resume_url")), "csv_column:resume_url", 0.65)
            _add_value(record, "years_experience", _parse_years(row.get("years_experience")), "csv_column:years_experience", 0.75)

            for skill in _split_skills(row.get("skills")):
                _add_value(record, "skills", skill, "csv_column:skills", 0.75)

            company = normalize_name(row.get("current_company"))
            title = normalize_name(row.get("title"))
            if company or title:
                # The canonical experience object has more fields than CSV
                # provides, so missing dates/summary remain null by design.
                _add_value(
                    record,
                    "experience",
                    {
                        "company": company,
                        "title": title,
                        "start": None,
                        "end": None,
                        "summary": None,
                    },
                    "csv_columns:current_company,title",
                    0.75,
                )
            candidates.append(record)
    return candidates


def _clean_url(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    return f"https://{text}"


def _github_username(row: dict[str, str]) -> str | None:
    username = normalize_name(row.get("github_username"))
    if username:
        return username.lstrip("@").split("/")[-1]
    url = _clean_url(row.get("github_url"))
    if not url:
        return None
    return url.rstrip("/").split("/")[-1] or None


def _github_url(row: dict[str, str]) -> str | None:
    url = _clean_url(row.get("github_url"))
    if url:
        return url
    username = _github_username(row)
    return f"https://github.com/{username}" if username else None


def _parse_years(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _split_skills(value: object) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text.strip("[]")
    raw_items = []
    for chunk in text.replace("|", ",").replace(";", ",").split(","):
        raw_items.extend(extract_skills_from_text(chunk) or [chunk])
    normalized = [normalize_skill(item.strip().strip("\"'")) for item in raw_items]
    return sorted({skill for skill in normalized if skill})


def _add_value(
    record: ExtractedCandidate,
    field: str,
    value: object,
    method: str,
    confidence: float,
) -> None:
    if value is None:
        return
    record.values.append(
        SourceValue(
            field=field,
            value=value,
            source=record.source,
            method=method,
            structured=True,
            confidence=confidence,
        )
    )
