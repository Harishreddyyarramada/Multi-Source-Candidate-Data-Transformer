import unittest

from transformer.projector import project


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


if __name__ == "__main__":
    unittest.main()
