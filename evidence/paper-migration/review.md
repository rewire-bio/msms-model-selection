# Independent review: imported-evidence manuscript "An MS/MS shortlist is not an identification"

- **Reviewer:** Claude Opus (`claude-opus-5-5`), an independent instance that did not write the manuscript. This is an AI review, not a human scientific review.
- **Date:** 2026-10-06
- **Object reviewed:** `paper/main.tex`, `paper/references.bib`, `paper/generated/*.tex`, `paper/build/main.pdf` (25 pages, build receipt dated 2026-10-06T11:04:33Z), `paper/build/warnings.txt`, `paper/build/main.log`/`main.bbl`/`main.blg`.

## Scope and what I did

- **Read in full:** `article/published-original.md`; `paper/main.tex`; `paper/references.bib`; every file in `paper/generated/`; `evidence/paper-migration/content-coverage.md`, `status.json`, `build-receipt.json`, `extraction-receipt.json`; the claims ledger (all 23 claim records, summarised); `companion/README.md` and `companion/REPRODUCE.md` (by grep); and the relevant parts of `scripts/paper_extract.py` and `companion/scripts/{analyse,rank_stats}.py`.
- **Archive members read without extracting files** (`tar -xzOf downloads/msms-shortlist-results.tar.gz …`): `analysis/{metrics,contrasts,abstention,strata-post-hoc,pool-sizes}.csv`, `analysis/random-repeats.json`, `analysis-mces1/{metrics,pool-sizes}.csv`, `analysis-mces1/random-repeats.json`, `protocol/{protocol.md,protocol-frozen-original.md,protocol-freeze-receipt.txt}`, `receipts/A02-…/summary.json`, `receipts/T01-…/train-receipt.json`, `receipts/T02-…` and `receipts/T03-…/released-result.json`, `receipts/V01-…/result.json` and `receipts/X02-…/consistency-check.txt`. I diffed the frozen original against the amended protocol (the only difference is amendment A1) and checked the SHA-256 of the frozen original against the freeze receipt (`aa2b30b5…31b6`; they match).
- **Numerical comparison:** I compared values read from the archive with the printed values, with no recomputation of any statistic:
  - every cell of Tables 3–8 and 10–15 against the archive;
  - all 90 rows of Table 16 against `contrasts.csv`, using a string comparison script;
  - every number in the text against the original article and the archive.
- **Rendering:** I rendered all 25 pages with `pdftoppm -r 50` and viewed **pages 1–25**. I also viewed higher-resolution crops of p. 8 (Table 3, 110 dpi), p. 9 (Table 5 and Fig. 2, 100 dpi), p. 12 (Fig. 6, 100 dpi) and p. 14 (Fig. 8, 100 dpi). Rendering succeeded with no errors.
- **Other checks:** I extracted the PDF text to search for personal paths and credentials (none found). I detached the embedded attachment `S1-published-original.md`; its SHA-256 (`21355078…c8bc`) is identical to `article/published-original.md`. Temporary files under `/tmp/msms-review/` were deleted afterwards.
- **Not done:** no experiments, inference, training, bootstrap, `make`, `uv`, companion scripts or network access. The cited literature was not re-retrieved.

## Overall assessment

The manuscript is a faithful, careful conversion.

**Numerical fidelity is excellent.** I found no numerical mismatches:
- Tables 3–8 and 10–16, and every result quoted in the text, agree with the archive and with the original article at printed precision.
- The extractor's cross-check (0 mismatches) is borne out.
- The 2-SD bands in Table 3 are arithmetically correct from the published means and SDs.

**Labels, framing and coverage are mostly sound.**
- Evidence labels and pre-declared/exploratory status match the original in the main body.
- The status box, abstract, running header and the §4.8 box state clearly that these are existing results and that independent reproduction is pending.
- Every original table, comparator, null result (C2), negative result (Emb-Cos and DeepSets outside the band; mass error showing no decline signal) and limitation is present.
- Supplement S1 is embedded byte-identically.
- The bibliography has exactly the original's 23 references, with no added DOIs, years or authors.
- The `mces_1` appendix table is numerically accurate and correctly described as a pre-declared, cheap-baseline-only secondary population that the original did not report. Its caption contains one false statement (finding 6).

**What remains is three major issues and a set of minor ones.**
- **Disclosure:** §8 asserts that a review exists before it existed.
- **New claim:** one new literature generalisation with a misattributed citation.
- **Coverage:** a coverage gap in the own-input instructions, which `content-coverage.md` wrongly reports as covered.
- **Minor:** mislabelled or unlabelled appendix tables, two bibliography rendering errors and an illegible decision-path figure.

None of these affects the scientific results. All are straightforward to fix.

## Findings

### 1. [major] §8 asserts an AI review and disposition before they existed
- **Location:** `main.tex` l.688–691 (PDF p. 17); title page l.69.
- **Evidence:**
  - The PDF states that the manuscript "was drafted by an AI model … and reviewed by an independent AI reviewer instance of the same model; the review and its disposition are recorded in `evidence/paper-migration/`".
  - At build time, `status.json` records `"stage": "draft_built_awaiting_review"`, and neither `review.md` nor `review-disposition.md` existed. The disposition still does not exist.
  - The title page says "Drafted with AI assistance", which understates §8's "drafted by an AI model".
- **Fix:**
  - Make the sentence true at the time of the build that is released, for example "…was reviewed by an independent AI instance (`review.md`); the author's disposition is in `review-disposition.md`". Rebuild only after both files exist, or phrase it conditionally.
  - Align the title-page wording with §8 ("Drafted by an AI model; see Section 8").
  - Keep the existing (correct) sentence that no human review has taken place.

### 2. [major] New literature generalisation with a misattributed citation
- **Location:** §1, `main.tex` l.117–118 (PDF p. 3).
- **Evidence:**
  - The text reads: "Learned alignment models, which embed spectra and structures in a shared space, report strong Recall@k on the MassSpecGym benchmark~\citep{bushuiev2024massspecgym,krzakala2026msalignv2}."
  - The original makes no such statement and never cites MassSpecGym for results of alignment models. It cites MassSpecGym only for pool construction and MoNA provenance.
  - This is the same class of defect as the unsupported generalisations found in the sibling paper.
- **Fix:** Cite only `krzakala2026msalignv2` and anchor the sentence to Table 1 (for example "MSAlign v2 reports Recall@5 of 60–71% for its standalone alignment models on the formula split (Table 1)"), or delete the sentence. The following sentence ("Published numbers, however, depend on…") is a fair synthesis of the original's three caveats and can stay.

### 3. [major] Own-input instructions and one literature qualifier are missing, and `content-coverage.md` wrongly reports them as covered
- **Location:** §4.7, §5.1, §2.4 and Appendix A; `content-coverage.md` rows "FAQ 5", "Running the shortlist…" and "What to do in each situation".
- **Evidence:** `grep` of `main.tex` finds none of the following original content:
  - **Input format (original l.230):** spectra go in an MGF file with `PEPMASS`, `CHARGE` and `ADDUCT` in every block; candidates go in a CSV with `id` and `smiles` columns, "frozen before you look at any scores". The last point is a methodological safeguard, not just formatting.
  - **Output columns and provenance (l.305–311):** `ppm_error`; the provenance file records the window; the ranked CSV has a decision column and tie flags; the `tied_with_previous` column.
  - **Threshold file:** the definition of the value in `models/thresholds.json` (0.599, "the lowest value that nominated at most 10% of target-removed validation queries") is only implicit.
  - **Model download:** the reassembly procedure and full-hash verification for the three model parts (l.299).
  - **Literature qualifier:** "Gupta et al. and Giné et al. varied candidate sets in other ways" (l.198). This sentence qualifies the novelty statement that the manuscript keeps in §2.4.
  - Row FAQ 5 of `content-coverage.md` maps "MGF with PEPMASS/CHARGE/ADDUCT; frozen candidate CSV" to "§4.7; §5.1; App. A; §7", but none of those places contains it.
- **Fix:**
  - Add a short "Inputs and outputs" paragraph to §4.7 or Appendix A covering the MGF fields, the candidate CSV frozen before scoring, the `ppm_error`/`tied_with_previous`/decision columns, the provenance file and the threshold definition.
  - Add the reassembly steps and the full hash in §7 (see finding 12).
  - Restore the Gupta/Giné sentence before the novelty statement in §2.4.
  - Correct `content-coverage.md`.

### 4. [minor] Table 9 shows identical sizes for `official, raw` and `official, dedup.`, contradicting §3.3
- **Location:** Table 9 (PDF p. 20), `tab_poolsizes.tex`.
- **Evidence:**
  - Both rows show mean 240.4, quartiles 243/252/255 and max 256.
  - The archive's `pool-sizes.csv` summarises `n_pool`, which is the number of distinct structures (`companion/scripts/rank_stats.py` l.70). Multiplicity is held separately in `n_pool_weighted`, which is not summarised.
  - So the raw row is not the "list as distributed, duplicates counted with their multiplicity" described in §3.3. Read literally, it contradicts "85.4% of the 28,936 official lists contain at least one repeated structure".
- **Fix:** Add a caption note ("sizes count distinct 2D structures; for `official, raw` the multiplicity-weighted list length is not summarised in the archive"), or drop the raw row.

### 5. [minor] Abstract reports only the favourable reproduction result
- **Location:** Abstract, `main.tex` l.100–101.
- **Evidence:** The abstract gives DreaMS + Morgan's 32.6% "just below the published two-SD band". It omits that Emb-Cos fell below the band on all three cut-offs and that DeepSets was far above it. Both are in the original (its section heading reads "at one seed only DreaMS + Morgan lands mostly inside the paper's band") and in §4.1.
- **Fix:** Add a clause such as "…Emb-Cos fell below the band at all three cut-offs and DeepSets far above it; one seed is not a refutation."

### 6. [minor] `mces_1` appendix table (Table 15): one false caption statement and missing context
- **Location:** Table 15 (PDF p. 23), `main.tex` l.865–868.
- **Evidence:**
  - **Values:** all 48 rows match `analysis-mces1/metrics.csv` exactly at printed precision. The "pre-declared secondary descriptive population, cheap baselines only" description matches protocol §2. The "new measurement, descriptive" label and the "not reported in the original" disclosure are accurate.
  - **False statement:** "Under the strict rule every candidate ties for random ordering, so it scores 0" is wrong for pool 16 at k = 20, which the table itself prints as 100.0 [100.0, 100.0].
  - **Missing context:**
    - The caption gives no pool sizes. The archive's `analysis-mces1/pool-sizes.csv` gives a dedup median of 251 and a sub64 minimum of 24, and the paper itself insists on quoting list size.
    - There is no caution that mass-error values on this fold (23.4% R@5 on dedup) cannot be compared with the formula-split 13.3%. The fold differs, and its share of recomputed-looking precursors was not audited.
- **Fix:**
  - Correct the strict-rule sentence ("…scores 0 except where the pool is no larger than k").
  - Add the median pool size.
  - Add one sentence warning against comparing these values with Tables 4 and 10.

### 7. [minor] Instrument strata labelled "post hoc" although the frozen protocol pre-specified them as descriptive
- **Location:** Table 12 caption; §6 bullet "Exploratory and post hoc analyses" (l.662–664).
- **Evidence:**
  - Protocol §5 (frozen original) says: "Also reported: … per-instrument strata (Orbitrap, QTOF) if the TSV join is unambiguous, descriptive only."
  - The manuscript inherits the original's "post hoc" label and states "only C1–C3 were pre-declared". That sentence also overlooks the pre-declared `mces_1` population.
  - The precursor-error strata are genuinely post hoc.
- **Fix:**
  - Keep the original label but add "(pre-specified as descriptive in protocol §5; labelled post hoc in the original article; 862 test spectra could not be mapped)".
  - Reword "only C1–C3 were pre-declared" to "only C1–C3 were pre-declared contrasts; the instrument strata and the `mces_1` population were pre-declared as descriptive".

### 8. [minor] Several appendix tables have no evidence label
- **Location:** Tables 9, 11, 13 and 16.
- **Evidence:** The status box says "Each number carries one of five labels", but these four tables have none. Table 11 mixes stress-test rows with exploratory margin-confidence rows. Table 13 (fusion weight) is exploratory. Table 16 is new measurement, descriptive except for C1–C3.
- **Fix:** Add the labels:
  - Table 9: NEW MEASUREMENT, descriptive.
  - Table 11: NEW MEASUREMENT (stress test); margin rows exploratory.
  - Table 13: exploratory.
  - Table 16: NEW MEASUREMENT; only the rows marked primary were pre-declared.

### 9. [minor] Figure 8 (decision path) text is illegible at print size
- **Location:** PDF p. 14.
- **Evidence:** At `\linewidth`, the converted SVG's box text is about 4–5 pt. At 100 dpi it is only just readable, and at 50 dpi it is not. The figure carries substantive numbers (6.94%, 63.2/61.4/31.3/13.3/2.1, 94.5/61.4/41.3, 0.599, 21.3%/13.2%), and most of its area is whitespace.
- **Fix:** Crop the whitespace (for example `rsvg-convert` with a tighter viewBox, or `trim=`/`clip`), give the figure its own page with larger scaling, or re-render it from the D2 source with larger fonts.

### 10. [minor] Two bibliography rendering errors in author names
- **Location:** References [1], [2] and [7] (PDF p. 17).
- **Evidence:**
  - `main.bbl` l.10 renders [1] as "F. Kretschmer, others, and T. Pluskal". The literal word "others" appears because BibTeX treats `others` as et al. only in the final position. The original reads "Kretschmer F, et al., Pluskal T".
  - [2] and [7] render "F. d'Alché Buc" (`main.bbl` l.22 and l.67). The hyphen is lost; the original has "d'Alché-Buc F".
- **Fix:**
  - For [1], use `Kretschmer, F. and {et al.} and Pluskal, T.`, or end the list with `and others` and give the final author in a note.
  - For [2] and [7], brace the surname: `{d'Alch{\'e}-Buc}, F.`.

### 11. [minor] §3.8 cites Appendix D for a statement Appendix D does not contain
- **Location:** `main.tex` l.325–326.
- **Evidence:**
  - The text says: "for Emb-Cos and DeepSets the harness test values equal the released code's own end-of-training evaluation to 0.01 points (Appendix D)".
  - Appendix D contains no such statement.
  - The claim itself is supported by the archived `receipts/T02-…/released-result.json` (35.36/59.32/76.83) and `receipts/T03-…/released-result.json` (13.11/27.92/46.94), which equal the `official_raw`/strict harness values, and by the extractor check (`paper_extract.py` l.150–153).
- **Fix:** Cite the T02/T03 receipts, or add a sentence to Appendix D.

### 12. [minor] Model and download availability is less precise than the original
- **Location:** §7, `main.tex` l.677–681.
- **Evidence:**
  - The model parts are given without repository paths. The actual files are `downloads/msms-shortlist-dreams-morgan-model.tar.gz.part01–03`, `downloads/reassemble-model.sh` and `downloads/msms-shortlist-dreams-morgan-model.parts.sha256`.
  - The SHA-256 is abbreviated to `646bbe4f…effc9`, although the original prints the full hash for verification.
  - The DreaMS revision `c81a62766b10` appears only inside the bibliography entry.
- **Fix:** Give the paths, the full hash, the "save all five files and run `sh reassemble-model.sh`" step, and the HF revision in the text.

### 13. [nit] An altered quotation in Appendix B
- **Location:** Appendix B, l.756–757, and the macro `\CLIConsistency`.
- **Evidence:** The text presents the consistency check as a quotation of what the archived file "reads". The extractor replaces `|` with ` ;` (`paper_extract.py` l.344) and drops the second line ("harness rank of target among dedup pool: 1 | CLI rank: 1").
- **Fix:** Quote the file verbatim (both lines) in the listing, or paraphrase without quotation marks.

### 14. [nit] Inconsistent description of the random baseline
- **Location:** Table 4 caption and row label; Table 10 caption; Table 15.
- **Evidence:** Tables 4 and 10 use the mean of 100 seeded orderings (`random-repeats.json`), but label it both as "expectation" and as "expectation over 100 repeated orderings". Table 15 instead uses the analytic expectation from `metrics.csv`, with bootstrap intervals. The values are identical at printed precision (0.4/2.1/8.5).
- **Fix:** Say "mean of 100 random orderings (equal to the analytic expectation at printed precision)", and state in the Table 15 caption that it shows the analytic expectation.

### 15. [nit] Ambiguous attribution of a quotation in §2.3
- **Location:** `main.tex` l.175–176.
- **Evidence:** The quotation "will be released upon publication" is followed only by `\citep{moldeberta_card}`, which attaches to the licence clause. The original attributes the quotation to MSAlign v2 ([^4]).
- **Fix:** Add `\citep{krzakala2026msalignv2}` directly after the quotation.

### 16. [nit] Listing and float layout
- **Location:** PDF pp. 19–22.
- **Evidence:**
  - In the Appendix B listing, one long line ("decision with the true structure removed: …") wraps.
  - The listing breaks across pp. 19–20, leaving a single orphan line on p. 20.
  - Page 22 is about half blank because Table 15 is `[H]` and does not fit.
  - The only build warning is one underfull hbox (l.900–905; `warnings.txt`); there are no overfull boxes and 0 BibTeX warnings.
- **Fix:**
  - Use a slightly smaller listing font, or keep the listing on one page (`\needspace` or a float).
  - Let Table 15 float (`[tp]`) or set it as a `longtable`.

### 17. [nit] Degenerate rows in Table 16 are unexplained
- **Location:** Table 16 (pp. 24–25).
- **Evidence:** Rows for pool 16 at k = 20 show +0.00 [+0.00, +0.00] for every contrast.
- **Fix:** Add a caption note that with 16 candidates every method has Recall@20 = 100%.

### 18. [nit] Literature-figure attributions are abbreviated
- **Location:** Fig. 1 and Fig. 6 captions.
- **Evidence:** The original captions give the full author list and the licence URL. The manuscript gives "Krzakala et al." / "Jürgens et al." with a bibliography citation and "CC BY 4.0". The attribution is adequate through the bibliography, but less complete than the original.
- **Fix (optional):** Add the licence URL (https://creativecommons.org/licenses/by/4.0/) to both captions.

## Checks that passed (for the record)

- **Numbers:** every number in the abstract, the body text and Tables 3–8 and 10–16 matches the archive and the article. This includes:
  - C1 +48.0 [+42.2, +53.6], C2 −1.85 [−5.19, +1.35] and C3 +18.0 [+13.4, +22.5];
  - expanded-pool C2 −4.56 [−7.95, −1.19];
  - thresholds 0.5994 and 0.4653;
  - 13.8/9.6 and 18.4/9.8 for the margin-confidence rows;
  - 21.3% (2,264/10,648) and "about half" (≈50% of mass-error hits);
  - fusion gains +8.4 and +2.4;
  - n = 220,456, 19.1% and 7.07%;
  - 7.75 h (27,890 s);
  - 0.99999988 over 64 spectra;
  - A1 values (6.94/16.1, 5.43/9.2, 4.18/15.4) against the protocol amendment;
  - freeze time and hash against the receipt.
- **Labels:** PUBLISHED, REPRODUCTION, NEW MEASUREMENT and POST HOC are correct in the main body. Fusion, the margin confidence, the expanded-pool contrast and window coverage (A1) are all marked exploratory or not pre-declared.
- **References:** 23 entries, matching the original one-for-one. "n.d." is used where the original gives no year; no DOI or year was added.
- **Privacy:** no personal paths, credentials or private logs appear in the PDF text or the generated tables.
- **Licences:** the licence statements (companion MIT, `towers.py` adapted from MSAlign under MIT, MassSpecGym MIT, Zenodo CC BY 4.0, DreaMS MIT, MolDeBERTa CC BY-NC-ND 4.0, literature figures CC BY 4.0) are supported by the original article, `companion/README.md` and `companion/REPRODUCE.md`.
- **Reproduction status:** the manuscript states correctly that the repository `protocol.md` is an unapproved scaffold and that no reproduction was executed. It makes no claim of verification, approval or human review (apart from finding 1).

## Author disposition

_To be completed by the paper author (see review-disposition.md)._
