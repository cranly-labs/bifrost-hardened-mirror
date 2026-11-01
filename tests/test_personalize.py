import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import personalize  # noqa: E402


class PersonalizeTests(unittest.TestCase):
    def test_replaces_repository_tokens(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            readme = root / "README.md"
            readme.write_text(
                "https://github.com/OWNER/REPO\n"
                "https://github.com/OWNER/REPO/pkgs/container/REPO\n"
                "https://img.shields.io/badge/image-ghcr.io%2FOWNER%2FREPO-blue\n"
                "ghcr.io/OWNER/REPO:v1\n",
                encoding="utf-8",
            )
            owners = root / ".github" / "CODEOWNERS"
            owners.parent.mkdir()
            owners.write_text("* @OWNER\n", encoding="utf-8")

            self.assertEqual(
                personalize.main(
                    ["--root", str(root), "--owner", "acme", "--repo", "gateway"]
                ),
                0,
            )
            text = readme.read_text(encoding="utf-8")
            self.assertIn("https://github.com/acme/gateway", text)
            self.assertIn("https://github.com/acme/gateway/pkgs/container/gateway", text)
            self.assertIn("ghcr.io%2Facme%2Fgateway", text)
            self.assertIn("ghcr.io/acme/gateway:v1", text)
            self.assertEqual(owners.read_text(encoding="utf-8"), "* @acme\n")

    def test_check_mode_reports_pending_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("OWNER/REPO\n", encoding="utf-8")
            self.assertEqual(
                personalize.main(
                    ["--root", str(root), "--owner", "acme", "--repo", "gateway", "--check"]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
