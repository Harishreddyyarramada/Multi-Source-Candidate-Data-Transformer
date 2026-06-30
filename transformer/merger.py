from __future__ import annotations

from collections import defaultdict
from typing import Any

from transformer.models import CandidateProfile, ExtractedCandidate, ProvenanceEntry, Skill, SourceValue
from transformer.normalizer import stable_candidate_id

LIST_FIELDS = {"emails", "phones"}
SCALAR_FIELDS = {"full_name", "headline", "years_experience"}


def merge_records(records: list[ExtractedCandidate]) -> list[CandidateProfile]:
    """Merge extracted records into canonical candidate profiles.

    Matching is deliberately conservative: exact email wins, exact normalized
    name can join GitHub to CSV, and a single CSV plus single GitHub profile may
    be merged for the assignment demo. Otherwise unmatched GitHub records become
    separate profiles instead of being guessed onto a person.
    """

    groups = _group_records(records)
    return [_merge_group(group) for group in groups]


def _group_records(records: list[ExtractedCandidate]) -> list[list[ExtractedCandidate]]:
    csv_records = [record for record in records if record.source == "recruiter_csv"]
    github_records = [record for record in records if record.source == "github_api"]
    groups: list[list[ExtractedCandidate]] = []
    indexes: dict[str, dict[str, list[ExtractedCandidate]]] = {
        "email": {},
        "github": {},
        "phone": {},
        "name": {},
    }

    for record in records:
        target = _find_group(record, indexes)
        if target is None and record.source == "github_api" and len(csv_records) == 1 and len(github_records) == 1:
            target = groups[0] if groups else None
        if target is None:
            target = []
            groups.append(target)
        target.append(record)
        _index_record(record, target, indexes)
    return groups


def _merge_group(records: list[ExtractedCandidate]) -> CandidateProfile:
    values_by_field: dict[str, list[SourceValue]] = defaultdict(list)
    for record in records:
        for value in record.values:
            values_by_field[value.field].append(value)

    full_name, name_conf = _choose_scalar(values_by_field["full_name"])
    emails, email_conf = _merge_list(values_by_field["emails"])
    phones, phone_conf = _merge_list(values_by_field["phones"])
    location, location_conf = _choose_location(values_by_field["location"])
    headline, headline_conf = _choose_scalar(values_by_field["headline"])
    years_experience, years_conf = _choose_scalar(values_by_field["years_experience"])
    linkedin = _choose_scalar(values_by_field["links.linkedin"])[0]
    github = _choose_scalar(values_by_field["links.github"])[0]
    portfolio = _choose_scalar(values_by_field["links.portfolio"])[0]
    other_links, _ = _merge_list(values_by_field["links.other"])
    skills = _merge_skills(values_by_field["skills"])
    experience, experience_conf = _merge_experience(values_by_field["experience"])

    candidate_id = stable_candidate_id(
        emails[0] if emails else None,
        full_name,
        records[0].candidate_key if records else None,
    )
    profile = CandidateProfile(
        candidate_id=candidate_id,
        full_name=full_name,
        emails=emails,
        phones=phones,
        location=location,
        links={"linkedin": linkedin, "github": github, "portfolio": portfolio, "other": other_links},
        headline=headline,
        years_experience=years_experience,
        skills=skills,
        experience=experience,
        education=[],
    )

    confidence = {
        "full_name": name_conf,
        "emails": email_conf,
        "phones": phone_conf,
        "location": location_conf,
        "headline": headline_conf,
        "years_experience": years_conf,
        "skills": _average([skill.confidence for skill in skills]),
        "experience": experience_conf,
        "education": 0.0,
        "links": max([0.55 if github else 0.0, 0.75 if linkedin else 0.0, 0.75 if portfolio else 0.0, 0.65 if other_links else 0.0]),
    }
    profile.field_confidence = confidence
    profile.match_confidence = _match_confidence(records)
    profile.overall_confidence = _average(confidence.values())
    profile.provenance = _provenance(values_by_field)
    profile.conflicts = _conflicts(
        values_by_field,
        {
            "full_name": full_name,
            "headline": headline,
            "years_experience": years_experience,
            "location": location,
            "links.linkedin": linkedin,
            "links.github": github,
            "links.portfolio": portfolio,
        },
    )
    return profile


def _find_group(
    record: ExtractedCandidate,
    indexes: dict[str, dict[str, list[ExtractedCandidate]]],
) -> list[ExtractedCandidate] | None:
    for field, index_name in (
        ("emails", "email"),
        ("identity.github_username", "github"),
        ("phones", "phone"),
        ("full_name", "name"),
    ):
        for key in _field_keys(record.values, field):
            target = indexes[index_name].get(key)
            if target is not None:
                return target
    return None


def _index_record(
    record: ExtractedCandidate,
    group: list[ExtractedCandidate],
    indexes: dict[str, dict[str, list[ExtractedCandidate]]],
) -> None:
    for key in _field_keys(record.values, "emails"):
        indexes["email"][key] = group
    for key in _field_keys(record.values, "identity.github_username"):
        indexes["github"][key] = group
    for key in _field_keys(record.values, "phones"):
        indexes["phone"][key] = group
    for key in _field_keys(record.values, "full_name"):
        indexes["name"][key] = group


def _field_keys(values: list[SourceValue], field: str) -> list[str]:
    keys = []
    for value in values:
        if value.field == field and value.value:
            keys.append(str(value.value).strip().lower())
    return keys


def _choose_scalar(values: list[SourceValue]) -> tuple[Any, float]:
    if not values:
        return None, 0.0
    grouped: dict[str, list[SourceValue]] = defaultdict(list)
    for value in values:
        grouped[str(value.value)].append(value)
    if grouped:
        agreed = [items for items in grouped.values() if len({item.source for item in items}) >= 2]
        if agreed:
            chosen = sorted(agreed, key=lambda items: str(items[0].value))[0]
            return chosen[0].value, 0.9
    # Structured data beats unstructured for identity/contact fields; after
    # that, confidence and stable source order break ties.
    chosen_value = sorted(
        values,
        key=lambda item: (not item.structured, -item.confidence, item.source, item.method, str(item.value)),
    )[0]
    return chosen_value.value, chosen_value.confidence


def _merge_list(values: list[SourceValue]) -> tuple[list[str], float]:
    if not values:
        return [], 0.0
    seen: dict[str, list[SourceValue]] = defaultdict(list)
    for value in values:
        if value.value:
            seen[str(value.value)].append(value)
    output = sorted(seen)
    if any(len({item.source for item in items}) >= 2 for items in seen.values()):
        return output, 0.9
    best = max((item.confidence for items in seen.values() for item in items), default=0.0)
    return output, best


def _choose_location(values: list[SourceValue]) -> tuple[dict[str, str | None], float]:
    empty = {"city": None, "region": None, "country": None}
    if not values:
        return empty, 0.0
    chosen = sorted(
        values,
        key=lambda item: (
            -sum(1 for value in item.value.values() if value),
            not item.structured,
            -item.confidence,
            item.source,
        ),
    )[0]
    return {**empty, **chosen.value}, chosen.confidence


def _merge_skills(values: list[SourceValue]) -> list[Skill]:
    by_name: dict[str, list[SourceValue]] = defaultdict(list)
    for value in values:
        if value.value:
            by_name[str(value.value)].append(value)
    skills = []
    for name, items in sorted(by_name.items()):
        sources = sorted({item.source for item in items})
        confidence = 0.9 if len(sources) >= 2 else max(item.confidence for item in items)
        skills.append(Skill(name=name, confidence=confidence, sources=sources))
    return skills


def _merge_experience(values: list[SourceValue]) -> tuple[list[dict[str, Any]], float]:
    if not values:
        return [], 0.0
    seen = {}
    for value in values:
        key = (
            value.value.get("company"),
            value.value.get("title"),
            value.value.get("start"),
            value.value.get("end"),
        )
        seen[key] = value.value
    return list(seen.values()), max(value.confidence for value in values)


def _provenance(values_by_field: dict[str, list[SourceValue]]) -> list[ProvenanceEntry]:
    seen = set()
    entries = []
    for values in values_by_field.values():
        for value in values:
            key = (value.field, value.source, value.method, repr(value.value))
            if key in seen:
                continue
            seen.add(key)
            entries.append((value.field, value.source, value.method, value.value, value.confidence))
    return [
        ProvenanceEntry(field=field, source=source, method=method, value=value, confidence=confidence)
        for field, source, method, value, confidence in sorted(entries, key=lambda item: (item[0], item[1], item[2], repr(item[3])))
    ]


def _conflicts(values_by_field: dict[str, list[SourceValue]], chosen: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    conflicts: dict[str, list[dict[str, Any]]] = {}
    for field, values in values_by_field.items():
        if field not in chosen or len({repr(value.value) for value in values}) <= 1:
            continue
        winner = chosen[field]
        conflicts[field] = [
            {
                "value": value.value,
                "source": value.source,
                "method": value.method,
                "confidence": round(value.confidence, 2),
                "chosen": value.value == winner,
            }
            for value in sorted(values, key=lambda item: (item.source, item.method, repr(item.value)))
        ]
    return conflicts


def _match_confidence(records: list[ExtractedCandidate]) -> float:
    if len(records) <= 1:
        return 1.0
    values_by_field: dict[str, set[str]] = defaultdict(set)
    sources_by_value: dict[tuple[str, str], set[str]] = defaultdict(set)
    for record in records:
        for value in record.values:
            if value.field in {"emails", "identity.github_username", "phones", "full_name"} and value.value:
                normalized = str(value.value).strip().lower()
                values_by_field[value.field].add(normalized)
                sources_by_value[(value.field, normalized)].add(record.source)
    if any(field == "emails" and len(sources) >= 2 for (field, _), sources in sources_by_value.items()):
        return 0.98
    if any(field == "identity.github_username" and len(sources) >= 2 for (field, _), sources in sources_by_value.items()):
        return 0.95
    if any(field == "phones" and len(sources) >= 2 for (field, _), sources in sources_by_value.items()):
        return 0.9
    if any(field == "full_name" and len(sources) >= 2 for (field, _), sources in sources_by_value.items()):
        return 0.72
    return 0.55


def _first_value(values: list[SourceValue], field: str) -> Any:
    for value in values:
        if value.field == field:
            return value.value
    return None


def _average(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)
