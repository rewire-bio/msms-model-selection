#!/usr/bin/env python3
"""Check preserved evidence and extraction without writing tracked outputs or running science."""
from pathlib import Path
import tempfile

from data import verify_data
import evidence_integrity
import paper_extract

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Cached scores are external execution inputs, not prerequisites for software CI.
    # Actual runs and clean correction reproduction require and hash-check every file.
    import json
    datasets = json.loads((ROOT / 'data/manifest.json').read_text())['datasets']
    if all((ROOT / row['path']).is_file() for row in datasets):
        verify_data(ROOT / 'data/manifest.json', ROOT)
    else:
        print('Cached execution inputs unavailable: skipped local-data check; no scientific run claimed.')
    evidence_integrity.verify_or_fail('verify')
    # Both entry points independently enforce input integrity before generation.
    import paper_ledger
    with tempfile.TemporaryDirectory(prefix='msms-verify-') as directory:
        output = Path(directory)
        paper_extract.GEN = output / 'generated'
        paper_extract.main()
        import corrected_evidence
        if corrected_evidence.INDEX.exists():
            (paper_extract.GEN / 'historical-extraction-receipt.json').write_text((paper_extract.GEN / 'extraction-receipt.json').read_text())
            paper_extract.main(corrected=True)
        paper_ledger.main(output / 'claims-ledger.json')
    print('Historical and corrected saved evidence and extraction verified; experiments were not reproduced.')


if __name__ == '__main__':
    main()
