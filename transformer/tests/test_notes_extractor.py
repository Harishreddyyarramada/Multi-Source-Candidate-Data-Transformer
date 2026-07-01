import tempfile
import unittest
from pathlib import Path

from transformer.extractor.notes_extractor import extract


class NotesExtractorTests(unittest.TestCase):
    def test_notes_extract_contact_and_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text(
                "Asha Rao is based in Bengaluru, India.\nEmail: asha@example.com\nPhone: +91 98765 43210\nPython and React candidate.",
                encoding="utf-8",
            )

            records = extract(path)

        values = [(value.field, value.value) for value in records[0].values]
        self.assertIn(("full_name", "Asha Rao"), values)
        self.assertIn(("emails", "asha@example.com"), values)
        self.assertIn(("phones", "+919876543210"), values)
        self.assertIn(("skills", "python"), values)
        self.assertIn(("location", {"city": "Bengaluru", "region": None, "country": "IN"}), values)


if __name__ == "__main__":
    unittest.main()
