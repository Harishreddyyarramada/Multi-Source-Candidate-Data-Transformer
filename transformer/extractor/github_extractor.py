from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import requests

from transformer.models import ExtractedCandidate, SourceValue
from transformer.normalizer import (
    LANGUAGE_TO_SKILL,
    extract_skills_from_text,
    normalize_location,
    normalize_name,
    normalize_skill,
)

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://api.github.com"
TIMEOUT_SECONDS = 5


def detect(usernames_path: str | Path | None) -> bool:
    if usernames_path is None:
        LOGGER.warning("GitHub usernames file not configured")
        return False
    path = Path(usernames_path)
    if not path.exists() or not path.is_file():
        LOGGER.warning("GitHub usernames file not found: %s", path)
        return False
    return True


def read_usernames(path: str | Path) -> list[str]:
    usernames = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        username = line.strip()
        if username and not username.startswith("#"):
            usernames.append(username)
    # Preserve input order while removing duplicates deterministically.
    return list(dict.fromkeys(usernames))


def extract(usernames_path: str | Path, session: requests.Session | None = None) -> list[ExtractedCandidate]:
    client = session or requests.Session()
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        client.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    candidates: list[ExtractedCandidate] = []
    for username in read_usernames(usernames_path):
        user = _get_json(client, f"{BASE_URL}/users/{username}")
        if user is None:
            continue

        record = ExtractedCandidate(source="github_api", candidate_key=username)
        github_url = user.get("html_url") or f"https://github.com/{username}"

        _add_value(record, "identity.github_username", username, "github_input:username", 0.95)
        _add_value(record, "full_name", normalize_name(user.get("name")), "github_user:name", 0.55)
        # GitHub bio can be None; we keep headline null rather than inventing "".
        _add_value(record, "headline", user.get("bio"), "github_user:bio", 0.55)
        _add_value(record, "location", normalize_location(user.get("location")), "github_user:location", 0.4)
        _add_value(record, "links.github", github_url, "github_user:html_url", 0.55)

        for skill in extract_skills_from_text(user.get("bio")):
            _add_value(record, "skills", skill, "github_user:bio_skill_parse", 0.4)

        repos = _get_json(client, f"{BASE_URL}/users/{username}/repos?per_page=100&sort=updated")
        if isinstance(repos, list):
            for repo in repos:
                for skill in _skills_from_repo(repo):
                    _add_value(record, "skills", skill, "github_repo:language_or_text", 0.4)

        candidates.append(record)
    return candidates


def _get_json(client: requests.Session, url: str) -> Any | None:
    try:
        response = client.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        LOGGER.warning("GitHub request failed for %s: %s", url, exc)
        return None
    if response.status_code == 404:
        LOGGER.warning("GitHub username not found for URL: %s", url)
        return None
    if response.status_code in {403, 429}:
        LOGGER.warning("GitHub rate limit or access limit returned %s for %s", response.status_code, url)
        return None
    if response.status_code >= 400:
        LOGGER.warning("GitHub request returned %s for %s", response.status_code, url)
        return None
    return response.json()


def _skills_from_repo(repo: dict[str, Any]) -> list[str]:
    skills: set[str] = set()
    language = repo.get("language")
    if language in LANGUAGE_TO_SKILL:
        skills.add(LANGUAGE_TO_SKILL[language])
    for field in ("name", "description", "topics"):
        value = repo.get(field)
        if isinstance(value, list):
            for item in value:
                skill = normalize_skill(item)
                if skill:
                    skills.add(skill)
        else:
            skills.update(extract_skills_from_text(value))
    return sorted(skills)


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
            structured=False,
            confidence=confidence,
        )
    )
