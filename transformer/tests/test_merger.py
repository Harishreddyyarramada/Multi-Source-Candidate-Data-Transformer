import unittest

from transformer.merger import merge_records
from transformer.models import ExtractedCandidate, SourceValue


def value(field, raw, source="recruiter_csv", structured=True, confidence=0.75, method="test"):
    return SourceValue(
        field=field,
        value=raw,
        source=source,
        method=method,
        structured=structured,
        confidence=confidence,
    )


class MergerTests(unittest.TestCase):
    def test_structured_name_beats_github_name(self):
        csv = ExtractedCandidate(
            source="recruiter_csv",
            candidate_key="asha@example.com",
            values=[
                value("full_name", "Asha Rao"),
                value("emails", "asha@example.com"),
            ],
        )
        github = ExtractedCandidate(
            source="github_api",
            candidate_key="asha",
            values=[
                value("full_name", "Asha R.", source="github_api", structured=False, confidence=0.55),
                value("links.github", "https://github.com/asha", source="github_api", structured=False, confidence=0.55),
            ],
        )

        profile = merge_records([csv, github])[0]

        self.assertEqual(profile.full_name, "Asha Rao")
        self.assertEqual(profile.links["github"], "https://github.com/asha")
        self.assertTrue(any(item.source == "github_api" for item in profile.provenance))

    def test_skills_union_and_multi_source_confidence(self):
        csv = ExtractedCandidate(
            source="recruiter_csv",
            candidate_key="a@example.com",
            values=[
                value("full_name", "Asha Rao"),
                value("emails", "a@example.com"),
                value("skills", "python"),
            ],
        )
        github = ExtractedCandidate(
            source="github_api",
            candidate_key="asha",
            values=[
                value("skills", "python", source="github_api", structured=False, confidence=0.4),
                value("skills", "react", source="github_api", structured=False, confidence=0.4),
            ],
        )

        profile = merge_records([csv, github])[0]
        skills = {skill.name: skill for skill in profile.skills}

        self.assertEqual(set(skills), {"python", "react"})
        self.assertEqual(skills["python"].confidence, 0.9)
        self.assertEqual(skills["react"].confidence, 0.4)

    def test_location_prefers_most_detailed(self):
        csv = ExtractedCandidate(source="recruiter_csv", candidate_key="a@example.com", values=[value("full_name", "Asha")])
        github = ExtractedCandidate(
            source="github_api",
            candidate_key="asha",
            values=[
                value(
                    "location",
                    {"city": "Bengaluru", "region": "Karnataka", "country": "IN"},
                    source="github_api",
                    structured=False,
                    confidence=0.4,
                )
            ],
        )

        profile = merge_records([csv, github])[0]

        self.assertEqual(profile.location["country"], "IN")
        self.assertEqual(profile.location["region"], "Karnataka")

    def test_github_username_matches_even_when_names_conflict(self):
        csv = ExtractedCandidate(
            source="recruiter_csv",
            candidate_key="asha@example.com",
            values=[
                value("full_name", "Asha Rao"),
                value("emails", "asha@example.com"),
                value("identity.github_username", "octocat", confidence=0.95),
            ],
        )
        github = ExtractedCandidate(
            source="github_api",
            candidate_key="octocat",
            values=[
                value("identity.github_username", "octocat", source="github_api", structured=False, confidence=0.95),
                value("full_name", "The Octocat", source="github_api", structured=False, confidence=0.55),
            ],
        )

        profile = merge_records([csv, github])[0]

        self.assertEqual(profile.full_name, "Asha Rao")
        self.assertEqual(profile.match_confidence, 0.95)
        self.assertIn("full_name", profile.conflicts)


if __name__ == "__main__":
    unittest.main()
