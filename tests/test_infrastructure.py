"""Maintenance regression tests; all training subprocesses are synthetic."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import evidence_integrity as integrity


class EvidenceTests(unittest.TestCase):
    def test_fusion_grid_and_figure_mutations_are_rejected(self):
        for relative in ('companion/results/fusion-weight.json', 'article/assets/01-recall-by-method.png',
                         'article/published-original.md'):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / relative
                target.parent.mkdir(parents=True)
                original = (ROOT / relative).read_bytes()
                target.write_bytes(original + b'changed')
                with patch.object(integrity, 'ROOT', root):
                    errors = integrity.verify_repository_evidence({relative: integrity.sha256_bytes(original)})
                self.assertTrue(any(relative in error for error in errors))

    def test_historical_protocol_copies_match_archive_members(self):
        self.assertEqual(integrity.verify_historical_protocol(), [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'evidence', root / 'evidence')
            shutil.copytree(ROOT / 'protocol/historical', root / 'protocol/historical')
            target = root / 'protocol/historical/protocol-with-amendments.md'
            target.write_text('changed')
            with patch.object(integrity, 'ROOT', root):
                self.assertIn('protocol-with-amendments.md', '\n'.join(integrity.verify_historical_protocol()))

    def test_maintained_source_and_docs_are_not_frozen(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(integrity, 'ROOT', Path(directory)):
            self.assertEqual(integrity.verify_repository_evidence({
                'companion/msms_shortlist/cli.py': 'historical',
                'companion/README.md': 'historical', 'README.md': 'historical'}), [])

    def test_extractor_and_ledger_reject_changed_grid_before_writes(self):
        import paper_extract
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'evidence', root / 'evidence')
            target = root / 'companion/results/fusion-weight.json'
            target.parent.mkdir(parents=True)
            value = json.loads((ROOT / target.relative_to(root)).read_text())
            value['validation_recall5_by_w']['0.0'] = .999
            target.write_text(json.dumps(value))
            with patch.object(integrity, 'ROOT', root), patch.object(paper_extract, 'GEN', root / 'generated'):
                with self.assertRaises(SystemExit) as raised:
                    paper_extract.main()
                self.assertIn('fusion-weight.json', str(raised.exception))
                self.assertFalse((root / 'generated').exists())
                spec = importlib.util.spec_from_file_location('ledger_mutation', ROOT / 'scripts/paper_ledger.py')
                module = importlib.util.module_from_spec(spec)
                with self.assertRaises(SystemExit) as raised:
                    spec.loader.exec_module(module)
                self.assertIn('fusion-weight.json', str(raised.exception))


FAKE = r'''#!PYTHON
import json, os, pathlib, sys
if len(sys.argv)>1 and sys.argv[1]=='-c':
    os.execv(sys.executable, [sys.executable]+sys.argv[1:])
a=sys.argv[1:]
mode=os.environ.get('FAKE_MODE','ok')
if mode=='fail': sys.exit(7)
if '--out' in a:
    path=pathlib.Path(a[a.index('--out')+1]); path.write_bytes(b'checkpoint'); sys.exit()
result=pathlib.Path(a[a.index('--result-path')+1])
result.write_text('broken' if mode=='invalid' else json.dumps({'metrics':{'test':1}}))
name=a[a.index('--wandb-run-name')+1]
checkpoint=pathlib.Path('checkpoints/paper_competitors')/name
checkpoint.mkdir(parents=True)
if mode!='empty': (checkpoint/'model.ckpt').write_bytes(b'checkpoint')
'''


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runs = self.root / 'runs'
        self.src = self.runs / 'external/msalign-src'
        interpreter = self.src / '.venv/bin/python'
        interpreter.parent.mkdir(parents=True)
        interpreter.write_text(FAKE.replace('PYTHON', sys.executable, 1))
        interpreter.chmod(0o755)

    def run_queue(self, mode='ok', env=None):
        environment = dict(os.environ, FAKE_MODE=mode)
        environment.update(env or {})
        return subprocess.run(['bash', str(ROOT / 'companion/scripts/queue_training.sh'), 'runs'],
                              cwd=self.root, env=environment, capture_output=True, text=True)

    def test_missing_checkout_creates_no_queue(self):
        shutil.rmtree(self.src)
        result = self.run_queue()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing MSAlign checkout', result.stderr)
        self.assertEqual(list(self.runs.glob('queue-*')), [])

    def test_failed_process_nonzero_no_success_and_no_move(self):
        (self.runs / 'queue-finished.txt').write_text('old success')
        result = self.run_queue('fail')
        self.assertEqual(result.returncode, 1, result.stderr)
        queue, = self.runs.glob('queue-*')
        self.assertFalse((queue / 'queue-finished.txt').exists())
        self.assertFalse((self.runs / 'queue-finished.txt').exists())
        self.assertEqual(len(list(self.runs.glob('legacy-queue.*/queue-finished.txt'))), 1)
        self.assertEqual(len(list(queue.glob('*/exit-code.txt'))), 3)
        self.assertTrue(all(p.read_text().strip() == '7' for p in queue.glob('*/exit-code.txt')))
        self.assertFalse((queue / 'T02-embcos/checkpoints').exists())

    def test_stale_checkpoint_is_preserved_and_refused(self):
        checkpoint = self.src / 'checkpoints/paper_competitors/embcos_formula_seed1'
        checkpoint.mkdir(parents=True)
        (checkpoint / 'old.ckpt').write_bytes(b'old')
        result = self.run_queue()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((checkpoint / 'old.ckpt').read_bytes(), b'old')
        self.assertEqual(list(self.runs.glob('queue-*')), [])

    def test_repeated_success_unique_and_relative_paths(self):
        for _ in range(2):
            result = self.run_queue()
            self.assertEqual(result.returncode, 0, result.stderr)
        queues = list(self.runs.glob('queue-*'))
        self.assertEqual(len(queues), 2)
        self.assertTrue(all((q / 'queue-finished.txt').exists() for q in queues))

    def test_invalid_or_empty_outputs_fail(self):
        for mode in ('invalid', 'empty'):
            with self.subTest(mode=mode):
                result = self.run_queue(mode)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(any(self.runs.glob('queue-*/queue-finished.txt')))
                # Synthetic failed outputs are left intact by production code.
                shutil.rmtree(self.src / 'checkpoints')

    def test_failed_promotion_is_not_success(self):
        fakebin = self.root / 'bin'
        fakebin.mkdir()
        command = fakebin / 'mv'
        command.write_text('#!/bin/sh\nexit 9\n')
        command.chmod(0o755)
        result = self.run_queue(env={'PATH': str(fakebin) + os.pathsep + os.environ['PATH']})
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(any(self.runs.glob('queue-*/queue-finished.txt')))
        self.assertTrue(any(self.src.glob('checkpoints/paper_competitors/*/*.ckpt')))


if __name__ == '__main__':
    unittest.main()
