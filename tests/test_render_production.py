import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import render_production  # noqa: E402

DIGEST = "sha256:" + "a" * 64
IMAGE = f"ghcr.io/example/bifrost@{DIGEST}"
TEMPLATE = """# Bifrost distribution {{VERSION}}
services:
  bifrost:
    image: "${BIFROST_IMAGE:?BIFROST_IMAGE must pin an immutable image reference}"
    labels:
      version: "{{VERSION}}"
      upstream: "{{UPSTREAM_TAG}}"
"""


class RenderProductionTests(unittest.TestCase):
    def test_renders_digest_pinned_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "deploy" / "coolify" / "compose.yaml"
            template.parent.mkdir(parents=True)
            template.write_text(TEMPLATE, encoding="utf-8")

            code = render_production.main(
                [
                    "--root",
                    str(root),
                    "--image",
                    IMAGE,
                    "--version",
                    "v2.4.0",
                    "--upstream-tag",
                    "transports/v2.4.0",
                    "--upstream-commit",
                    "abc123",
                    "--output-dir",
                    "dist/production",
                ]
            )
            self.assertEqual(code, 0)
            compose = (root / "dist" / "production" / "compose.yaml").read_text(encoding="utf-8")
            self.assertIn(IMAGE, compose)
            self.assertIn("transports/v2.4.0", compose)
            self.assertNotIn("{{", compose)
            release = (root / "dist" / "production" / "release.json").read_text(encoding="utf-8")
            self.assertIn("sha256:", release)

    def test_rejects_mutable_tags_by_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = root / "deploy" / "coolify" / "compose.yaml"
            template.parent.mkdir(parents=True)
            template.write_text(TEMPLATE, encoding="utf-8")
            code = render_production.main(
                [
                    "--root",
                    str(root),
                    "--image",
                    "ghcr.io/example/bifrost:v2.4.0",
                    "--version",
                    "v2.4.0",
                ]
            )
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
