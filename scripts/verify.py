#!/usr/bin/env python3
"""Check preserved evidence and extraction without writing tracked outputs or running science."""
from pathlib import Path
import tempfile

from data import verify_data
import evidence_integrity
import paper_extract

ROOT = Path(__file__).resolve().parents[1]


def main():
    verify_data(ROOT / 'data/manifest.json', ROOT)
    evidence_integrity.verify_or_fail('verify')
    # Both entry points independently enforce input integrity before generation.
    import paper_ledger
    with tempfile.TemporaryDirectory(prefix='msms-verify-') as directory:
        output = Path(directory)
        paper_extract.GEN = output / 'generated'
        paper_extract.main()
        paper_ledger.main(output / 'claims-ledger.json')
    print('Historical evidence and extraction verified; experiments were not reproduced.')


if __name__ == '__main__':
    main()
