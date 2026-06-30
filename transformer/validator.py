from __future__ import annotations

from typing import Any


CANONICAL_FIELDS = {
    "candidate_id",
    "full_name",
    "emails",
    "phones",
    "location",
    "links",
    "headline",
    "years_experience",
    "skills",
    "experience",
    "education",
    "provenance",
    "conflicts",
    "match_confidence",
    "overall_confidence",
}


def validate_canonical(profile: dict[str, Any]) -> None:
    missing = CANONICAL_FIELDS - set(profile)
    if missing:
        raise ValueError(f"Canonical profile missing fields: {sorted(missing)}")
    if not isinstance(profile["candidate_id"], str):
        raise TypeError("candidate_id must be a string")
    _is_optional_string(profile["full_name"], "full_name")
    _is_string_list(profile["emails"], "emails")
    _is_string_list(profile["phones"], "phones")
    _validate_location(profile["location"])
    _validate_links(profile["links"])
    _is_optional_string(profile["headline"], "headline")
    if profile["years_experience"] is not None and not isinstance(profile["years_experience"], (int, float)):
        raise TypeError("years_experience must be a number or null")
    _validate_skills(profile["skills"])
    _validate_experience(profile["experience"])
    _validate_education(profile["education"])
    _validate_provenance(profile["provenance"])
    if not isinstance(profile["conflicts"], dict):
        raise TypeError("conflicts must be an object")
    _validate_score(profile["match_confidence"], "match_confidence")
    _validate_score(profile["overall_confidence"], "overall_confidence")


def validate_projected(projected: dict[str, Any], config: dict[str, Any]) -> None:
    """Validate the requested output contract after projection.

    For custom projections the requested schema is the config's field list and
    missing behavior. Full canonical validation is still run before projection.
    """

    fields = config.get("fields")
    if fields is None:
        validate_canonical(projected)
        return
    requested_targets = []
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, str):
                requested_targets.append(str(field))
            elif isinstance(field, dict):
                requested_targets.append(str(field.get("path") or field.get("name") or field.get("from")))
    elif isinstance(fields, dict):
        for source_name, spec in fields.items():
            if isinstance(spec, str):
                requested_targets.append(spec)
            elif isinstance(spec, dict):
                requested_targets.append(str(spec.get("rename", source_name)))
            else:
                requested_targets.append(str(source_name))
    if config.get("on_missing", "null") != "omit":
        missing = set(requested_targets) - set(projected)
        if missing:
            raise ValueError(f"Projected profile missing requested fields: {sorted(missing)}")


def _is_optional_string(value: Any, field: str) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{field} must be a string or null")


def _is_string_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{field} must be a string list")


def _validate_location(value: Any) -> None:
    if not isinstance(value, dict):
        raise TypeError("location must be an object")
    for key in ("city", "region", "country"):
        _is_optional_string(value.get(key), f"location.{key}")


def _validate_links(value: Any) -> None:
    if not isinstance(value, dict):
        raise TypeError("links must be an object")
    for key in ("linkedin", "github", "portfolio"):
        _is_optional_string(value.get(key), f"links.{key}")
    _is_string_list(value.get("other"), "links.other")


def _validate_skills(value: Any) -> None:
    if not isinstance(value, list):
        raise TypeError("skills must be a list")
    for skill in value:
        if not isinstance(skill, dict):
            raise TypeError("each skill must be an object")
        if not isinstance(skill.get("name"), str):
            raise TypeError("skill.name must be a string")
        _validate_score(skill.get("confidence"), "skill.confidence")
        _is_string_list(skill.get("sources"), "skill.sources")


def _validate_experience(value: Any) -> None:
    if not isinstance(value, list):
        raise TypeError("experience must be a list")
    for item in value:
        for key in ("company", "title", "start", "end", "summary"):
            _is_optional_string(item.get(key), f"experience.{key}")


def _validate_education(value: Any) -> None:
    if not isinstance(value, list):
        raise TypeError("education must be a list")
    for item in value:
        for key in ("institution", "degree", "field"):
            _is_optional_string(item.get(key), f"education.{key}")
        if item.get("end_year") is not None and not isinstance(item.get("end_year"), int):
            raise TypeError("education.end_year must be an integer or null")


def _validate_provenance(value: Any) -> None:
    if not isinstance(value, list):
        raise TypeError("provenance must be a list")
    for item in value:
        for key in ("field", "source", "method"):
            if not isinstance(item.get(key), str):
                raise TypeError(f"provenance.{key} must be a string")
        if "confidence" in item:
            _validate_score(item.get("confidence"), "provenance.confidence")


def _validate_score(value: Any, field: str) -> None:
    if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{field} must be a 0.0-1.0 score")
