import unittest

from transformer.projector import project
from transformer.validator import validate_projected


class ProjectorTests(unittest.TestCase):
    def test_assignment_style_field_specs_support_paths_and_arrays(self):
        profile = {
            "full_name": "Asha Rao",
            "emails": ["asha@example.com"],
            "phones": ["+919876543210"],
            "skills": [{"name": "Python"}, {"name": "React"}],
            "overall_confidence": 0.82,
        }
        config = {
            "fields": [
                {"path": "name", "from": "full_name", "type": "string", "required": True},
                {"path": "primary_email", "from": "emails[0]", "type": "string", "required": True},
                {"path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical"},
                {"path": "score", "from": "overall_confidence", "type": "number"},
            ],
            "include_confidence": True,
            "on_missing": "null",
        }

        output = project(profile, config)

        self.assertEqual(output["name"], "Asha Rao")
        self.assertEqual(output["primary_email"], "asha@example.com")
        self.assertEqual(output["skills"], ["python", "react"])
        self.assertEqual(output["score"], 0.82)

    def test_include_confidence_false_removes_confidence_from_default_output(self):
        profile = {
            "candidate_id": "asha-rao",
            "full_name": "Asha Rao",
            "emails": ["asha@example.com"],
            "phones": ["+919876543210"],
            "location": {"city": "Bengaluru", "region": None, "country": "India"},
            "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
            "headline": None,
            "years_experience": None,
            "skills": [{"name": "python", "confidence": 0.9, "sources": ["csv"]}],
            "experience": [],
            "education": [],
            "provenance": [{"field": "full_name", "source": "csv", "method": "test", "confidence": 0.8}],
            "conflicts": {},
            "confidence": {"full_name": 0.8},
            "match_confidence": 0.95,
            "overall_confidence": 0.82,
        }
        config = {"fields": None, "include_confidence": False, "on_missing": "null"}

        output = project(profile, config)

        validate_projected(output, config)
        self.assertFalse(_contains_confidence_key(output))

    def test_include_confidence_false_omits_custom_confidence_fields(self):
        profile = {
            "full_name": "Asha Rao",
            "emails": ["asha@example.com"],
            "overall_confidence": 0.82,
            "match_confidence": 0.95,
        }
        config = {
            "fields": [
                {"path": "name", "from": "full_name", "type": "string"},
                {"path": "score", "from": "overall_confidence", "type": "number"},
                {"path": "match_confidence", "type": "number"},
            ],
            "include_confidence": False,
            "on_missing": "null",
        }

        output = project(profile, config)

        validate_projected(output, config)
        self.assertEqual(output, {"name": "Asha Rao"})


def _contains_confidence_key(value):
    if isinstance(value, list):
        return any(_contains_confidence_key(item) for item in value)
    if isinstance(value, dict):
        return any("confidence" in str(key).lower() or _contains_confidence_key(item) for key, item in value.items())
    return False


if __name__ == "__main__":
    unittest.main()
