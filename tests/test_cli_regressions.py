"""Regression tests for msms_shortlist.cli / chem (GitHub issues #5, #6, #7).

Run with: python -m unittest discover -s tests (from the repository root).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from contextlib import nullcontext

import numpy as np
import pandas as pd

_COMPANION_DIR = Path(__file__).resolve().parent.parent / "companion"
sys.path.insert(0, str(_COMPANION_DIR))

from msms_shortlist import cli  # noqa: E402
from msms_shortlist.chem import canonical_2d, exact_mass  # noqa: E402


def _args(ppm: float = 10.0, shortlist: int = 5) -> types.SimpleNamespace:
    return types.SimpleNamespace(ppm=ppm, shortlist=shortlist)


def _spectrum(params: dict, peaks: list[tuple[float, float]]) -> dict:
    return {"params": params, "peaks": peaks}


def _candidates_csv(rows: str) -> Path:
    fd, filename = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    path = Path(filename)
    path.write_text(rows)
    return path


class _NaNModel:
    """Mocked alignment model: avoids downloading/running real DreaMS weights."""

    vocab = ["[M+H]+"]

    def __init__(self, score=float("nan")):
        self.value = score

    def score(self, peaks, meta, smiles):
        return np.full(len(smiles), self.value)


# -- Issue #5: finite peak and score validation -----------------------------


class FinitePeaksTests(unittest.TestCase):
    def test_zero_intensity_peak_is_unusable(self):
        self.assertEqual(len(cli.finite_peaks([(20.0, 0.0)])), 0)

    def test_infinite_intensity_peak_is_unusable(self):
        self.assertEqual(len(cli.finite_peaks([(20.0, float("inf"))])), 0)

    def test_nan_mz_peak_is_unusable(self):
        self.assertEqual(len(cli.finite_peaks([(float("nan"), 100.0)])), 0)

    def test_mixed_peaks_keep_only_finite_positive_ones(self):
        kept = cli.finite_peaks(
            [(20.0, 0.0), (30.0, 5.0), (float("inf"), 9.0), (40.0, float("nan"))]
        )
        self.assertEqual(kept.tolist(), [[30.0, 5.0]])


class EmbeddingInputTests(unittest.TestCase):
    def setUp(self):
        self.model = cli.AlignmentModel.__new__(cli.AlignmentModel)
        self.model.torch = types.SimpleNamespace(
            inference_mode=nullcontext, from_numpy=lambda value: value)
        self.captured = []
        self.model.dreams = lambda value: self.captured.append(value) or value

    def test_unusable_peaks_raise_before_embedding_or_normalization(self):
        for peaks in ([], [(20, 0)], [(20, -1)], [(20, float("inf"))],
                      [(float("nan"), 100)]):
            with self.subTest(peaks=peaks), np.errstate(all="raise"):
                with self.assertRaisesRegex(ValueError, "no usable peaks"):
                    self.model.embed_spectrum(peaks, 47.0)
        self.assertEqual(self.captured, [])

    def test_mixed_peaks_produce_finite_normalized_embedding_input(self):
        result = self.model.embed_spectrum(
            [(20, 50), (30, 100), (40, 0), (50, float("inf")),
             (float("nan"), 200)], 47.0)
        self.assertEqual(result.shape, (1, cli.N_PEAKS + 1, 2))
        self.assertTrue(np.isfinite(result).all())
        np.testing.assert_array_equal(result[0, 1:3], [[30, 1], [20, .5]])
        self.assertFalse(result[0, 3:].any())


class RankOneUsablePeaksTests(unittest.TestCase):
    def setUp(self):
        path = _candidates_csv("id,smiles\neth,CCO\n")
        self.addCleanup(path.unlink)
        self.candidates, _ = cli.prepare_candidates(path)

    def test_all_zero_intensity_peaks_refused_not_nominated(self):
        spectrum = _spectrum(
            {"PEPMASS": "47.049141264", "ADDUCT": "[M+H]+", "CHARGE": "1+"},
            [(20.0, 0.0)],
        )
        table, summary = cli.rank_one(spectrum, self.candidates, _args(), None, None)
        self.assertTrue(table.empty)
        self.assertEqual(summary["decision"], "refused")
        self.assertIn("usable peaks", summary["reason"])

    def test_infinite_and_nan_only_peaks_refused(self):
        spectrum = _spectrum(
            {"PEPMASS": "47.049141264", "ADDUCT": "[M+H]+", "CHARGE": "1+"},
            [(20.0, float("inf")), (float("nan"), 50.0)],
        )
        table, summary = cli.rank_one(spectrum, self.candidates, _args(), None, None)
        self.assertTrue(table.empty)
        self.assertEqual(summary["decision"], "refused")

    def test_negative_only_peaks_refused(self):
        spectrum = _spectrum(
            {"PEPMASS": "47.049141264", "ADDUCT": "[M+H]+", "CHARGE": "1+"},
            [(20.0, -1.0)],
        )
        table, summary = cli.rank_one(spectrum, self.candidates, _args(), None, None)
        self.assertTrue(table.empty)
        self.assertEqual(summary["decision"], "refused")


class RankOneNonFiniteModelScoreTests(unittest.TestCase):
    def setUp(self):
        path = _candidates_csv("id,smiles\neth,CCO\n")
        self.addCleanup(path.unlink)
        self.candidates, _ = cli.prepare_candidates(path)

    def test_nan_model_score_is_refused_not_nominated(self):
        spectrum = _spectrum(
            {"PEPMASS": "47.049141264", "ADDUCT": "[M+H]+", "CHARGE": "1+"},
            [(31.0, 100.0)],
        )
        table, summary = cli.rank_one(
            spectrum, self.candidates, _args(), _NaNModel(), {"tau": 0.6}
        )
        self.assertTrue(table.empty)
        self.assertEqual(summary["decision"], "refused")
        self.assertNotEqual(summary["decision"], "nominate shortlist")

    def test_infinite_model_scores_are_refused(self):
        spectrum = _spectrum(
            {"PEPMASS": "47.049141264", "ADDUCT": "[M+H]+", "CHARGE": "1+"},
            [(31.0, 100.0)],
        )
        for score in (float("inf"), -float("inf")):
            with self.subTest(score=score):
                table, summary = cli.rank_one(
                    spectrum, self.candidates, _args(), _NaNModel(score), {"tau": .6})
                self.assertTrue(table.empty)
                self.assertEqual(summary["decision"], "refused")


# -- Issue #6: isotope-aware identity and mass -------------------------------


class IsotopeIdentityTests(unittest.TestCase):
    def test_isotope_label_changes_canonical_identity(self):
        self.assertNotEqual(canonical_2d("[13CH3]CO"), canonical_2d("CCO"))

    def test_isotope_label_changes_exact_mass(self):
        labelled_mass = exact_mass(canonical_2d("[13CH3]CO"))
        unlabelled_mass = exact_mass(canonical_2d("CCO"))
        self.assertAlmostEqual(labelled_mass - unlabelled_mass, 1.003355, places=5)

    def test_stereoisomers_still_share_one_identity(self):
        self.assertEqual(
            canonical_2d("C[C@H](N)C(=O)O"),
            canonical_2d("C[C@@H](N)C(=O)O"),
        )

    def test_labelled_and_unlabelled_candidates_are_not_merged(self):
        path = _candidates_csv("id,smiles\nlabelled,[13CH3]CO\nunlabelled,CCO\n")
        self.addCleanup(path.unlink)
        candidates, report = cli.prepare_candidates(path)
        self.assertEqual(report["n_distinct_2d"], 2)
        self.assertEqual(report["n_duplicate_2d_merged"], 0)

    def test_labelled_candidate_found_within_precursor_window(self):
        path = _candidates_csv("id,smiles\nlabelled,[13CH3]CO\nunlabelled,CCO\n")
        self.addCleanup(path.unlink)
        candidates, _ = cli.prepare_candidates(path)
        spectrum = _spectrum(
            {"PEPMASS": "48.052496104", "ADDUCT": "[M+H]+", "CHARGE": "1+"},
            [(31.0, 100.0)],
        )
        table, summary = cli.rank_one(spectrum, candidates, _args(), None, None)
        self.assertNotEqual(summary["decision"], "no candidate within window")
        self.assertIn("labelled", table["id"].tolist())


# -- Issue #7: malformed per-spectrum metadata must not crash the batch -----


class ValidateMetadataRefusalTests(unittest.TestCase):
    def test_unreadable_charge_is_refused_not_raised(self):
        meta, reason = cli.validate(
            {"PEPMASS": "47.049141264", "ADDUCT": "[M+H]+", "CHARGE": "unknown"}
        )
        self.assertIsNone(meta)
        self.assertIn("CHARGE", reason)

    def test_unreadable_collision_energy_is_refused_not_raised(self):
        meta, reason = cli.validate(
            {
                "PEPMASS": "47.049141264",
                "ADDUCT": "[M+H]+",
                "CHARGE": "1+",
                "COLLISION_ENERGY": "35 eV",
            }
        )
        self.assertIsNone(meta)
        self.assertIn("COLLISION_ENERGY", reason)

    def test_infinite_collision_energy_is_refused(self):
        meta, reason = cli.validate(
            {
                "PEPMASS": "47.049141264",
                "ADDUCT": "[M+H]+",
                "CHARGE": "1+",
                "COLLISION_ENERGY": "inf",
            }
        )
        self.assertIsNone(meta)
        self.assertIn("COLLISION_ENERGY", reason)

    def test_nan_collision_energy_is_permitted_as_missing_sentinel(self):
        meta, reason = cli.validate(
            {
                "PEPMASS": "47.049141264",
                "ADDUCT": "[M+H]+",
                "CHARGE": "1+",
                "COLLISION_ENERGY": "nan",
            }
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(meta)
        self.assertTrue(np.isnan(meta["collision_energy"]))


class ThresholdsTauValidationTests(unittest.TestCase):
    def setUp(self):
        candidates = _candidates_csv("id,smiles\neth,CCO\n")
        self.addCleanup(candidates.unlink)
        mgf = Path(tempfile.mkstemp(suffix=".mgf")[1])
        mgf.write_text(
            "BEGIN IONS\nTITLE=valid1\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\n31.0 100.0\nEND IONS\n"
        )
        self.addCleanup(mgf.unlink)
        self.candidates_path = candidates
        self.mgf_path = mgf
        self.out_path = Path(tempfile.mkstemp(suffix=".csv")[1])
        self.addCleanup(self.out_path.unlink)

    def _thresholds_path(self, body: str) -> Path:
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(body)
        self.addCleanup(path.unlink)
        return path

    def _run(self, thresholds_path: Path):
        return cli.main([
            "--spectra", str(self.mgf_path),
            "--candidates", str(self.candidates_path),
            "--out", str(self.out_path),
            "--thresholds", str(thresholds_path),
        ])

    def test_nan_tau_is_rejected_before_ranking(self):
        thresholds_path = self._thresholds_path('{"tau": NaN}')
        with self.assertRaises(SystemExit):
            self._run(thresholds_path)

    def test_infinite_tau_is_rejected_before_ranking(self):
        thresholds_path = self._thresholds_path('{"tau": Infinity}')
        with self.assertRaises(SystemExit):
            self._run(thresholds_path)

    def test_missing_tau_key_is_rejected_before_ranking(self):
        thresholds_path = self._thresholds_path('{"confidence": "top-1 cosine"}')
        with self.assertRaises(SystemExit):
            self._run(thresholds_path)

    def test_finite_tau_is_accepted(self):
        thresholds_path = self._thresholds_path('{"tau": 0.6}')
        rc = self._run(thresholds_path)
        self.assertEqual(rc, 0)


class ArgparseGuardTests(unittest.TestCase):
    def setUp(self):
        candidates = _candidates_csv("id,smiles\neth,CCO\n")
        self.addCleanup(candidates.unlink)
        mgf = Path(tempfile.mkstemp(suffix=".mgf")[1])
        mgf.write_text(
            "BEGIN IONS\nTITLE=valid1\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\n31.0 100.0\nEND IONS\n"
        )
        self.addCleanup(mgf.unlink)
        self.candidates_path = candidates
        self.mgf_path = mgf
        self.out_path = Path(tempfile.mkstemp(suffix=".csv")[1])
        self.addCleanup(self.out_path.unlink)

    def _run(self, extra_args: list[str]):
        return cli.main([
            "--spectra", str(self.mgf_path),
            "--candidates", str(self.candidates_path),
            "--out", str(self.out_path),
            *extra_args,
        ])

    def test_zero_ppm_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._run(["--ppm", "0"])

    def test_negative_ppm_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._run(["--ppm", "-5"])

    def test_nonfinite_ppm_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._run(["--ppm", "inf"])

    def test_shortlist_below_one_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._run(["--shortlist", "0"])

    def test_negative_shortlist_is_rejected(self):
        with self.assertRaises(SystemExit):
            self._run(["--shortlist", "-1"])

    def test_valid_ppm_and_shortlist_are_accepted(self):
        rc = self._run(["--ppm", "15", "--shortlist", "3"])
        self.assertEqual(rc, 0)


class MnaExampleMetadataStillAcceptedTests(unittest.TestCase):
    def test_mna_example_collision_energy_nan_sentinel_still_validates(self):
        mna_path = _COMPANION_DIR / "examples" / "mna.mgf"
        spectra = cli.read_mgf(mna_path)
        self.assertEqual(len(spectra), 1)
        meta, reason = cli.validate(spectra[0]["params"])
        self.assertIsNone(reason)
        self.assertIsNotNone(meta)
        self.assertTrue(np.isnan(meta["collision_energy"]))


class BatchRefusalDoesNotCrashSiblingsTests(unittest.TestCase):
    def test_valid_invalid_valid_mgf_batch_writes_valid_rows_and_refusal(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(tmp))
        mgf = tmp / "spectra.mgf"
        mgf.write_text(
            "BEGIN IONS\nTITLE=valid1\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\n31.0 100.0\nEND IONS\n"
            "BEGIN IONS\nTITLE=bad_charge\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=unknown\n31.0 100.0\nEND IONS\n"
            "BEGIN IONS\nTITLE=valid2\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\n31.0 100.0\nEND IONS\n"
        )
        candidates = tmp / "candidates.csv"
        candidates.write_text("id,smiles\neth,CCO\n")
        out = tmp / "out.csv"

        rc = cli.main(["--spectra", str(mgf), "--candidates", str(candidates), "--out", str(out)])

        self.assertEqual(rc, 0)
        result = pd.read_csv(out)
        self.assertEqual(sorted(result["query_id"].unique().tolist()), ["valid1", "valid2"])
        provenance = json.loads(out.with_suffix(".provenance.json").read_text())
        decisions = {q["query_id"]: q["decision"] for q in provenance["queries"]}
        self.assertEqual(decisions["bad_charge"], "refused")
        self.assertIn("CHARGE", provenance["queries"][1]["reason"])
        self.assertEqual(decisions["valid1"], "nominate shortlist")
        self.assertEqual(decisions["valid2"], "nominate shortlist")

    def test_valid_invalid_valid_mgf_batch_with_malformed_energy(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(tmp))
        mgf = tmp / "spectra.mgf"
        mgf.write_text(
            "BEGIN IONS\nTITLE=valid1\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\n31.0 100.0\nEND IONS\n"
            "BEGIN IONS\nTITLE=bad_energy\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\nCOLLISION_ENERGY=inf\n31.0 100.0\nEND IONS\n"
            "BEGIN IONS\nTITLE=valid2\nPEPMASS=47.049141264\nADDUCT=[M+H]+\n"
            "CHARGE=1+\n31.0 100.0\nEND IONS\n"
        )
        candidates = tmp / "candidates.csv"
        candidates.write_text("id,smiles\neth,CCO\n")
        out = tmp / "out.csv"

        rc = cli.main(["--spectra", str(mgf), "--candidates", str(candidates), "--out", str(out)])

        self.assertEqual(rc, 0)
        result = pd.read_csv(out)
        self.assertEqual(sorted(result["query_id"].unique().tolist()), ["valid1", "valid2"])
        provenance = json.loads(out.with_suffix(".provenance.json").read_text())
        decisions = {q["query_id"]: q["decision"] for q in provenance["queries"]}
        reasons = {q["query_id"]: q.get("reason") for q in provenance["queries"]}
        self.assertEqual(decisions["bad_energy"], "refused")
        self.assertIn("COLLISION_ENERGY", reasons["bad_energy"])
        self.assertEqual(decisions["valid1"], "nominate shortlist")
        self.assertEqual(decisions["valid2"], "nominate shortlist")


if __name__ == "__main__":
    unittest.main()
