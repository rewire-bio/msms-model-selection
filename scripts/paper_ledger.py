#!/usr/bin/env python3
"""Write evidence/paper-migration/claims-ledger.json for the imported-evidence manuscript.

Each substantive manuscript claim is tied to a historical artifact path, a pointer inside it and the artifact's
SHA-256 (archive members use the digests in evidence/migration-audit.json; repository files use the import
manifest or are hashed here). No value is computed. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import evidence_integrity

ROOT = Path(__file__).resolve().parents[1]
TARNAME = "downloads/msms-shortlist-results.tar.gz"
PREFIX = "msms-shortlist-results/"
AUDIT = json.loads((ROOT / "evidence/migration-audit.json").read_text())
MEMBERS = {m["path"]: m["sha256"] for a in AUDIT["archives"] if a["path"] == TARNAME for m in a["members"]}
MANIFEST = {f["path"]: f["sha256"] for f in json.loads((ROOT / "evidence/import-manifest.json").read_text())["files"]}
PUBLISHED = "article/published-original.md"

try:
    evidence_integrity.verify_or_fail("paper_ledger")
except evidence_integrity.IntegrityError as exc:
    sys.exit(str(exc))


def file_sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def member(name: str, pointer: str) -> dict:
    return {"artifact": f"{TARNAME}!{PREFIX}{name}", "pointer": pointer, "sha256": MEMBERS[PREFIX + name],
            "container_sha256": MANIFEST[TARNAME]}


def article(pointer: str) -> dict:
    return {"artifact": PUBLISHED, "pointer": pointer, "sha256": file_sha(PUBLISHED),
            "note": "byte-identical copy of the published article; link-adjusted copy at article/original.md"}


def repo(path: str, pointer: str) -> dict:
    """Hash the actual current file and cross-check it against the import manifest.

    Never silently falls back to the recorded manifest digest: a changed evidence
    file must surface as a ledger failure, not a stale expected digest.
    """
    actual = file_sha(path)
    expected = MANIFEST.get(path)
    if expected is not None and actual != expected:
        raise evidence_integrity.IntegrityError(
            f"ledger evidence mismatch: {path} (expected {expected}, actual {actual})")
    return {"artifact": path, "pointer": pointer, "sha256": actual}


A = "analysis/"
CLAIMS = [
    ("PROTOCOL", "Protocol frozen 2026-10-04T22:07:05Z before any test outcome; amendment A1 (window coverage)", "sec:protocol",
     "registration record", [member("protocol/protocol-freeze-receipt.txt", "whole file"), member("protocol/protocol.md", "section 12"),
                             member("protocol/protocol-frozen-original.md", "whole file")]),
    ("POPULATION", "Split formula_seed1: train 210,825/26,087, validation 9,631/1,428, test 10,648/1,421; no exclusions or failures",
     "sec:data, tab:main", "new measurement", [member("protocol/protocol.md", "section 2"), member(A + "metrics.csv", "n_spectra, n_molecules, n_missing_or_failed")]),
    ("POOLS", "Pool definitions; dedup median 252; expanded median 449 (IQR 296-691); 5.1% reach the cap", "sec:pools, tab:poolsizes",
     "new measurement", [member("protocol/protocol.md", "section 3"), member(A + "pool-sizes.csv", "all rows"), article("pool-size section (5.1% at cap)")]),
    ("REPEATS-ISOMERS", "85.4% of 28,936 official lists contain a repeated 2D structure (mean 6.9, max 121); 32.6% of validation decoys share the target's exact mass",
     "sec:pools, sec:task", "data audit (protocol notes and article text)", [member("protocol/access-and-feasibility.md", "repeated-structure and isomer audit"), article("task section")]),
    ("NEAR-DUP", "34.7% of test rows match more than one MassSpecGym record (structure, adduct, precursor, top-10 peaks)", "sec:data, sec:limitations",
     "data audit (article text only)", [article("'What this comparison does not show', near-duplicate records")]),
    ("REPRO", "Released evaluation (strict, official_raw): DreaMS+Morgan 32.6/56.8/76.7, Emb-Cos 35.4/59.3/76.8, DeepSets 13.1/27.9/46.9; harness equals released evaluation",
     "tab:repro, sec:repro", "reproduction", [member(A + "metrics.csv", "pool=official_raw, rule=strict"),
                                              member("receipts/T02-embcos-formula1-20261005T055415Z/released-result.json", "$.metrics.test"),
                                              member("receipts/T03-deepsets-formula1-20261005T085424Z/released-result.json", "$.metrics.test")]),
    ("PUBLISHED", "MSAlign v2 and v1 published values, v2 two-SD bands", "tab:published, tab:repro, sec:published", "published (transcribed from article)",
     [article("Table 2 and the paragraphs after it")]),
    ("MAIN", "Primary Recall@1/5/20 on official_dedup with random-tie expectation and molecule-bootstrap intervals", "tab:main, fig:recall",
     "new measurement", [member(A + "metrics.csv", "pool=official_dedup, rule=expected"), member(A + "random-repeats.json", "$.official_dedup"),
                         repo("article/assets/01-recall-by-method.png", "figure")]),
    ("CONTRASTS", "C1 +48.0 [+42.2, +53.6]; C2 -1.85 [-5.19, +1.35]; C3 +18.0 [+13.4, +22.5]; expanded-pool C2 -4.56 [-7.95, -1.19] (not pre-declared)",
     "tab:contrasts, tab:contrasts-all, sec:poolsize", "new measurement", [member(A + "contrasts.csv", "all rows; primary flag")]),
    ("POOLSIZE", "Recall@5 and Recall@1 by pool (16, 64, 252, 449)", "fig:pools, tab:pools", "new measurement (stress test)",
     [member(A + "metrics.csv", "pool in sub16, sub64, official_dedup, expanded1024; rule=expected"), member(A + "random-repeats.json", "all pools"),
      repo("article/assets/02-pool-size-stress.png", "figure")]),
    ("RULES", "Tie and duplicate conventions: mass error 6.3 -> 13.3 (R@5), 0.8 -> 3.7 (R@1); DreaMS+Morgan 56.8 -> 61.4", "tab:rules, fig:rules",
     "new measurement", [member(A + "metrics.csv", "official_raw/official_dedup x strict/expected"), repo("article/assets/03-tie-and-duplicate-rules.png", "figure")]),
    ("ABSTENTION", "Decline thresholds (fitted on validation) on test: coverage, Recall@5 among covered, false nominations; threshold 0.599",
     "tab:abstention, tab:abstention-all, fig:decline", "new measurement (stress test)",
     [member(A + "abstention.csv", "all rows"), member(A + "risk-coverage-curves.json", "curves"), repo("companion/models/thresholds.json", "threshold"),
      repo("article/assets/04-decline-to-nominate.png", "figure")]),
    ("PRECURSOR", "Precursor audit: training 19.0% within 0.01 ppm; test 6.94% > 10 ppm and 16.1% > 5 ppm (amendment A1); Fig. 7 caption values",
     "sec:precursor, fig:precursor, tab:precursor", "new measurement (data audit)",
     [member("receipts/A02-precursor-error-audit-20261004T224918Z/summary.json", "train, val"), member("protocol/protocol.md", "amendment A1"),
      repo("article/assets/05-precursor-mass-error.png", "figure")]),
    ("STRATA", "Post hoc Recall@5 by precursor stratum and instrument", "tab:strata, tab:strata-instrument, sec:limitations", "post hoc",
     [member(A + "strata-post-hoc.csv", "all rows")]),
    ("FUSION", "Fusion weight 0.55 chosen on validation Recall@5", "tab:fusion, tab:methods", "new measurement (exploratory)",
     [repo("companion/results/fusion-weight.json", "$.validation_recall5_by_w")]),
    ("MCES1", "Pre-declared secondary population mces_1 (17,556 spectra, 2,997 molecules), cheap baselines only; archived but not in the article",
     "tab:mces1", "new measurement (descriptive)", [member("analysis-mces1/metrics.csv", "all rows"), member("protocol/protocol.md", "section 2")]),
    ("TRAINING", "Training: DreaMS+Morgan 30,000 steps, selected step 3,296, 7.75 h; Emb-Cos 16,000 steps, 3.0 h; seed 42", "sec:methods-list, sec:provenance",
     "execution record", [member("receipts/T01-msalign-dreams-morgan-formula1-20261004T220904Z/train-receipt.json", "$.wall_seconds, $.effective_config"),
                          article("training-time paragraph (Emb-Cos 3.0 h)")]),
    ("DEMO", "Companion demonstration outputs (MassSpecGymID0226249, MassSpecGymID0395778, invalid metadata); CLI-harness consistency",
     "sec:demo, app:demo", "execution record", [article("'Running the shortlist on your own spectra' console blocks"),
                                                member("receipts/X02-cli-demo-20261005T060708Z/consistency-check.txt", "whole file"),
                                                member("receipts/V01-dreams-torchscript-equivalence-20261004T221550Z/result.json", "$.cosine_min")]),
    ("CLI-TIMING", "Clean-archive uv sync 1.5 s, first CLI run 35 s, model run 5.3 s", "app:repro", "execution record (article text only)",
     [article("companion section, timing paragraph")]),
    ("FIGURES-LIT", "MSAlign and Juergens figures (CC BY 4.0)", "fig:msalign, fig:jurgens", "published",
     [repo("article/assets/01-msalign-v2-recipe-model-zoo-late-fusion.png", "figure"), repo("article/assets/13-jurgens-selective-prediction-overview.png", "figure")]),
    ("DECISION-PATH", "Companion decision path", "fig:path", "figure", [repo("article/assets/01-decision-path.svg", "figure")]),
    ("LITERATURE", "Literature statements (MassSpecGym pools, Kind & Fiehn, DreaMS, audit of 17 of 26 papers, tie conventions, COSMIC, MS2Query, conformal, MSI, Schymanski, Charbonnet)",
     "sec:background, sec:limitations", "literature (not re-retrieved)", [article("body text and References")]),
    ("INTERPRETATION", "Recommendation: alignment model for a five-structure shortlist; DreaMS+Morgan as shipped, Emb-Cos if training one's own; decline as triage",
     "abstract, sec:guidance", "interpretation", [member(A + "metrics.csv", "official_dedup expected"), member(A + "contrasts.csv", "C2 primary")]),
]


def main(output: Path | None = None) -> None:
    ledger = {"schema_version": 1,
              "status": "historical_imported: every value comes from the 2026-10-03/05 runs (results archive and companion files), the "
                        "published papers or the cited literature; nothing was recomputed or reproduced during migration",
              "claims": [{"id": i, "claim": c, "manuscript": loc, "evidence_class": cls, "evidence": ev} for i, c, loc, cls, ev in CLAIMS]}
    import corrected_evidence
    info, run = corrected_evidence.load()
    replacement = {
        f"{TARNAME}!{PREFIX}analysis/{name}": str((run / 'analysis' / name).relative_to(ROOT))
        for name in ('metrics.csv', 'contrasts.csv', 'abstention.csv', 'risk-coverage-curves.json')
    }
    replacement.update({
        'companion/results/fusion-weight.json': str((run / 'fusion-weight.json').relative_to(ROOT)),
        'article/assets/02-pool-size-stress.png': 'paper/figures/corrected/02-pool-size-stress.png',
        'article/assets/04-decline-to-nominate.png': 'paper/figures/corrected/04-decline-to-nominate.png',
    })
    for claim in ledger['claims']:
        for item in claim['evidence']:
            if item['artifact'] in replacement:
                item['artifact'] = replacement[item['artifact']]
                item['sha256'] = file_sha(item['artifact'])
                item.pop('container_sha256', None)
                item['provenance'] = 'corrected cached-score analysis; see evidence/corrected-analysis/current.json'
    ledger['status'] = 'Cached-score correction of fusion; unchanged historical supplementary evidence. No independent training reproduction.'
    ledger['corrected_evidence'] = info
    ledger['claims'].append({'id':'CORRECTION', 'claim':'Per-pool fusion correction; nonfusion results, official-dedup fusion metrics, selected weight and validation grid unchanged.',
        'manuscript':'status, sec:abst-methods, sec:repro-status', 'evidence_class':'retrospective cached-score correction',
        'evidence':[repo(str((run / name).relative_to(ROOT)), 'whole file') for name in ('results.json','run-receipt.json','comparison-metrics.csv','comparison-abstention.csv')]})
    (output or ROOT / "evidence/paper-migration/claims-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(f"claims ledger: {len(CLAIMS)} claims")


if __name__ == "__main__":
    main()
