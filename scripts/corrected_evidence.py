"""Read the frozen corrected-analysis evidence without modifying historical inputs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'evidence/corrected-analysis/current.json'

def load():
    if not INDEX.is_file():
        raise ValueError('Corrected evidence index is required for the current manuscript')
    info = json.loads(INDEX.read_text())
    run = ROOT / info['run']
    if not run.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Corrected run path escapes repository')
    required = [str((run / name).relative_to(ROOT)) for name in (
        'results.json', 'run-receipt.json', 'fusion-weight.json',
        'analysis/metrics.csv', 'analysis/contrasts.csv', 'analysis/abstention.csv',
        'analysis/risk-coverage-curves.json', 'comparison-metrics.csv',
        'comparison-contrasts.csv', 'comparison-abstention.csv')]
    required += ['paper/figures/corrected/02-pool-size-stress.png',
                 'paper/figures/corrected/04-decline-to-nominate.png']
    missing = set(required) - set(info['artifacts'])
    if missing:
        raise ValueError('Required corrected evidence is not hash-bound: ' + ', '.join(sorted(missing)))
    if info['status'] != 'passed':
        raise ValueError('Corrected analysis has not passed')
    for name, expected in info['artifacts'].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Evidence path escapes repository')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Corrected evidence digest mismatch: {name}')
    run = ROOT / info['run']
    result = json.loads((run / 'results.json').read_text())
    if not result['nonfusion_invariance_passed'] or not result['fusion_official_dedup_unchanged']:
        raise ValueError('Corrected-analysis invariants failed')
    receipt = json.loads((run / 'run-receipt.json').read_text())
    if receipt['status'] != 'passed':
        raise ValueError('Corrected execution failed')
    for name, expected in receipt['artifacts'].items():
        path = run / name
        if info['artifacts'].get(str(path.relative_to(ROOT))) != expected:
            raise ValueError(f'Corrected artifact not bound to execution receipt: {name}')
    return info, run
