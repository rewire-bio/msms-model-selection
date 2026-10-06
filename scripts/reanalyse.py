"""Reanalyse frozen cached scores without training, inference, or data downloads."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def validate_inputs(root, manifest):
    paths = {}
    for key, entry in manifest['files'].items():
        path = root / entry['path']
        if not path.is_file() or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
            raise ValueError(f'Input missing or changed: {key}: {entry["path"]}')
        paths[key] = path
    return paths

def compare_frames(old, new, keys, tolerance):
    """Fail closed on duplicate/missing rows; compare shared numeric evidence."""
    import numpy as np
    if old.duplicated(keys).any() or new.duplicated(keys).any():
        raise ValueError('Duplicate comparison keys')
    merged = old.merge(new, on=keys, how='outer', suffixes=('_historical', '_corrected'), indicator=True)
    if not merged['_merge'].eq('both').all():
        raise ValueError('Historical/corrected comparison keys differ')
    missing_numeric = [c for c in old.columns if c not in keys and old[c].dtype.kind in 'iuf' and (c not in new or new[c].dtype.kind not in 'iuf')]
    if missing_numeric:
        raise ValueError(f'Missing historical numeric columns: {missing_numeric}')
    numeric = [c for c in old.columns if c not in keys and c in new and old[c].dtype.kind in 'iuf' and new[c].dtype.kind in 'iuf']
    merged['unchanged'] = True
    for col in numeric:
        before, after = merged[col+'_historical'], merged[col+'_corrected']
        merged[col+'_delta'] = after - before
        merged['unchanged'] &= np.isclose(before, after, atol=tolerance, rtol=0, equal_nan=True)
    return merged.drop(columns='_merge')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', type=Path, default=ROOT / 'configs/corrected-analysis.json')
    ap.add_argument('--input-root', type=Path)
    ap.add_argument('--output', type=Path, required=True, help='New portable evidence directory')
    ap.add_argument('--work-dir', type=Path, help='New ignored directory for score and rank files')
    ap.add_argument('--validate-only', action='store_true')
    args = ap.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    args.input_root = args.input_root or ROOT / config['input_root']
    args.work_dir = args.work_dir or ROOT / 'results' / ((args.output.parent.name if args.output.name == 'output' else args.output.name) + '-scores')
    manifest_path = ROOT / config['input_manifest']
    manifest = json.loads(manifest_path.read_text())
    paths = validate_inputs(args.input_root.resolve(), manifest)
    if args.validate_only:
        print(f'Validated {len(paths)} frozen input files; no analysis executed.')
        return
    import pandas as pd
    if sys.version_info[:2] != (3, 11):
        raise ValueError('Use the pinned companion Python 3.11 environment')
    versions = {name: importlib.metadata.version(name) for name in ('numpy','pandas','h5py')}
    if versions != {'numpy':'1.25.0','pandas':'2.2.1','h5py':'3.11.0'}:
        raise ValueError(f'Unexpected dependencies: {versions}')
    if (args.output.exists() and any(args.output.iterdir())) or args.work_dir.exists():
        raise ValueError('Output/work directories must be new; historical artifacts are never overwritten')
    args.output.mkdir(parents=True, exist_ok=True)
    args.work_dir.mkdir(parents=True)
    out, work = args.output.resolve(), args.work_dir.resolve()
    scripts = ROOT / 'companion/scripts'
    # Verify implementation constants before touching scientific results.
    sys.path.insert(0, str(scripts))
    import analyse
    if (analyse.N_BOOT, analyse.SEED) != (config['bootstrap_replicates'],config['bootstrap_seed']):
        raise ValueError('Analysis bootstrap settings disagree with frozen configuration')
    started = time.time()
    import numpy as np
    import h5py
    meta = pd.read_csv(paths['metadata'])
    folds = pd.read_csv(paths['split'])['fold'].to_numpy()
    if len(meta) != len(folds):
        raise ValueError('Metadata/split row count differs')
    ids = meta['unique_smiles_idx'].to_numpy()
    if set(ids[folds=='val']) & set(ids[folds=='test']):
        raise ValueError('Validation/test molecule overlap')
    with h5py.File(paths['pools']) as pools:
        targets = pools['target_ids'][:]
        for fold in ('val','test'):
            expected = np.flatnonzero(folds==fold)
            for method in config['methods']:
                frame = pd.read_csv(paths[f'{method}_ranks_{fold}'])
                if not np.array_equal(np.sort(frame.row.unique()), expected):
                    raise ValueError(f'{method}/{fold}: rank row mismatch')
                if not np.array_equal(frame.target_id.to_numpy(), ids[frame.row.to_numpy()]):
                    raise ValueError(f'{method}/{fold}: rank target mismatch')
            for method in ('mass','msalign'):
                with h5py.File(paths[f'{method}_scores_{fold}']) as scores:
                    if not np.array_equal(scores['rows'][:],expected) or not np.array_equal(targets[scores['target_slot'][:]],ids[expected]):
                        raise ValueError(f'{method}/{fold}: component alignment mismatch')
    receipt = {'status':'running','started_at_utc':datetime.now(timezone.utc).isoformat(), 'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'git_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'config_sha256':digest(config_path),'manifest_sha256':digest(manifest_path),
               'protocol_sha256':digest(ROOT/config['protocol']), 'python':platform.python_version(),
               'dependencies':versions,'commands':[], 'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in
               [Path(__file__),scripts/'fuse_scores.py',scripts/'rank_stats.py',scripts/'analyse.py',ROOT/'companion/msms_shortlist/metrics.py']}}
    def portable(s):
        for absolute, token in [(str(args.input_root.resolve()),'$INPUT_ROOT'),(str(out),'$OUTPUT'),(str(work),'$WORK_DIR'),(str(ROOT),'$REPO')]:
            s = s.replace(absolute,token)
        return s.replace(sys.executable,'$PYTHON')
    def run(argv):
        t = time.time()
        result = subprocess.run([sys.executable,*map(str,argv)],capture_output=True,text=True)
        receipt['commands'].append({'argv':[portable(str(s)) for s in ['$PYTHON',*argv]],'seconds':time.time()-t,'returncode':result.returncode})
        with (out/'execution.log').open('a') as f:
            f.write(portable(result.stdout+result.stderr)+'\n')
        if result.returncode:
            raise RuntimeError(f'Analysis stage failed: {Path(argv[0]).name}; see execution.log')
    try:
        fuse = [scripts/'fuse_scores.py','--pools',paths['pools']]
        for kind,method in [('model','msalign'),('mass','mass')]:
            for fold in ('val','test'):
                fuse += [f'--{kind}-{fold}',paths[f'{method}_scores_{fold}']]
        run([*fuse,'--out-dir',work/'fusion'])
        weight = json.loads((work/'fusion/fusion-weight.json').read_text())
        historical_weight = json.loads(paths['historical_weight'].read_text())
        if weight['fusion_normalization'] != config['fusion_normalization'] or sorted(map(float,weight['validation_recall5_by_w'])) != config['weight_grid']:
            raise ValueError('Implemented fusion settings disagree with config')
        if weight['chosen_w_mass'] != historical_weight['chosen_w_mass'] or set(weight['validation_recall5_by_w']) != set(historical_weight['validation_recall5_by_w']):
            raise ValueError('Historical fusion weight/grid changed')
        if any(abs(value-historical_weight['validation_recall5_by_w'][key]) > config['absolute_tolerance'] for key,value in weight['validation_recall5_by_w'].items()):
            raise ValueError('Historical validation selection curve changed')
        receipt['fusion_weight_and_validation_grid_unchanged'] = True
        for fold in ('val','test'):
            run([scripts/'rank_stats.py','--pools',paths['pools'],'--scores',work/'fusion'/f'scores-{fold}.h5','--out',work/f'ranks-fusion-{fold}.csv.gz'])
        command = [scripts/'analyse.py']
        for fold in ('test','val'):
            command += ['--'+fold,*[f'{m}={paths[f"{m}_ranks_{fold}"]}' for m in config['methods']],f'fusion={work/f"ranks-fusion-{fold}.csv.gz"}']
        run([*command,'--data',paths['metadata'].parent,'--split',config['split'],'--out',out/'analysis'])
        comparisons = {}
        for name,keys in [('metrics',['pool','rule','method','k']),('contrasts',['contrast','pool','rule','k']),('abstention',['method','confidence','threshold'])]:
            comparison=compare_frames(pd.read_csv(paths['historical_'+name]),pd.read_csv(out/'analysis'/f'{name}.csv'),keys,config['absolute_tolerance'])
            comparison.to_csv(out/f'comparison-{name}.csv',index=False)
            comparisons[name]={'rows':len(comparison),'changed_rows':int((~comparison.unchanged).sum())}
            required = comparison if name=='contrasts' else comparison[comparison.method!='fusion']
            if not required.unchanged.all():
                raise ValueError(f'Unexpected nonfusion change in {name}; stop and investigate')
            if name=='metrics':
                primary=comparison[(comparison.method=='fusion') & (comparison.pool=='official_dedup')]
                receipt['fusion_official_dedup_unchanged']=bool(primary.unchanged.all())
                if not primary.unchanged.all():
                    raise ValueError('Unexpected official_dedup fusion metric change; investigate precision/ties')
        (out/'fusion-weight.json').write_text((work/'fusion/fusion-weight.json').read_text())
        receipt.update(status='passed',comparisons=comparisons)
        result = {'scope':'cached-score correction only; no retraining', 'comparisons':comparisons, 'nonfusion_invariance_passed':True, 'fusion_official_dedup_unchanged':receipt['fusion_official_dedup_unchanged'], 'fusion_weight':json.loads((out/'fusion-weight.json').read_text())['chosen_w_mass']}
        (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        receipt.update(status='failed',error=portable(str(exc)))
        raise
    finally:
        receipt['wall_seconds']=time.time()-started
        receipt['artifacts']={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='run-receipt.json'}
        (out/'run-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'wall_seconds':receipt['wall_seconds'],'comparisons':comparisons},indent=2))

if __name__ == '__main__':
    main()
