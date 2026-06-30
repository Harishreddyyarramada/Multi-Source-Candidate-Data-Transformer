from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from transformer.extractor import csv_extractor, github_extractor, notes_extractor
from transformer.merger import merge_records
from transformer.projector import project
from transformer.validator import validate_canonical, validate_projected

LOGGER = logging.getLogger(__name__)


def run_pipeline(
    csv_path: Path | None,
    github_usernames_path: Path | None,
    config_path: Path | None,
    output_path: Path,
    notes_path: Path | None = None,
    default_phone_region: str = "IN",
) -> list[dict[str, Any]]:
    config = _load_config(config_path)

    # 1. DETECT: keep unavailable sources from breaking the whole pipeline.
    available_sources = []
    if csv_path and csv_extractor.detect(csv_path):
        available_sources.append("csv")
    if github_usernames_path and github_extractor.detect(github_usernames_path):
        available_sources.append("github")
    if notes_path and notes_extractor.detect(notes_path):
        available_sources.append("notes")
    LOGGER.info("Available sources: %s", available_sources)

    # 2. EXTRACT: every extractor returns the same internal SourceValue shape.
    extracted = []
    if "csv" in available_sources:
        extracted.extend(csv_extractor.extract(csv_path, default_phone_region=default_phone_region))
    if "github" in available_sources:
        extracted.extend(github_extractor.extract(github_usernames_path))
    if "notes" in available_sources:
        extracted.extend(notes_extractor.extract(notes_path, default_phone_region=default_phone_region))

    # 3. NORMALIZE happens inside extractors so bad values can be nulled early.
    # 4. MERGE: combine records, resolve conflicts, and record provenance.
    # 5. CONFIDENCE: merger assigns field-level and overall scores.
    merged_profiles = merge_records(extracted)
    canonical_profiles = [profile.to_dict(include_confidence=config.get("include_confidence", True)) for profile in merged_profiles]

    # 6. PROJECT and 7. VALIDATE: validate canonical first, then requested shape.
    projected_profiles = []
    for profile in canonical_profiles:
        validate_canonical(profile)
        projected = project(profile, config)
        validate_projected(projected, config)
        projected_profiles.append(projected)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected_profiles, indent=2, sort_keys=True), encoding="utf-8")
    LOGGER.info(
        "Run summary: sources=%s extracted_records=%s profiles_emitted=%s",
        ",".join(available_sources) or "none",
        len(extracted),
        len(projected_profiles),
    )
    return projected_profiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-source candidate data transformer")
    parser.add_argument("--csv", type=Path, default=Path("transformer/sample_inputs/candidates.csv"))
    parser.add_argument("--github-usernames", type=Path, default=Path("transformer/sample_inputs/github_usernames.txt"))
    parser.add_argument("--notes", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=Path("transformer/config.json"))
    parser.add_argument("--output", type=Path, default=Path("transformer/output/default_output.json"))
    parser.add_argument("--default-phone-region", default="IN")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s:%(name)s:%(message)s")
    run_pipeline(
        csv_path=args.csv,
        github_usernames_path=args.github_usernames,
        notes_path=args.notes,
        config_path=args.config,
        output_path=args.output,
        default_phone_region=args.default_phone_region,
    )


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"fields": None, "include_confidence": True, "on_missing": "null"}
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    config = json.loads(path.read_text(encoding="utf-8"))
    config.setdefault("fields", None)
    config.setdefault("include_confidence", True)
    config.setdefault("on_missing", "null")
    return config


if __name__ == "__main__":
    main()
