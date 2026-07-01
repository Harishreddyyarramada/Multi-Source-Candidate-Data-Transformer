import tempfile
import unittest
from pathlib import Path

from transformer.extractor.github_extractor import read_usernames


class GitHubExtractorTests(unittest.TestCase):
    def test_read_usernames_cleans_urls_handles_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "github_usernames.txt"
            path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "@octocat",
                        "https://github.com/octocat/",
                        "github.com/eightfold",
                        "plain-user",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(read_usernames(path), ["octocat", "eightfold", "plain-user"])


if __name__ == "__main__":
    unittest.main()
