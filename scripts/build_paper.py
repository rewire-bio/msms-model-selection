#!/usr/bin/env python3
"""Build the imported-evidence manuscript with the locally installed TeX Live.

Steps (no experiment, no data fetch, no environment creation, no network):
  1. scripts/paper_extract.py  -- format archived metrics into paper/generated/*.tex
  2. scripts/paper_ledger.py   -- write evidence/paper-migration/claims-ledger.json
  3. convert the original decision-path SVG in article/assets/ to PDF in paper/figures/ (rsvg-convert);
     the originals are left untouched, PNG figures are read in place
  4. pdflatex -> bibtex -> pdflatex -> pdflatex into paper/build/
  5. record tool versions, exact commands, warnings and output digests in
     evidence/paper-migration/build-receipt.json

Standard library only. Usage: `make paper-imported` or `python3 scripts/build_paper.py`.
(The previous Tectonic-based builder targeted the generic harness fixture; scripts/bootstrap_tectonic.py
is left in place but is no longer used for the manuscript.)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
BUILD = PAPER / "build"
FIGS = PAPER / "figures"
RECEIPT = ROOT / "evidence/paper-migration/build-receipt.json"
TEXBIN = Path("/Library/TeX/texbin")
SVG_FIGURES = ["01-decision-path"]


def tool(name: str) -> str:
    cand = TEXBIN / name
    if cand.exists():
        return str(cand)
    found = shutil.which(name)
    if not found:
        sys.exit(f"required tool not found: {name}")
    return found


def first_line(cmd: list[str]) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    return (out.stdout or out.stderr).strip().splitlines()[0]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path, env: dict, log: list) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, errors="replace")
    shown = [Path(c).name if c.startswith("/") else c for c in cmd]
    rel = str(cwd.relative_to(ROOT)) if cwd != ROOT else "."
    log.append({"cwd": rel, "command": " ".join(shown), "exit": proc.returncode})
    return proc


def main() -> None:
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = "1791244800"  # 2026-10-06T00:00:00Z (manuscript migration date), fixed for reproducible PDF metadata
    env["FORCE_SOURCE_DATE"] = "1"
    env["TZ"] = "UTC"
    commands: list = []

    for script in ("paper_extract.py", "paper_ledger.py"):
        proc = run([sys.executable, f"scripts/{script}"], ROOT, env, commands)
        sys.stdout.write(proc.stdout)
        if proc.returncode:
            sys.stderr.write(proc.stderr)
            sys.exit(f"{script} failed")

    FIGS.mkdir(parents=True, exist_ok=True)
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        sys.exit("rsvg-convert is required to convert the original SVG figures")
    figures = {}
    for name in SVG_FIGURES:
        src = ROOT / "article/assets" / f"{name}.svg"
        dst = FIGS / f"{name}.pdf"
        proc = run([rsvg, "-f", "pdf", "-o", str(dst.relative_to(ROOT)), str(src.relative_to(ROOT))], ROOT, env, commands)
        if proc.returncode:
            sys.exit(proc.stderr)
        figures[str(dst.relative_to(ROOT))] = {"from": str(src.relative_to(ROOT)), "source_sha256": sha256(src)}

    BUILD.mkdir(parents=True, exist_ok=True)
    for stale in BUILD.glob("main.*"):
        stale.unlink()
    pdflatex, bibtex = tool("pdflatex"), tool("bibtex")
    latex = [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-output-directory=build", "main.tex"]
    for i, cmd in enumerate([latex, "bibtex", latex, latex]):
        if cmd == "bibtex":
            benv = dict(env, BIBINPUTS=f"{PAPER}:", BSTINPUTS=f"{PAPER}:")
            proc = run([bibtex, "main"], BUILD, benv, commands)
            (BUILD / "bibtex.stdout.txt").write_text(proc.stdout)
            if proc.returncode:
                sys.stdout.write(proc.stdout)
                sys.exit("bibtex failed")
            continue
        proc = run(cmd, PAPER, env, commands)
        if proc.returncode:
            sys.stdout.write(proc.stdout[-4000:])
            sys.exit(f"pdflatex pass {i} failed")
    # Extra passes only while LaTeX reports that cross-references may have changed (at most two).
    for _ in range(2):
        if "Rerun to get cross-references right" not in (BUILD / "main.log").read_text(errors="replace"):
            break
        proc = run(latex, PAPER, env, commands)
        if proc.returncode:
            sys.exit("pdflatex rerun failed")

    log = (BUILD / "main.log").read_text(errors="replace")
    blg = (BUILD / "main.blg").read_text(errors="replace") if (BUILD / "main.blg").exists() else ""
    warnings = [line.strip() for line in log.splitlines()
                if re.search(r"(LaTeX|Package \w+) Warning|Overfull|Underfull|undefined", line)]
    bib_warnings = [line.strip() for line in blg.splitlines() if line.startswith("Warning") or "error" in line.lower()]
    (BUILD / "warnings.txt").write_text("\n".join(warnings + bib_warnings) + "\n")

    pdf = BUILD / "main.pdf"
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
        sys.exit("no valid PDF produced")
    pages = None
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        pages = int(m.group(1)) if m else None

    receipt = {
        "schema_version": 1,
        "kind": "historical and corrected cached-score manuscript build; compiling is not scientific verification",
        "built_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "tools": {
            "pdflatex": first_line([pdflatex, "--version"]),
            "bibtex": first_line([bibtex, "--version"]),
            "rsvg-convert": first_line([rsvg, "--version"]),
            "python": sys.version.split()[0],
            "tex_distribution": "TeX Live 2026 (local install under /Library/TeX/texbin)",
        },
        "environment": {"SOURCE_DATE_EPOCH": env["SOURCE_DATE_EPOCH"], "FORCE_SOURCE_DATE": "1", "TZ": "UTC"},
        "commands": commands,
        "figures_converted": figures,
        "outputs": {"paper/build/main.pdf": {"sha256": sha256(pdf), "bytes": pdf.stat().st_size, "pages": pages}},
        "warnings": {"latex": warnings, "bibtex": bib_warnings,
                     "counts": {"latex": len(warnings), "bibtex": len(bib_warnings)}},
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{pdf.relative_to(ROOT)}: {pages} pages; {len(warnings)} LaTeX warnings, {len(bib_warnings)} BibTeX warnings")


if __name__ == "__main__":
    main()
