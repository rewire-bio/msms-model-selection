# Series-wide second review — 6 October 2026

This pass reviewed the maintained scoring, ranking and analysis code; input refusal paths; evidence validation and manuscript generation; cached-correction reproduction; and the current paper/blog claims. The original evidence and the corrected measurements remain unchanged.

## Findings and fixes

- [#12](https://github.com/rewire-bio/msms-model-selection/issues/12): keep declared methods with no successful predictions in every pool represented by the evaluation, with zero recall and the full failure count. Missing, nonfinite or negative rank counts now consistently count as failures. If every method lacks all pool rows, analysis fails explicitly because the available pools cannot be inferred.
- [#13](https://github.com/rewire-bio/msms-model-selection/issues/13): preserve malformed MGF blocks as explicit per-query refusals. Bad peaks, nested blocks, orphan endings and a missing final ending no longer crash or silently truncate a mixed batch. A file with no blocks fails explicitly.
- [#14](https://github.com/rewire-bio/msms-model-selection/issues/14): current-paper builds require the corrected evidence index and all required hash bindings. Historical validation remains a separate first stage, but missing correction metadata cannot silently restore superseded tables.

## Validation and result impact

All 73 regression tests pass. Historical and corrected evidence validation passes, including the original article cross-check. A software equivalence check on all five saved test-method rank files produced exactly equal before/after metrics for all 150 nonrandom method/pool/rule/k rows, using 20 diagnostic bootstrap draws. This check is a regression test, not a replacement scientific run or a new confidence-interval estimate.

The saved benchmark ranks are complete, finite and nonnegative, the evidence index is present, and the archived CLI examples contain valid MGF syntax. No historical or corrected numerical result is changed by these fixes. The paper and published blog therefore retain their corrected values and caveats. The verified cached-score correction remains the archived run at source revision `8b650adabc3f2cd833acb778dd7dd140d0f0e6f6`; independent training reproduction is still pending.

## Second pass

Reviewed the new failure branches against synthetic fixtures, checked the current evidence and generated tables without changing tracked outputs, and checked that normal saved-score inputs retain their previous behavior. Missing cached execution data remains explicitly distinct from the lightweight software/evidence check. No additional substantive finding was identified in this pass; this is not a guarantee that the repository is defect-free.
