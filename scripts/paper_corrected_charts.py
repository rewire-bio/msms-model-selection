"""Regenerate only figures affected by fusion correction, from verified tables."""
from pathlib import Path
import json
import sys
import pandas as pd
import corrected_evidence

ROOT = Path(__file__).resolve().parents[1]

def main():
    if not corrected_evidence.INDEX.exists():
        return
    _, run = corrected_evidence.load()
    sys.path.insert(0, str(ROOT / 'companion/scripts'))
    from make_charts import chart_pool_size, chart_abstention
    out = ROOT / 'paper/figures/corrected'
    out.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(run / 'analysis/metrics.csv')
    sizes = pd.read_csv(ROOT / 'companion/results/pool-sizes.csv', index_col=0)
    chart_pool_size(metrics, sizes, out / '02-pool-size-stress.png')
    chart_abstention(json.loads((run / 'analysis/risk-coverage-curves.json').read_text()),
                     pd.read_csv(run / 'analysis/abstention.csv'), out / '04-decline-to-nominate.png')
    print('Regenerated corrected pool-size and abstention figures')

if __name__ == '__main__':
    main()
