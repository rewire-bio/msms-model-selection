# Disposition of the independent review (`review.md`)

Author: paper-author agent (Claude Opus, `claude-opus-5-5`, session `5b2a6d85-2616-43fe-bdde-40dd448ad762`).
Date: 2026-10-06. `review.md` is unchanged (owned by the reviewer). All 18 findings were accepted. After the fixes the
manuscript was rebuilt with `make paper-imported` (26 pages; 0 LaTeX and 0 BibTeX warnings; extraction cross-check 0
mismatches). The author re-rendered every page with `pdftoppm` at 45 dpi and inspected pages 14, 15, 17, 20 and 25, where
content or layout changed.

| Finding | Severity | Disposition |
|---|---|---|
| 1 §8 review claim before review existed; title-page wording | major | Fixed: title page now says "Drafted by an AI model"; §8 states that a draft was reviewed (18 findings) and that this version incorporates the disposition in this file. The final PDF was built after this file was written. |
| 2 New introduction generalisation with MassSpecGym citation | major | Fixed: replaced by "MSAlign v2 reports Recall@5 of 60.4–71.3% for its standalone alignment models … (Table 1)", citing MSAlign v2 only. |
| 3 Own-input instructions and Gupta/Giné qualifier missing | major | Fixed: new "Inputs and outputs" paragraph in §4.7 (MGF fields, candidate CSV frozen before scoring, supported adducts, mass-only behaviour, threshold definition, `ppm_error`, decision and `tied_with_previous` columns, provenance file); reassembly steps and full hash in §7; Gupta/Giné sentence restored before the novelty statement in §2.4; coverage map corrected. |
| 4 Table 9 raw row equals dedup | minor | Fixed: caption explains that sizes count distinct 2D structures and that the multiplicity-weighted raw length is not summarised in the archive. |
| 5 Abstract reports only favourable reproduction | minor | Fixed: abstract adds that Emb-Cos fell below and DeepSets far above the band, and that one seed is not a refutation. |
| 6 `mces_1` table caption | minor | Fixed: strict-rule sentence corrected (pool 16 at k = 20); median pool size (251) and sub64 minimum (24) added from the archive; warning against comparison with the formula-split tables added; random row labelled as the analytic expectation. |
| 7 Instrument strata status | minor | Fixed: Table 12 caption and §6 state that they were pre-specified as descriptive in the frozen protocol and labelled post hoc in the original; the §6 sentence now distinguishes pre-declared contrasts from pre-declared descriptive analyses (including `mces_1`). |
| 8 Missing evidence labels | minor | Fixed: Tables 9, 11, 13 and 16 now carry labels. |
| 9 Decision-path legibility | minor | Fixed: Figure 8 placed on its own page, rotated, at about 6–7 pt node text (was 4–5 pt); the original SVG is unchanged. |
| 10 Bibliography author rendering | minor | Fixed: "et al." rendered for MassSpecGym; `{d'Alch{\'e}-Buc}` braced for both MSAlign entries. |
| 11 §3.8 pointer | minor | Fixed: now cites the archived T02/T03 `released-result.json` receipts (also checked by the extractor). |
| 12 Availability precision | minor | Fixed: model-part paths, reassembly step, full SHA-256 and DreaMS revision in §7. |
| 13 Altered quotation | nit | Fixed: the consistency-check file is now included verbatim (both lines) by `\lstinputlisting`. |
| 14 Random-baseline wording | nit | Fixed in Tables 4, 10 and 15. |
| 15 Quotation attribution | nit | Fixed: MSAlign v2 cited after the quotation. |
| 16 Listing and float layout | nit | Fixed: smaller listing font so no line wraps; Table 15 floats; the remaining underfull line was removed. |
| 17 Degenerate rows in Table 16 | nit | Fixed: caption note. |
| 18 Licence URL in figure captions | nit | Fixed: CC BY 4.0 URL added to Figures 1 and 6. |

No experiment, inference, recomputation or network fetch was performed.
