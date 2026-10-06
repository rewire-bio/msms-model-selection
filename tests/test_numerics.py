import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from study.monte_carlo import estimate_pi, inside_quarter_circle
from data import verify_data


class NumericalTests(unittest.TestCase):
    def test_known_geometry(self):
        self.assertTrue(inside_quarter_circle(0, 0))
        self.assertTrue(inside_quarter_circle(1, 0))
        self.assertTrue(inside_quarter_circle(0.6, 0.8))
        self.assertFalse(inside_quarter_circle(1, 1))
        with self.assertRaises(ValueError):
            inside_quarter_circle(-0.1, 0)

    def test_seeded_known_count(self):
        result = estimate_pi(10, 0)
        self.assertEqual(result["inside"], 6)
        self.assertEqual(result["estimate_pi"], 2.4)

    def test_reference_error_is_bounded_for_fixture(self):
        result = estimate_pi(100000, 20261001)
        self.assertLess(result["absolute_error"], 0.03)

    def test_invalid_size(self):
        for value in [0, -1, 1.5, True, 10000001]:
            with self.assertRaises(ValueError):
                estimate_pi(value, 0)

    def test_missing_or_corrupt_dataset_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"datasets": [{"path": "input.txt", "source": "https://example.org/data", "sha256": hashlib.sha256(b"expected").hexdigest(), "license": "CC0", "provenance": "test fixture"}]}))
            with self.assertRaisesRegex(ValueError, "Missing dataset"):
                verify_data(manifest, root)
            (root / "input.txt").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                verify_data(manifest, root)
            (root / "input.txt").write_bytes(b"expected")
            verify_data(manifest, root)


if __name__ == "__main__":
    unittest.main()
