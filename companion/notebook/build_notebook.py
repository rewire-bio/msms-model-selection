"""Write the walkthrough notebook (executed separately with nbclient)."""

from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
nb.cells = [
    md("""# Shortlisting candidate structures from an MS/MS spectrum

This notebook runs the companion tool on three real MassSpecGym spectra chosen by a fixed rule
(the first [M+H]+ and the first [M+Na]+ spectrum of the formula-split test fold, plus the
[M+H]+ spectrum with its true structure removed from the candidate file). It then loads the saved
benchmark receipts behind the article's numbers.

A shortlist is a set of structures to confirm, not an identification. Scores are not probabilities.
Identity is 2D: stereoisomers are not distinguished."""),
    code("""import json, platform, subprocess, sys
from pathlib import Path
import pandas as pd
import torch, rdkit
ROOT = Path.cwd().parent if Path.cwd().name == "notebook" else Path.cwd()
sys.path.insert(0, str(ROOT))
from msms_shortlist import __version__
from msms_shortlist.chem import exact_mass, neutral_mass, ppm_error
EX, MODELS = ROOT / "examples", ROOT / "models"
DREAMS = Path(ROOT / "weights" / "DreaMS_embedding_model_torchscript.pt")
OUT = ROOT / "notebook" / "outputs"; OUT.mkdir(exist_ok=True)
print("msms_shortlist", __version__, "| python", platform.python_version(), "| torch", torch.__version__, "| rdkit", rdkit.__version__)
print("DreaMS TorchScript present:", DREAMS.exists(), "| model bundle present:", (MODELS / "dreams_morgan_formula_seed1_fp16.pt").exists())"""),
    md("""## 1. Check the metadata before ranking anything

The neutral mass comes from the precursor m/z, the adduct and the charge. If any of them is missing
or inconsistent, the tool refuses to rank."""),
    code("""demo = json.loads((EX / "demo-inputs.json").read_text())
for key in ("mh", "mna"):
    d = demo[key]
    implied = neutral_mass(d["precursor_mz"], d["adduct"], 1)
    true = exact_mass(d["true_smiles_2d"])
    print(f"{key}: {d['massspecgym_identifier']} {d['adduct']} precursor {d['precursor_mz']} -> neutral {implied:.5f}; "
          f"annotated structure {true:.5f} ({float(ppm_error(implied, true)):+.2f} ppm); {d['n_candidates']} candidates")"""),
    code("""def run(spectra, candidates, out, model=True, extra=()):
    cmd = [sys.executable, "-m", "msms_shortlist.cli", "--spectra", str(EX / spectra),
           "--candidates", str(EX / candidates), "--out", str(OUT / out), *extra]
    if model:
        cmd += ["--model", str(MODELS / "dreams_morgan_formula_seed1_fp16.pt"), "--dreams", str(DREAMS),
                "--thresholds", str(MODELS / "thresholds.json")]
    print(subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip())
    prov = json.loads((OUT / out).with_suffix(".provenance.json").read_text())
    table = pd.read_csv(OUT / out) if (OUT / out).stat().st_size > 1 else pd.DataFrame()
    return table, prov

run("invalid-metadata.mgf", "mh-candidates.csv", "invalid.csv", model=False);"""),
    md("""## 2. The cheap baseline: rank by precursor mass error

Every isomer of the true structure has exactly the same monoisotopic mass, so mass error cannot
separate them. The tool reports how many candidates tie at the shortlist boundary."""),
    code("""mass, prov = run("mh.mgf", "mh-candidates.csv", "mh-mass.csv", model=False)
q = prov["queries"][0]
print("tie at shortlist boundary:", q["tie_at_shortlist_boundary"], "| candidates sharing the 5th score:", q["n_candidates_tied_with_shortlist_boundary"])
mass.head(8)[["rank", "id", "smiles_2d", "ppm_error", "tied_with_previous", "in_shortlist"]]"""),
    md("""## 3. The learned model: DreaMS spectrum embedding + Morgan fingerprint alignment

The model was trained here with the released MSAlign code (DreaMS + Morgan pair, released
formula-split settings, one seed). The decline threshold was fitted on validation spectra so that at
most 10% of queries with their answer removed would still get a shortlist."""),
    code("""model, prov = run("mh.mgf", "mh-candidates.csv", "mh-model.csv")
truth = demo["mh"]["true_structure_id"]
print("decision:", prov["queries"][0]["decision"], "| top score:", round(prov["queries"][0]["top_score"], 4),
      "| threshold:", round(prov["thresholds"]["tau"], 4))
print("rank of the annotated structure:", int(model.loc[model.id == truth, "rank"].iloc[0]))
model.head(5)[["rank", "id", "smiles_2d", "score_model", "ppm_error"]]"""),
    md("""The true structure is ranked first, yet the tool declines: its top score is far below the
threshold. On the test fold that threshold nominated only about one target-present query in five.
A strict decline rule buys fewer false nominations with a lot of silence."""),
    code("""absent, prov = run("mh.mgf", "mh-candidates-target-removed.csv", "mh-absent-model.csv")
print("decision with the true structure removed:", prov["queries"][0]["decision"],
      "| top score:", round(prov["queries"][0]["top_score"], 4))
absent.head(5)[["rank", "id", "smiles_2d", "score_model"]]"""),
    md("""## 4. A failure before ranking: the precursor value itself

The [M+Na]+ spectrum selected by the same rule records its precursor as 826.4. The annotated
structure implies 826.494, so the true answer lies 117 ppm away. A 10 or 50 ppm window around the
recorded value contains none of the candidates, and the tool says so instead of ranking an empty pool.
Only a window wider than about 120 ppm brings them back, and against a real database such a window
admits far more structures than this frozen candidate file holds."""),
    code("""for w in ("10", "50", "200"):
    _, prov = run("mna.mgf", "mna-candidates.csv", f"mna-{w}ppm.csv", extra=("--ppm", w))
    print(w, "ppm:", prov["queries"][0]["decision"], "| candidates in window:", prov["queries"][0].get("n_candidates_in_window"))"""),
    md("""## 5. The benchmark receipts behind the article

These tables are read from the saved analysis outputs; nothing is re-run here."""),
    code("""res = ROOT / "results"
metrics = pd.read_csv(res / "metrics.csv")
view = metrics.query("pool == 'official_dedup' and rule == 'expected'").pivot(index="method", columns="k", values="estimate")
view.round(1)"""),
    code("""metrics.query("rule == 'expected' and k == 5").pivot(index="method", columns="pool", values="estimate").round(1)"""),
    code("""ab = pd.read_csv(res / "abstention.csv")
ab.query("confidence == 'top1'")[["method", "threshold", "coverage_present_estimate",
    "recall5_among_nominated_estimate", "false_nomination_absent_estimate"]].round(3)"""),
]
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = Path(__file__).with_name("msms_shortlist_walkthrough.ipynb")
nbf.write(nb, out)
print(out)
