import json
import tempfile
import unittest
from pathlib import Path

from transformer.main import _load_config


class MainConfigTests(unittest.TestCase):
    def test_load_config_rejects_invalid_missing_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"on_missing": "guess"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                _load_config(path)

    def test_load_config_rejects_invalid_field_spec(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"fields": [123]}), encoding="utf-8")

            with self.assertRaises(TypeError):
                _load_config(path)


if __name__ == "__main__":
    unittest.main()
