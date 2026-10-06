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
            (root / 'results.json').write_text('changed')
            index = root / 'current.json'
            index.write_text(json.dumps({'status':'passed','artifacts':{'results.json':'0'*64}}))
            with patch.object(corrected_evidence, 'ROOT', root), patch.object(corrected_evidence, 'INDEX', index):
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    corrected_evidence.load()
