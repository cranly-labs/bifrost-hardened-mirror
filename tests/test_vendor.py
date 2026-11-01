import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import verify_vendor  # noqa: E402


class VendorIntegrityTests(unittest.TestCase):
    def test_repository_vendor_matches_lockfile(self):
        root = Path(__file__).resolve().parent.parent
        self.assertEqual(verify_vendor.main(["--root", str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
