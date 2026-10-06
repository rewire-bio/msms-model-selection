import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / 'companion' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import fuse_scores


class FusionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pools_path = self.root / 'pools.h5'
        with h5py.File(self.pools_path, 'w') as h:
            h['offsets'] = [0, 4]
            h['flags'] = [15, 15, 13, 9]  # varying pool membership
            h['official_multiplicity'] = [1, 3, 1, 1]
            h['target_ids'] = [50]
        self.pools = h5py.File(self.pools_path, 'r')
        self.addCleanup(self.pools.close)
        self.model = self.data([0., 1., 2., 4.])
        self.mass = self.data([5., 3., 2., 1.])

    def data(self, scores):
        return dict(rows=np.array([7]), target_slot=np.array([0]),
                    score_offsets=np.array([0, 4]), scores=np.array(scores, dtype=np.float32))

    def rank(self, path, out, *extra):
        return subprocess.run([sys.executable, str(SCRIPTS / 'rank_stats.py'),
                               '--pools', str(self.pools_path), '--scores', str(path),
                               '--out', str(out), *extra], text=True, capture_output=True)

    def write_v2(self, path, model=None):
        model = self.model if model is None else model
        arrays = {name: fuse_scores.fused(self.pools, model, self.mass, .15, name)
                  for name in fuse_scores.POOL_NAMES}
        fuse_scores.write(path, model, arrays['official_dedup'],
                          {'method': 'fusion', 'fold': 'test'}, arrays)
        return arrays

    def test_excluded_target_cannot_change_absent_scores_or_rank_output(self):
        changed = self.data([100000., 1., 2., 4.])
        outputs = []
        for i, model in enumerate((self.model, changed)):
            path, out = self.root / f's{i}.h5', self.root / f'r{i}.csv.gz'
            arrays = self.write_v2(path, model)
            self.assertTrue(np.isnan(arrays['absent'][0]))
            res = self.rank(path, out)
            self.assertEqual(res.returncode, 0, res.stderr)
            outputs.append(pd.read_csv(out).set_index('pool').loc['absent'])
        for key in ('top1', 'top2', 'top5'):
            self.assertEqual(outputs[0][key], outputs[1][key])
        # Thus threshold decisions also cannot depend on the excluded target.
        for threshold in (-1., 0., 1.):
            self.assertEqual(outputs[0].top1 >= threshold, outputs[1].top1 >= threshold)

    def test_normalization_uses_each_pool_and_raw_multiplicity(self):
        for name in fuse_scores.POOL_NAMES:
            mask = fuse_scores.pool_mask(self.pools['flags'][:], self.pools['official_multiplicity'][:], name)
            values = self.model['scores'][mask]
            weights = self.pools['official_multiplicity'][:][mask] if name == 'official_raw' else np.ones(mask.sum())
            mean = np.average(values, weights=weights)
            expected = (values - mean) / np.sqrt(np.average((values - mean)**2, weights=weights))
            actual = fuse_scores.fused(self.pools, self.model, self.mass, 0., name)
            np.testing.assert_allclose(actual[mask], expected, atol=1e-6)
            self.assertTrue(np.isnan(actual[~mask]).all())

    def test_legacy_requires_explicit_opt_in_and_marks_output(self):
        path, out = self.root / 'legacy.h5', self.root / 'legacy.csv.gz'
        fuse_scores.write(path, self.model, self.model['scores'], {'method': 'fusion', 'fold': 'test'})
        res = self.rank(path, out)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('--allow-legacy-fusion', res.stderr)
        self.assertFalse(out.exists())
        res = self.rank(path, out, '--allow-legacy-fusion')
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(set(pd.read_csv(out).fusion_normalization), {'legacy_post_scoring_deletion'})
        receipt = json.loads((self.root / 'legacy.receipt.json').read_text())
        self.assertEqual(receipt['fusion_normalization'], 'legacy_post_scoring_deletion')

    def test_incomplete_v2_rejected_even_with_legacy_flag(self):
        path = self.root / 'bad.h5'
        self.write_v2(path)
        with h5py.File(path, 'a') as h:
            del h['pool_scores/absent']
        res = self.rank(path, self.root / 'bad.csv.gz', '--allow-legacy-fusion')
        self.assertNotEqual(res.returncode, 0)
        self.assertIn('Incomplete', res.stderr)

    def test_unavailable_and_empty_pools(self):
        self.pools.close()
        with h5py.File(self.pools_path, 'a') as h:
            h['flags'][:] = [1, 0, 0, 0]  # absent empty, subsets unbuilt
        self.pools = h5py.File(self.pools_path, 'r')
        self.addCleanup(self.pools.close)
        path, out = self.root / 'empty.h5', self.root / 'empty.csv.gz'
        arrays = self.write_v2(path)
        self.assertTrue(np.isnan(arrays['sub16']).all())
        res = self.rank(path, out)
        self.assertEqual(res.returncode, 0, res.stderr)
        ranks = pd.read_csv(out).set_index('pool')
        self.assertNotIn('sub16', ranks.index)
        self.assertEqual(ranks.loc['absent', 'n_pool'], 0)
        self.assertTrue(np.isnan(ranks.loc['absent', 'top1']))

    def test_nonfinite_excluded_target_does_not_fail_absent_pool(self):
        model = self.data([np.nan, 1., 2., 4.])
        self.assertTrue(np.isnan(fuse_scores.fused(self.pools, model, self.mass, .15)).all())
        self.assertTrue(np.isfinite(fuse_scores.fused(self.pools, model, self.mass, .15, 'absent')[1:]).all())

    def test_all_predictions_failed_preserves_readable_schema_and_abstention(self):
        import analyse
        path, out = self.root / 'failed.h5', self.root / 'failed.csv.gz'
        self.write_v2(path, self.data([np.nan, np.nan, np.nan, np.nan]))
        res = self.rank(path, out)
        self.assertEqual(res.returncode, 0, res.stderr)
        frame = pd.read_csv(out)
        self.assertTrue(frame.empty)
        old = analyse.N_BOOT
        analyse.N_BOOT = 5
        try:
            summary, curves = analyse.abstention({'m': frame}, {'m': frame}, [7], [7], [50])
        finally:
            analyse.N_BOOT = old
        self.assertTrue((summary.coverage_present_estimate == 0).all())
        self.assertTrue(all(not curve for curve in curves.values()))

    def test_misaligned_components_rejected(self):
        mass = dict(self.mass, target_slot=np.array([1]))
        with self.assertRaisesRegex(ValueError, 'target_slot mismatch'):
            fuse_scores.fused(self.pools, self.model, mass, .15)

    def test_cli_writes_versioned_per_pool_artifacts(self):
        for name, data in (('model', self.model), ('mass', self.mass)):
            fuse_scores.write(self.root / f'{name}.h5', data, data['scores'], {'method': name})
        command = [sys.executable, str(SCRIPTS / 'fuse_scores.py'), '--pools', str(self.pools_path),
                   '--out-dir', str(self.root / 'run')]
        for fold in ('val', 'test'):
            for name in ('model', 'mass'):
                command += [f'--{name}-{fold}', str(self.root / f'{name}.h5')]
        res = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        for fold in ('val', 'test'):
            with h5py.File(self.root / 'run' / f'scores-{fold}.h5') as h:
                self.assertEqual(h.attrs['fusion_schema_version'], 2)
                self.assertEqual(set(h['pool_scores']), set(fuse_scores.POOL_NAMES))
            res = self.rank(self.root / 'run' / f'scores-{fold}.h5', self.root / f'{fold}.csv.gz')
            self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == '__main__':
    unittest.main()
