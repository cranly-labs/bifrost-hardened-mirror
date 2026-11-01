import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sync_upstream  # noqa: E402


class VersionKeyTests(unittest.TestCase):
    def test_semver_ordering(self):
        tags = [
            "transports/v2.9.9",
            "transports/v2.10.0",
            "transports/v2.4.0",
            "transports/v2.10.0-rc.1",
        ]
        ordered = sorted(tags, key=sync_upstream.version_key)
        self.assertEqual(
            ordered,
            [
                "transports/v2.4.0",
                "transports/v2.9.9",
                "transports/v2.10.0-rc.1",
                "transports/v2.10.0",
            ],
        )

    def test_rejects_unparseable_tag(self):
        with self.assertRaises(sync_upstream.SyncError):
            sync_upstream.version_key("transports/nightly")


class TreeDigestTests(unittest.TestCase):
    def test_digest_is_deterministic_and_sensitive_to_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a").mkdir()
            (root / "a" / "file.txt").write_text("one\n", encoding="utf-8")
            first, count = sync_upstream.tree_digest(root)
            second, _ = sync_upstream.tree_digest(root)
            self.assertEqual(first, second)
            self.assertEqual(count, 1)

            (root / "a" / "file.txt").write_text("two\n", encoding="utf-8")
            third, _ = sync_upstream.tree_digest(root)
            self.assertNotEqual(first, third)

    def test_digest_includes_executable_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "run.sh"
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            script.chmod(0o644)
            before, _ = sync_upstream.tree_digest(root)
            script.chmod(0o755)
            after, _ = sync_upstream.tree_digest(root)
            self.assertNotEqual(before, after)


class SparsePatternTests(unittest.TestCase):
    def test_documentation_media_is_excluded(self):
        patterns = sync_upstream._sparse_patterns()
        self.assertIn("/*", patterns)
        self.assertIn("!/docs/media/", patterns)
        self.assertIn("!.github", patterns)


if __name__ == "__main__":
    unittest.main()
