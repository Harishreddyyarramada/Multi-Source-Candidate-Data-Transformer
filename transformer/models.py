from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceValue:
    """A candidate value plus the evidence needed to make merge decisions.

    Keeping method/source next to the value makes provenance deterministic and
    auditable, which is important for the "never invent values" requirement.
    """

    field: str
    value: Any
    source: str
    method: str
    structured: bool
    confidence: float


@dataclass
class ExtractedCandidate:
    """Standard internal representation emitted by every extractor."""

    source: str
    candidate_key: str
    values: list[SourceValue] = field(default_factory=list)


@dataclass(frozen=True)
class ProvenanceEntry:
    field: str
    source: str
    method: str
    value: Any | None = None
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"field": self.field, "source": self.source, "method": self.method}
        if self.value is not None:
            data["value"] = self.value
        if self.confidence is not None:
            data["confidence"] = round(self.confidence, 2)
        return data


@dataclass(frozen=True)
class Skill:
    name: str
    confidence: float
    sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "confidence": round(self.confidence, 2),
            "sources": sorted(self.sources),
        }


@dataclass
class CandidateProfile:
    """Canonical profile shape required by the assignment."""

    candidate_id: str
    full_name: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    location: dict[str, str | None] = field(
        default_factory=lambda: {"city": None, "region": None, "country": None}
    )
    links: dict[str, Any] = field(
        default_factory=lambda: {
            "linkedin": None,
            "github": None,
            "portfolio": None,
            "other": [],
        }
    )
    headline: str | None = None
    years_experience: float | None = None
    skills: list[Skill] = field(default_factory=list)
    experience: list[dict[str, Any]] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    conflicts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    field_confidence: dict[str, float] = field(default_factory=dict)
    match_confidence: float = 1.0
    overall_confidence: float = 0.0

    def to_dict(self, include_confidence: bool = True) -> dict[str, Any]:
        """Return the exact canonical JSON-serializable schema.

        Field-level confidence is intentionally optional runtime metadata; the
        schema only requires skill confidence and overall_confidence.
        """

        data: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "full_name": self.full_name,
            "emails": self.emails,
            "phones": self.phones,
            "location": self.location,
            "links": self.links,
            "headline": self.headline,
            "years_experience": self.years_experience,
            "skills": [skill.to_dict() for skill in self.skills],
            "experience": self.experience,
            "education": self.education,
            "provenance": [entry.to_dict() for entry in self.provenance],
            "conflicts": self.conflicts,
            "match_confidence": round(self.match_confidence, 2),
            "overall_confidence": round(self.overall_confidence, 2),
        }
        if include_confidence:
            data["confidence"] = {
                key: round(value, 2)
                for key, value in sorted(self.field_confidence.items())
            }
        return data
