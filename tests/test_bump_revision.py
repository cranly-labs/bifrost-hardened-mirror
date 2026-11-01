import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import bump_revision  # noqa: E402
import sync_upstream  # noqa: E402


class BumpRevisionTests(unittest.TestCase):
    def test_increments_revision_and_versions_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = {
                "upstream": {
                    "repository": sync_upstream.UPSTREAM_REPOSITORY,
                    "tag": "transports/v2.4.0",
                    "version": "2.4.0",
                    "commit": "a" * 40,
                    "git_tree": "b" * 40,
                    "source_url": "https://github.com/maximhq/bifrost/tree/transports/v2.4.0",
                    "release_url": "https://github.com/maximhq/bifrost/releases/tag/transports%2Fv2.4.0",
                },
                "vendor": {
                    "directory": "upstream",
                    "tree_sha256": "c" * 64,
                    "file_count": 1,
                    "excluded": [],
                },
                "distribution": {
                    "revision": 1,
                    "generator": "scripts/sync_upstream.py",
                },
                "synced_at": "2026-11-01T00:00:00Z",
            }
            (root / "vendor.lock.json").write_text(json.dumps(lock), encoding="utf-8")
            self.assertEqual(bump_revision.main(["--root", str(root)]), 0)
            updated = json.loads((root / "vendor.lock.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["distribution"]["revision"], 2)
            versions = (root / "versions.env").read_text(encoding="utf-8")
            self.assertIn("DISTRO_REVISION=2", versions)
            self.assertIn("BIFROST_VERSION=2.4.0", versions)

    def test_rejects_non_increasing_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = {"distribution": {"revision": 3}, "upstream": {"version": "2.4.0"}}
            (root / "vendor.lock.json").write_text(json.dumps(lock), encoding="utf-8")
            self.assertEqual(bump_revision.main(["--root", str(root), "--set", "3"]), 1)


if __name__ == "__main__":
    unittest.main()
