# Formula-free MS/MS molecular shortlisting

Status: UNAPPROVED

## Research question

Which model and baseline should be used for formula-free ms/ms molecular shortlisting, within the original measured scope?

## Purpose and contribution

UNCONFIGURED: the research designer must complete this protocol and the engineer must replace the disabled example implementation before execution.

## Hypotheses and estimands

Fixture only: estimate pi using four times the mean of indicators that a uniform
point in the unit square lies inside the unit quarter circle. The analytical
reference is `math.pi`. The fixture checks execution and provenance, not novelty.
Replace this section for a substantive study.

## Data, provenance, and licences

The fixture generates synthetic points with Python's seeded `random.Random`.
No external dataset is required. Record external inputs in `data/manifest.json`
with a stable URL, local path, SHA256, licence, and provenance before use.

## Methods, controls, and baselines

Use 100,000 independent point pairs, seed 20261001, and the analytical reference.
The 1,000-point smoke run is operational only and cannot establish reproduction.
Do not select seeds after seeing results. Keep pilot analyses separate.

## Metrics and uncertainty

Report the estimate, absolute error, and plug-in Monte Carlo standard error
`4 * sqrt(p_hat * (1 - p_hat) / n)`. This is uncertainty from simulation, not a
guarantee on the observed error. No hypothesis test or significance claim is made.

## Analysis plan and stopping conditions

Run the fixed sample count once. Generate the convergence figure, numeric macros,
and results table from the recorded JSON output. Preserve unsuccessful runs.
Stop on command failure, a changed input checksum, or budget exhaustion.

## Reproduction tolerances

Compare all numeric outputs using absolute tolerance 1e-10 and relative tolerance
1e-8. These tolerances are set before verification. Exact counts and seeds must
match. Paper PDF bytes may differ due to typesetting metadata.

## Budgets

Local CPU only. Each experiment: 120 seconds. Each worker: 600 seconds.
Full reproduction, including initial toolchain download: 600 seconds.
At most 20 worker calls and 2 attempts per job; retained run storage 200 MB.
The storage limit excludes the shared TeX cache and downloaded toolchain.

## Limitations and failure interpretation

The fixture establishes that the harness can reproduce a known computation.
It provides no scientific novelty. A noisy estimate or null result is reportable;
an incomplete run or missing evidence is not verification.

## Approval and amendments

The owner must explicitly approve the protocol using the research CLI before
the harness runs experiments. Changes invalidate approval; record reasons and
effects in `protocol/amendments/` and request approval again. Direct standalone
reproduction commands are intended for already released studies and do not
constitute protocol approval.
