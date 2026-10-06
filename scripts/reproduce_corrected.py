"""Independent cached-score correction reproduction; never retrain original models."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from reanalyse import digest, validate_inputs


def main():
    source = os.environ.get('MSMS_CACHED_INPUT_ROOT')
    if not source:
        raise SystemExit('Set MSMS_CACHED_INPUT_ROOT to the preserved cached-input directory. Public raw-artifact acquisition is unavailable.')
    config = json.loads((ROOT/'configs/corrected-analysis.json').read_text())
    manifest = json.loads((ROOT/config['input_manifest']).read_text())
    source = Path(source).resolve()
    source_paths = validate_inputs(source,manifest)
    destination = ROOT/config['input_root']
    for key,entry in manifest['files'].items():
        target = destination/entry['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if digest(target) != entry['sha256']:
                raise ValueError(f'Existing input changed: {key}')
        else:
            shutil.copy2(source_paths[key],target)
    validate_inputs(destination,manifest)
    output = ROOT/'results/reproduction'
    subprocess.run([sys.executable,str(ROOT/'scripts/reanalyse.py'),'--config',str(ROOT/'configs/corrected-analysis.json'),
                    '--output',str(output),'--work-dir',str(ROOT/'results/reproduction-scores')],cwd=ROOT,check=True)
    index = json.loads((ROOT/'evidence/corrected-analysis/current.json').read_text())
    reference = ROOT/index['run']
    deterministic = ['results.json','fusion-weight.json','comparison-metrics.csv','comparison-contrasts.csv','comparison-abstention.csv']
    deterministic += ['analysis/'+p.name for p in sorted((reference/'analysis').iterdir()) if p.is_file()]
    for name in deterministic:
        if digest(output/name) != digest(reference/name):
            raise ValueError(f'Deterministic corrected evidence differs: {name}')
    # A separate ignored source tree lets the paper regenerate without mutating
    # tracked generated tables, evidence, charts, or the published PDF.
    paper = ROOT/'results/paper-work'
    paper.mkdir(parents=True,exist_ok=False)
    archive = ROOT/'results/paper-source.tar'
    subprocess.run(['git','archive','--format=tar','--output',str(archive),'HEAD'],cwd=ROOT,check=True)
    with tarfile.open(archive) as handle:
        handle.extractall(paper,filter='data')
    target = paper/index['run']
    for item in output.rglob('*'):
        if item.is_file():
            rel = item.relative_to(output)
            (target/rel).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(item,target/rel)
    index['artifacts'] = {str(p.relative_to(paper)):digest(p) for p in sorted(target.rglob('*')) if p.is_file()}
    (paper/'evidence/corrected-analysis/current.json').write_text(json.dumps(index,indent=2)+'\n')
    # Reuse only the pinned local executable/tool cache; scientific data and
    # outputs were independently reconstructed above.
    for rel in ('companion/.venv','.tools'):
        existing=ROOT/rel
        if existing.exists():
            dest=paper/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.symlink_to(existing.resolve(),target_is_directory=True)
    for name in ('paper_corrected_charts.py','build_paper.py'):
        subprocess.run([sys.executable,str(paper/'scripts'/name)],cwd=paper,check=True)
    shutil.copy2(paper/'paper/build/main.pdf',ROOT/'results/reproduction-paper.pdf')
    (ROOT/'results/reproduction-check.json').write_text(json.dumps({'status':'passed','scope':'cached-score correction only; no original model-training reproduction',
        'deterministic_artifacts_equal':deterministic,'paper_sha256':digest(ROOT/'results/reproduction-paper.pdf')},indent=2)+'\n')

if __name__=='__main__':
    main()
