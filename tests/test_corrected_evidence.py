"""The manuscript must reject corrected evidence modified after execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import corrected_evidence

class CorrectedEvidenceTests(unittest.TestCase):
    def test_current_evidence_passes(self):
        info, run = corrected_evidence.load()
        self.assertEqual(info['status'], 'passed')
        self.assertTrue((run / 'analysis/abstention.csv').is_file())

    def test_changed_corrected_bytes_fail_before_rendering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            import shutil
            info = json.loads(corrected_evidence.INDEX.read_text())
            for name in info['artifacts']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(corrected_evidence.ROOT / name, target)
            (root / info['run'] / 'results.json').write_text('changed')
            index = root / 'current.json'
            index.write_text(json.dumps(info))
            with patch.object(corrected_evidence, 'ROOT', root), patch.object(corrected_evidence, 'INDEX', index):
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    corrected_evidence.load()

    def test_missing_index_is_not_historical_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(corrected_evidence, 'INDEX', Path(temp)/'missing.json'):
                with self.assertRaisesRegex(ValueError, 'index is required'):
                    corrected_evidence.load()

    def test_required_artifact_cannot_be_unbound(self):
        info = json.loads(corrected_evidence.INDEX.read_text())
        del info['artifacts'][info['run']+'/run-receipt.json']
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp)/'current.json'
            index.write_text(json.dumps(info))
            with patch.object(corrected_evidence, 'INDEX', index):
                with self.assertRaisesRegex(ValueError, 'not hash-bound'):
                    corrected_evidence.load()
