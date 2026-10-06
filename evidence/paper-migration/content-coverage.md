# Content coverage: original article to manuscript

Original: `article/published-original.md` (byte-identical published copy; SHA-256
`21355078f6c7ff3cc9a9e0ff0f9768fb7b767eb450fbafe456bc7548456fc8bc`), *An MS/MS Shortlist Is Not an Identification: Choosing a
Formula-Free Ranker and Knowing When to Decline* (5 October 2026). Manuscript: `paper/main.tex` → `paper/build/main.pdf`.
The original is retained unchanged as Supplement S1 (repository file and PDF attachment `S1-published-original.md`).

Generated tables come from members of `downloads/msms-shortlist-results.tar.gz` read in memory by `scripts/paper_extract.py`
(plus the imported `companion/results/fusion-weight.json`). Every value that also appears in the original article (Tables
3–7, pool-size, tie-rule and abstention values, contrasts including the expanded-pool C2, threshold, fusion weight, training
time) is cross-checked at printed precision; recorded result 0 mismatches (`paper/generated/extraction-receipt.json`).

Numbering map — original → manuscript: Table 1 (methods) → Table 2; Table 2 (published) → Table 1; Table 3 → Table 3;
Table 4 → Table 4; Table 5 → Table 5; Table 6 → Table 7; Table 7 → Table 8. Figures 1–8 keep their numbers.

| Original section / element | Scientific content | Manuscript location | Notes |
|---|---|---|---|
| Front matter: excerpt | 10,648/1,421; 61.4% and 63.2% vs 13.3%; top score weak signal | Title, status box, Abstract | |
| FAQ 1 (which method) | 63.2 / 61.4 / 31.3 / 13.3; no detectable difference; DreaMS + Morgan as shipped, Emb-Cos if training | Abstract; §4.2; §5.1 | |
| FAQ 2 (mass error alone) | 13.3%; isomers; half of hits from 21% recomputed-looking precursors; 31.6 vs 9.2 | §2.1; §4.6; Table 8 | |
| FAQ 3 (high score ≠ correct) | not a probability; 21.3% covered, 13.2% false; confirm against standard | §4.5; Table 7; §6 (No identification) | |
| FAQ 4 (list size) | 94.5 → 61.4 → 41.3 (DreaMS + Morgan); 93.8 → 63.2 → 45.9 (Emb-Cos); quote list size | §4.3; Figure 3; App. Table 10 | |
| FAQ 5 (running the tool) | uv sync; MGF with PEPMASS/CHARGE/ADDUCT; frozen candidate CSV; refusal and window reporting; DreaMS weights separate | §4.7 (Inputs and outputs); §5.1; App. A; §7 | Added after review (finding 3) |
| FAQ 6 (decline) | threshold 0.599; declines ~4 in 5 present queries; ranked list still written; recheck precursor | §4.5; §4.7; §5.1 | |
| FAQ 7 (relation to MSAlign) | v2 three-seed means; MolDeBERTa not run; strict ties in released code; 32.6% R@1 just below 33.0–44.2 | §2.3; §4.1; Table 3 | |
| Lead paragraphs | Recommendation; 252-structure pools; DeepSets 31.3, mass 13.3, random 2.1; population; 41.3 / 45.9; five evidence labels; shortlist ≠ identification | Abstract; §1; status box (labels); §4.2–4.3 | |
| §"The task is ranking a frozen, mass-matched list…" | precursor, adducts, ppm pools; MassSpecGym pool rule (quote); pools centred on annotated mass; 32.6% isomer decoys; Kind & Fiehn; 2D identity; Recall@k definition; formula track excluded | §2.1; §3.5 | |
| Table 1 (methods) | Inputs and scores of six methods; fusion weight 0.55 | Table 2; §3.4 | Training settings added from the archived protocol and T01 receipt |
| Morgan / contrastive / DreaMS / abstention definitions | | §2.2; §3.7 | |
| §"Published numbers…" + Table 2 + Figure 1 | v2 means ± SD; v1/v2 disagreement (22.2/48.5 vs 4.7/38.6; ChemBERTa vs MolDeBERTa); untested strongest rows (MolDeBERTa CC BY-NC-ND, 20 GB cache, CUDA for JESTR/FLARE/MVP); audit 17 of 26; 0.43% → 12.98% | §2.3; Table 1; Figure 1 | Table 1 transcribed from the article |
| §"The harness reproduces…" + Table 3 | Released rule; harness exactness; three models vs two-SD bands; early peak 0.376; DeepSets near v1; one seed is not a refutation | §4.1; §3.8; Table 3 | Harness = released evaluation checked again against T02/T03 receipts at extraction |
| §"Under a frozen protocol…" + Table 4 + Figure 2 | dedup (85.4% of 28,936 lists; mean 6.9, max 121; median 252); random-tie rule; main results; no failures | §3.3; §3.5; Table 4; Figure 2 | |
| Table 5 + paragraphs | C1, C2, C3; no alignment-vs-fingerprint contrast; non-overlap; C2 not equivalence and not a pretraining test; controlled pair published only | Table 5; §4.2; App. Table 16 (all 90 archived contrasts) | |
| Training-time and choice paragraph | 3.0 h vs 7.75 h; step budgets; companion ships DreaMS + Morgan | §3.9; §5.1 | |
| Fusion paragraph | 64.8% exploratory, not recommendation | §4.2; §4.6 | |
| §"More candidates mean fewer hits…" + Figure 3 | Pool construction (16, 64, 449 with IQR 296–691; 5.1% at cap); values; family order; within-family reversal; −4.56 [−7.95, −1.19] not pre-declared; Giné quote | §3.3; §4.3; Figure 3; §2.4; App. Tables 9–10 | |
| §"Scoring conventions…" + Figure 4 | 6.3 → 13.3; 0.8 → 3.7; 56.8 → 61.4; isomer ties; MSAlign Gaussian scorers 0.6–0.8% (inference); Gupta / Guo quotes | §4.4; Table 6 (new, formatted from archive); Figure 4; §2.4 | |
| §"The top score is only a weak signal…" + Table 6 + Figure 5 | Target removal as stress test; thresholds; table values; margin alternative 13.8/9.6, 18.4/9.8; mass error 12.2 = 12.1; choice of failure mode | §3.7; §4.5; Table 7; Figure 5; App. Table 11 | |
| Figure 6 + related-work paragraph | Jürgens framing and quotes; COSMIC; MS2Query; novelty statement dated 4 Oct 2026 | Figure 6; §2.4 (incl. the Gupta/Giné qualifier) | |
| §"Check the precursor value…" + Figure 7 + Table 7 | 19.1% / 7.07% / median 0.211; training 19.0%; Kind & Fiehn accuracy; Spectraverse quote; 6.94% >10 ppm and 16.1% >5 ppm (A1); strata; fusion +8.4 / +2.4; mass as filter not ranker | §4.6; Figure 7; Table 8; App. Table 14; §3.1 | A1 validation and mces_1 percentages added from the archived protocol amendment |
| §"Running the shortlist…" + Figure 8 + console blocks | Inputs; commands; decline rule 0.599; fixed-rule demo spectra; verbatim outputs; interpretation (30-way tie; 0.019; −117 ppm; 227 of 229); timings; DreaMS equivalence; 2.2e-4 match; downloads | §4.7 (Inputs and outputs, Demonstration); Figure 8 (rotated full page); App. A; App. B (verbatim outputs); §7 (model parts, full hash, reassembly) | |
| §"What to do in each situation" | precursor check; no-candidate handling; decline as triage; refit threshold (conformal study); mass-only ties | §5.1 | |
| §"What this comparison does not show" | seeds; untested methods; untested data and instrument strata; encoder overlap; near-duplicates (34.7%); shortcut controls; no identification (MSI, Schymanski, Charbonnet) | §6; App. Table 12 | Added: target-present pools; exploratory/post hoc list |
| §"What would change this recommendation" | Three results; practical sequence | §5.2; §5.1 | |
| References (23) | Bibliography | `paper/references.bib` (23 entries) | No DOI, year or author added beyond the original |

## Additions beyond the original article (archived evidence only; no new computation)

- Table 6: Recall@5 / Recall@1 under four counting conventions (the article plotted three in Figure 4).
- App. Tables 9–16: pool-size distributions; Recall@5 and Recall@1 by pool for every method; all decline-threshold results
  (both confidences, both rules); instrument strata with intervals; fusion weight grid; per-fold precursor audit; the
  **pre-declared secondary population `mces_1`** (cheap baselines only), which the archive holds but the article did not
  report; all 90 archived paired contrasts.
- Methods detail from the archived frozen protocol (§3.1–3.8): freeze time and hash, amendment A1, pool definitions,
  training settings, confidence definitions, harness acceptance criterion.

## Not carried into the manuscript body (retained in Supplement S1)

- FAQ format, second-person phrasing and front-matter fields.
- Site-relative download links; the manuscript names repository paths instead.

## Provenance notes

- Some archived receipts (for example `receipts/T01-…/train-receipt.json`, `receipts/P02-…/pools.receipt.json`) and the
  imported `companion/results/T01-train-receipt.json` contain absolute local paths from the original run machine. These
  original files are preserved unchanged; no such path is reproduced in the manuscript or the generated tables.
