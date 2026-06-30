from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import phonenumbers
import pycountry


COMMON_SKILLS = {
    "aws",
    "azure",
    "c",
    "c++",
    "css",
    "django",
    "docker",
    "fastapi",
    "flask",
    "go",
    "graphql",
    "html",
    "java",
    "javascript",
    "kubernetes",
    "machine learning",
    "mongodb",
    "mysql",
    "next.js",
    "node.js",
    "pandas",
    "postgresql",
    "python",
    "react",
    "redis",
    "rust",
    "sql",
    "tensorflow",
    "typescript",
}

LANGUAGE_TO_SKILL = {
    "C#": "c#",
    "C++": "c++",
    "CSS": "css",
    "Go": "go",
    "HTML": "html",
    "Java": "java",
    "JavaScript": "javascript",
    "Jupyter Notebook": "python",
    "Python": "python",
    "Ruby": "ruby",
    "Rust": "rust",
    "Shell": "shell",
    "TypeScript": "typescript",
}


def normalize_email(value: Any) -> str | None:
    if value is None:
        return None
    email = str(value).strip().lower()
    if not email:
        return None
    # Conservative validation avoids inventing corrected addresses.
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return email
    return None


def normalize_phone(value: Any, default_region: str = "IN") -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, default_region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_date_yyyy_mm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%Y", "%b %Y", "%B %Y", "%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return f"{parsed.year:04d}-{parsed.month:02d}"
        except ValueError:
            continue
    return None


def normalize_country(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if len(text) == 2:
            country = pycountry.countries.get(alpha_2=text.upper())
        elif len(text) == 3:
            country = pycountry.countries.get(alpha_3=text.upper())
        else:
            country = pycountry.countries.lookup(text)
    except LookupError:
        return None
    return country.alpha_2 if country else None


def normalize_location(value: Any) -> dict[str, str | None] | None:
    """Best-effort location normalization without guessing missing parts.

    GitHub location is free text. We only map a country when pycountry can
    recognize a token; city/region remain literal cleaned tokens.
    """

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    parts = [part.strip().strip(".;:") for part in re.split(r",|\|", text) if part.strip().strip(".;:")]
    country = None
    remaining: list[str] = []
    for part in parts:
        parsed_country = normalize_country(part)
        if parsed_country and country is None:
            country = parsed_country
        else:
            remaining.append(part)

    city = remaining[0] if len(remaining) >= 1 else None
    region = remaining[1] if len(remaining) >= 2 else None
    return {"city": city, "region": region, "country": country}


def normalize_skill(value: Any) -> str | None:
    if value is None:
        return None
    skill = re.sub(r"\s+", " ", str(value).strip().lower())
    aliases = {
        "js": "javascript",
        "node": "node.js",
        "nodejs": "node.js",
        "postgres": "postgresql",
        "py": "python",
        "ts": "typescript",
    }
    skill = aliases.get(skill, skill)
    return skill or None


def extract_skills_from_text(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value).lower()
    found = []
    for skill in sorted(COMMON_SKILLS):
        pattern = r"(?<![\w.+#-])" + re.escape(skill) + r"(?![\w.+#-])"
        if re.search(pattern, text):
            found.append(skill)
    return found


def normalize_name(value: Any) -> str | None:
    if value is None:
        return None
    name = re.sub(r"\s+", " ", str(value).strip())
    return name or None


def stable_candidate_id(email: str | None, name: str | None, github_username: str | None = None) -> str:
    """Build a deterministic human-readable ID from stable input fields."""

    basis = email or github_username or name or "unknown"
    slug = re.sub(r"[^a-z0-9]+", "-", basis.lower()).strip("-")
    return slug or "unknown"
