import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'companion' / 'scripts'))
import analyse


class AbstentionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.old_boot = analyse.N_BOOT
        analyse.N_BOOT = 20
        self.rows = np.arange(10)
        self.frame = pd.DataFrame([
            dict(row=i, target_id=i, pool=pool, b=0., t=0.,
                 top1=.8 if pool == 'official_dedup' else .2, top2=.1)
            for i in self.rows for pool in ('official_dedup', 'absent')
        ])

    def tearDown(self):
        analyse.N_BOOT = self.old_boot

    def run_abstention(self, val=None, test=None):
        return analyse.abstention({'m': self.frame if val is None else val},
                                 {'m': self.frame if test is None else test},
                                 self.rows, self.rows, self.rows)

    def test_complete_data_preserves_original_quantile(self):
        varied = self.frame.copy()
        varied.loc[varied.pool == 'official_dedup', 'top1'] = np.linspace(.4, .9, 10)
        result, _ = self.run_abstention(val=varied)
        for conf in ('top1', 'margin'):
            selected = result[(result.confidence == conf) & (result.threshold == 'tau_cov90')]
            values = np.linspace(.4, .9, 10) - (0.1 if conf == 'margin' else 0.)
            self.assertEqual(float(selected.tau.iloc[0]), float(np.quantile(values, .1)))

    def test_missing_validation_does_not_poison_threshold(self):
        result, _ = self.run_abstention(val=self.frame[self.frame.row != 0])
        self.assertTrue(np.isfinite(result.tau).all())
        np.testing.assert_allclose(result.val_coverage_present, .9)
        np.testing.assert_allclose(result.coverage_present_estimate, 1.)
        self.assertTrue((result.n_valid_calibration_present == 9).all())

    def test_missing_test_counts_decline_without_nan_hit_arithmetic(self):
        result, curves = self.run_abstention(test=self.frame[self.frame.row != 0])
        np.testing.assert_allclose(result.coverage_present_estimate, .9)
        np.testing.assert_allclose(result.recall5_among_nominated_estimate, 1.)
        self.assertTrue(np.isfinite(result.filter(regex='estimate|ci_low|ci_high').to_numpy()).all())
        self.assertTrue(all(np.isfinite(p['recall5_among_nominated']) for curve in curves.values() for p in curve))

    def test_nonfinite_confidence_is_failed_not_nominated(self):
        invalid = self.frame.copy()
        for i, value in enumerate((np.inf, -np.inf, np.nan)):
            invalid.loc[invalid.row == i, 'top1'] = value
        result, curves = self.run_abstention(val=invalid, test=invalid)
        np.testing.assert_allclose(result.coverage_present_estimate, .7)
        self.assertTrue(np.isfinite(result.tau).all())
        self.assertTrue(all(np.isfinite(p['tau']) for curve in curves.values() for p in curve))
        self.assertTrue(all(p['coverage_present'] <= .7 for curve in curves.values() for p in curve))

    def test_missing_rank_with_finite_confidence_is_failure(self):
        invalid = self.frame.copy()
        invalid.loc[invalid.row == 0, 'b'] = np.nan
        result, _ = self.run_abstention(test=invalid)
        np.testing.assert_allclose(result.coverage_present_estimate, .9)
        np.testing.assert_allclose(result.recall5_among_nominated_estimate, 1.)

    def test_no_calibration_or_no_predictions_fail_closed(self):
        empty = self.frame.iloc[:0]
        result, _ = self.run_abstention(val=empty)
        self.assertTrue(np.isposinf(result.tau).all())
        self.assertTrue((result.coverage_present_estimate == 0).all())
        self.assertFalse(result.recall5_defined.any())
        result, curves = self.run_abstention(test=empty)
        self.assertTrue((result.recall5_among_nominated_estimate == 0).all())
        self.assertTrue(all(not curve for curve in curves.values()))

    def test_fusion_provenance_preserved_and_mixed_modes_rejected(self):
        legacy = self.frame.assign(fusion_normalization='legacy_post_scoring_deletion')
        corrected = self.frame.assign(fusion_normalization='per_pool_v2')
        result, _ = self.run_abstention(val=legacy, test=legacy)
        self.assertEqual(set(result.fusion_normalization), {'legacy_post_scoring_deletion'})
        with self.assertRaisesRegex(ValueError, 'normalization mismatch'):
            self.run_abstention(val=legacy, test=corrected)
        result, _ = self.run_abstention(val=corrected, test=corrected.iloc[:0])
        self.assertEqual(set(result.fusion_normalization), {'per_pool_v2'})
        self.assertTrue((result.coverage_present_estimate == 0).all())

    def test_empty_fold_rejected(self):
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            analyse.abstention({'m': self.frame}, {'m': self.frame}, [], self.rows, self.rows)


if __name__ == '__main__':
    unittest.main()
