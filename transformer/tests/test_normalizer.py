import unittest

from transformer.normalizer import (
    extract_skills_from_text,
    normalize_country,
    normalize_date_yyyy_mm,
    normalize_email,
    normalize_location,
    normalize_phone,
    normalize_skill,
)


class NormalizerTests(unittest.TestCase):
    def test_phone_normalizes_indian_local_number_to_e164(self):
        self.assertEqual(normalize_phone("9876543210", default_region="IN"), "+919876543210")

    def test_invalid_phone_becomes_null(self):
        self.assertIsNone(normalize_phone("123", default_region="US"))

    def test_email_is_lowercase_or_null(self):
        self.assertEqual(normalize_email("USER@Example.COM "), "user@example.com")
        self.assertIsNone(normalize_email("not-an-email"))

    def test_date_formats_to_year_month(self):
        self.assertEqual(normalize_date_yyyy_mm("Jan 2024"), "2024-01")
        self.assertEqual(normalize_date_yyyy_mm("2024"), "2024-01")

    def test_country_becomes_alpha_2(self):
        self.assertEqual(normalize_country("India"), "IN")
        self.assertEqual(normalize_country("usa"), "US")

    def test_location_does_not_guess_missing_country(self):
        self.assertEqual(normalize_location("Bengaluru, India"), {"city": "Bengaluru", "region": None, "country": "IN"})
        self.assertEqual(normalize_location("Remote"), {"city": "Remote", "region": None, "country": None})

    def test_skills_are_canonical_lowercase(self):
        self.assertEqual(normalize_skill(" JS "), "javascript")
        self.assertIn("python", extract_skills_from_text("Python and React developer"))

    def test_skill_aliases_and_typos_deduplicate_to_canonical_name(self):
        self.assertEqual(normalize_skill("ML"), "machine learning")
        self.assertEqual(normalize_skill("achiine laenring"), "machine learning")
        self.assertEqual(normalize_skill("k8s"), "kubernetes")
        self.assertEqual(normalize_skill("reactjs"), "react")
        self.assertEqual(normalize_skill("sklearn"), "scikit-learn")
        self.assertEqual(
            extract_skills_from_text("Worked on ML, k8s, reactjs and achiine laenring systems"),
            ["kubernetes", "machine learning", "react"],
        )


if __name__ == "__main__":
    unittest.main()
