from __future__ import annotations

from typing import Any

from transformer.normalizer import normalize_phone, normalize_skill


def project(profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Apply runtime shape config without changing extraction/merge code.

    Supported field specs:
      "fields": ["full_name", "emails"]
      "fields": {"full_name": "name", "emails": {"rename": "contact_emails"}}
      "fields": [{"path": "primary_email", "from": "emails[0]", "type": "string", "required": true}]
    """

    include_confidence = bool(config.get("include_confidence", True))
    on_missing = config.get("on_missing", "null")
    if on_missing not in {"null", "omit", "error"}:
        raise ValueError("on_missing must be one of: null, omit, error")

    source = dict(profile)
    if not include_confidence:
        source = _strip_confidence_metadata(source)

    fields = config.get("fields")
    if fields is None:
        return source

    output: dict[str, Any] = {}
    for spec in _field_specs(fields):
        if not include_confidence and _is_confidence_spec(spec):
            continue
        source_name = spec["from"]
        target_name = spec["path"]
        found, value = _get_path(source, source_name)
        if not found:
            if on_missing == "error":
                raise KeyError(f"Requested field is missing: {source_name}")
            if on_missing == "null" or spec.get("required"):
                output[target_name] = None
            continue
        if value is None and on_missing == "omit":
            continue
        value = _apply_normalize(value, spec.get("normalize"))
        _validate_type(value, spec.get("type"), target_name)
        output[target_name] = value
    return output


def _strip_confidence_metadata(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_confidence_metadata(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _strip_confidence_metadata(item)
            for key, item in value.items()
            if "confidence" not in str(key).lower()
        }
    return value


def _is_confidence_spec(spec: dict[str, Any]) -> bool:
    source_name = str(spec.get("from", "")).lower()
    target_name = str(spec.get("path", "")).lower()
    return "confidence" in source_name or "confidence" in target_name


def _field_specs(fields: Any) -> list[dict[str, Any]]:
    if isinstance(fields, list):
        specs = []
        for field in fields:
            if isinstance(field, str):
                specs.append({"from": field, "path": field})
            elif isinstance(field, dict):
                target = str(field.get("path") or field.get("name") or field.get("from"))
                source = str(field.get("from") or target)
                specs.append({**field, "from": source, "path": target})
            else:
                raise TypeError("field entries must be strings or objects")
        return specs
    if isinstance(fields, dict):
        specs = []
        for source_name, spec in fields.items():
            if isinstance(spec, str):
                target = spec
            elif isinstance(spec, dict):
                target = spec.get("rename") or spec.get("path") or source_name
            else:
                target = source_name
            specs.append({"from": str(source_name), "path": str(target)})
        return specs
    raise TypeError("fields must be a list, object, or null")


def _get_path(source: Any, path: str) -> tuple[bool, Any]:
    current = source
    for part in path.split("."):
        if isinstance(current, list):
            mapped = [_get_path(item, part) for item in current]
            current = [value for found, value in mapped if found]
            continue
        if part.endswith("[]"):
            key = part[:-2]
            if not isinstance(current, dict) or key not in current or not isinstance(current[key], list):
                return False, None
            current = current[key]
            continue
        if part.endswith("]") and "[" in part:
            key, index_text = part[:-1].split("[", 1)
            if not isinstance(current, dict) or key not in current or not isinstance(current[key], list):
                return False, None
            try:
                current = current[key][int(index_text)]
            except (ValueError, IndexError):
                return False, None
            continue
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _apply_normalize(value: Any, rule: Any) -> Any:
    if value is None or rule is None:
        return value
    rule_text = str(rule).lower()
    if rule_text == "e164":
        return normalize_phone(value)
    if rule_text == "canonical":
        if isinstance(value, list):
            return [skill for skill in (normalize_skill(item) for item in value) if skill]
        return normalize_skill(value)
    return value


def _validate_type(value: Any, expected: Any, field: str) -> None:
    if expected is None or value is None:
        return
    expected_text = str(expected)
    if expected_text == "string" and not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if expected_text == "string[]" and (not isinstance(value, list) or not all(isinstance(item, str) for item in value)):
        raise TypeError(f"{field} must be a string list")
    if expected_text == "number" and not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a number")
    if expected_text == "object" and not isinstance(value, dict):
        raise TypeError(f"{field} must be an object")
