---
title: "Choosing a Model to Rank Molecules from MS/MS Spectra"
date: '2026-10-05T09:00:00Z'
excerpt: >-
  If you can confirm five candidate structures for an MS/MS spectrum, which method should pick them? On 10,648
  MassSpecGym test spectra, two trained alignment models put the true structure in the top five about 6 times in 10,
  against fewer than 1 in 7 for precursor mass error. Their top scores were only a weak signal that the answer was missing.
tags:
  - metabolomics
  - mass-spectrometry
  - benchmarks
  - machine-learning
seoTitle: "Formula-Free MS/MS Ranking for a Five-Structure Shortlist"
citationStatus: verified
references: {}
faqs:
  - question: "Which formula-free method should produce a five-structure shortlist from one MS/MS spectrum?"
    answer: "On this benchmark, a trained alignment model. Emb-Cos put the true structure in the top five for 63.2% of test spectra and DreaMS + Morgan for 61.4%, against 31.3% for a fingerprint predictor and 13.3% for ranking by precursor mass error. The two alignment models were not separated. Use DreaMS + Morgan if you run the companion tool as shipped, or the cheaper Emb-Cos recipe if you train your own. The numbers come from one split of MassSpecGym (formula split seed 1) and one training run per model."
  - question: "Is ranking candidates by precursor mass error good enough on its own?"
    answer: "No. Many candidates are isomers with exactly the target's mass, so mass cannot separate them, and it reached 13.3% in the top five. A post hoc analysis found that about half of its hits came from the 21% of test spectra whose recorded precursor values look recomputed from the known structure. Use mass to build the candidate list, not to rank it."
  - question: "Does a high alignment score mean the top structure is correct?"
    answer: "No. The score measures similarity, and shortlisted structures still require experimental confirmation. In a stress test where the true structure was removed from each list, a threshold fitted on validation data to allow at most 10% false shortlists gave DreaMS + Morgan shortlists for 21.3% of lists that held the answer and still for 13.2% of lists that did not. Confirm any candidate against an authentic standard."
  - question: "How does the size of my candidate list change the expected hit rate?"
    answer: "Longer lists give fewer hits. DreaMS + Morgan put the true structure in the top five for 94.5% of spectra with 16 candidates, 61.4% with a median of 252 and 41.3% with a median of 449. Emb-Cos fell from 93.8% to 63.2% and 45.9%. Quote your own list size next to any expected hit rate."
  - question: "How do I run the shortlist tool on my own spectra?"
    answer: "The companion code in the study repository has a command-line tool. Give it an MGF file with PEPMASS, CHARGE and ADDUCT in every spectrum and a CSV of candidate structures fixed before you look at any scores. It ranks by mass error alone, or with the trained DreaMS + Morgan model if you also download the model and the DreaMS weights. It refuses spectra with missing or inconsistent metadata and reports when no candidate lies inside the mass window."
  - question: "What should I do when the tool declines or finds no candidate in the window?"
    answer: "A decline means the top score fell below 0.599, the threshold fitted on validation data. On this benchmark that threshold also declined about four in five lists that did hold the answer, so treat a decline as a prompt to recheck, not as proof that the answer is absent; the ranked list is still written. If no candidate lies in the window, recheck the precursor value, adduct and charge before widening the window."
  - question: "How do these results relate to the numbers in the MSAlign paper?"
    answer: "They answer a narrower question. MSAlign v2 reports averages over three data splits, and its best standalone model, DreaMS + MolDeBERTa, was not run here because no trained weights were released. Retrained on one of those splits and scored with the released code's rule, DreaMS + Morgan reached 32.6% top-1 recall, just below a band of two standard deviations around the paper's mean for the same model pair, 33.0 to 44.2%. This comparison covers only one split."
---
Suppose a mass spectrometer has given you a spectrum from an unknown small molecule, and a database search has returned 250 candidate structures with the right mass. You can afford to buy and test five of them as reference standards. Which method should choose those five, and how far should you trust its choice?

On one large public benchmark, a trained alignment model picked a five-structure shortlist that held the true structure about 6 times in 10. Ranking by mass alone did so fewer than 1 time in 7. The full methods, tables and code are in the [study repository](https://github.com/rewire-bio/msms-model-selection), with the [historical detailed article](https://github.com/rewire-bio/msms-model-selection/blob/main/article/original.md) and the [completed paper (PDF)](https://github.com/rewire-bio/msms-model-selection/blob/main/paper/build/main.pdf).

*Correction, 6 October 2026: the exploratory fusion method originally kept score normalizations from the full candidate list when the answer was removed or the list size changed. The corrected analysis recomputes them for the candidates actually available. The main comparison, all single-model results and the recommendation are unchanged. Figures 2 and 3 now use the corrected fusion results. This was a reanalysis of saved scores, not a new training run. [Correction results](https://github.com/rewire-bio/msms-model-selection/tree/main/evidence/corrected-analysis/20261006).*

## What an MS/MS spectrum gives you

A tandem mass spectrometer (MS/MS) selects ions of one mass, breaks them apart and records the masses of the fragments. The selected ion's mass-to-charge ratio is the **precursor m/z**. Together with the adduct (the ion form, such as the molecule plus a proton, [M+H]+) and the charge, it gives the molecule's neutral mass. Every structure whose exact mass lies within a small tolerance of that mass, here 10 parts per million (ppm), joins the candidate list.

Mass alone cannot finish the job. Many candidates are isomers, with the same atoms and therefore the same mass: in this benchmark's validation lists, 32.6% of the distinct wrong candidates had exactly the true structure's mass. The fragments carry the structural information. A **shortlist** contains the few top-ranked candidates you will confirm in the lab.

"Formula-free" means the ranking method is not told the molecular formula. It sees only the peaks, precursor m/z, adduct, charge and candidate list. The measure used here is **Recall@5**: the share of spectra whose true structure lands in the top five.

The data are [MassSpecGym](https://arxiv.org/abs/2410.23326), formula split seed 1, as processed by the [MSAlign](https://arxiv.org/abs/2605.19752v2) authors: 10,648 test spectra from 1,421 molecules, [M+H]+ and [M+Na]+ only. Two structures that differ only in stereochemistry counted as the same answer. After repeated structures were removed, each list held a median of 252 candidates, and the true structure was always in the list.

## The main result: about 6 in 10 against fewer than 1 in 7

Five methods were compared, plus random ordering:

- **Precursor mass error**: rank by how close each candidate's mass is to the measured precursor.
- **DeepSets fingerprint predictor**: predict a [Morgan fingerprint](https://doi.org/10.1021/ci100050t), a list of the small substructures in a molecule, from the peaks, then rank candidates by similarity to it.
- **Alignment models**: train one network for spectra and one for structures so that a spectrum lands close to its true structure in a shared space, then rank by that closeness (cosine similarity). **Emb-Cos**, named by [De Waele et al.](https://arxiv.org/abs/2602.16507), reads the peaks grouped into fixed-width mass bins. **DreaMS + Morgan**, from the MSAlign code, reads a [DreaMS](https://doi.org/10.1038/s41587-025-02663-3) embedding, a numerical summary of the spectrum from a model pre-trained on millions of unlabelled spectra. Both read each candidate structure as a Morgan fingerprint.
- **Alignment + mass fusion**: a weighted sum of the DreaMS + Morgan score and the mass-error score, with the weight chosen on validation data (spectra kept apart from both training and the test set). It is exploratory and not a recommendation.

Each learned model was retrained once with the code and settings released by the MSAlign authors, under a protocol fixed before any test score existed. Emb-Cos reached 63.2% Recall@5 [95% interval 58.4 to 67.5] and DreaMS + Morgan 61.4% [56.2 to 66.3]. The fingerprint predictor reached 31.3%, mass error 13.3% and random ordering 2.1%.

![Dot plot of Recall at 1, 5 and 20 for five methods with 95% bootstrap intervals and dashed random baselines](/images/an-msms-shortlist-is-not-an-identification/01-recall-by-method.png)

*Figure 1. Share of the 10,648 test spectra with the true structure in the top 1, 5 or 20 candidates. Read the middle panel: five is the confirmation budget. Bars are 95% intervals from resampling the 1,421 test molecules; dashed lines show random ordering. "Alignment + mass fusion" is an exploratory combination, not a recommendation. Source: [study repository](https://github.com/rewire-bio/msms-model-selection).*

Are the two alignment models different? The data cannot tell. DreaMS + Morgan minus Emb-Cos was −1.85 percentage points [−5.19 to +1.35]. In plain terms, the data fit anything from DreaMS + Morgan finding about 5 fewer true structures per 100 spectra than Emb-Cos to finding about 1 more. That interval includes zero, so the result is inconclusive, not a demonstration that the two are equal. By contrast, DreaMS + Morgan beat mass error by 48.0 points [42.2 to 53.6].

Emb-Cos trained in 3.0 hours and DreaMS + Morgan in 7.75 hours on one Apple M4 machine, with different step budgets. The companion tool ships a trained DreaMS + Morgan model. If you use the tool as it is, use DreaMS + Morgan. If you train your own model, the cheaper Emb-Cos recipe was not separated from DreaMS + Morgan here, but you would have to score with it yourself and fit its own decline threshold.

## Longer lists mean fewer hits

The benchmark lists are capped at 256 structures. A real database search can return far more. To see the effect, the study shrank the lists to random subsets of 16 and 64, and grew them by adding same-mass structures from MassSpecGym's larger 4M molecule set, to a median of 449.

![Line chart of Recall at 5 against median candidate-pool size for five methods and random ordering, all falling as pools grow from 16 to 449 structures](/images/an-msms-shortlist-is-not-an-identification/02-pool-size-stress.png)

*Figure 2. Recall@5 against the median number of candidates per spectrum, with the true structure always present. Every method falls as the list grows. The two alignment models stay well above the fingerprint predictor and mass error, but swap order between themselves: DreaMS + Morgan is ahead by under one point at 16 candidates and Emb-Cos by 4.6 points at 449; this comparison was not declared in advance. Fusion scores are normalized separately for each available list in the corrected analysis. Source: [corrected results](https://github.com/rewire-bio/msms-model-selection/tree/main/evidence/corrected-analysis/20261006).*

DreaMS + Morgan fell from 94.5% with 16 candidates to 61.4% at 252 and 41.3% at 449. Quote the list size with any hit rate. If your list is much longer than 252, expect less than the headline numbers.

## When to decline a shortlist

Benchmark lists always contain the answer. A real search may not. To test this, each test list was scored twice: intact, and with the true structure removed. This artificial removal is a stress test, not a measured rate of real absence. For fusion, both component scores are normalized again after removing the answer; otherwise the supposedly missing structure still affects the remaining scores.

The tool can decline to nominate when its top score falls below a threshold. The threshold, 0.599, was fitted on validation data to allow at most 10% false shortlists, that is, shortlists for lists missing the answer. On the test data, DreaMS + Morgan then gave a shortlist for 21.3% of lists that held the answer, and 68.4% of those shortlists contained it. It still gave a shortlist for 13.2% of lists without the answer.

![Curves of coverage of target-present queries against false nominations on target-removed queries for five methods, with markers at the validation-fitted thresholds](/images/an-msms-shortlist-is-not-an-identification/04-decline-to-nominate.png)

*Figure 3. Each curve moves the decline threshold from strict to lenient. The vertical axis shows the share of lists holding the answer that still get a shortlist. The horizontal axis shows the share of lists missing the answer that wrongly get one. The dashed diagonal is no better than chance, and a useful signal stays well above it. The alignment models sit only modestly above it, and mass error lies on it. Markers show the threshold fitted on validation data to allow at most 10% false shortlists. The fusion curve and marker use the corrected analysis; the other methods are unchanged. Source: [corrected results](https://github.com/rewire-bio/msms-model-selection/tree/main/evidence/corrected-analysis/20261006).*

For exploratory fusion, the corrected threshold gives shortlists for 17.4% of lists holding the answer, compared with 21.8% in the original analysis. Of those retained shortlists, 88.4% contain the answer. False shortlists for lists without the answer change from 10.2% to 10.4%. Fusion remains exploratory; these corrected values do not change the recommendation to use an alignment model. [Correction results](https://github.com/rewire-bio/msms-model-selection/tree/main/evidence/corrected-analysis/20261006).

You choose between failure modes. The strict threshold declines about four in five lists that do hold the answer. A lenient threshold that keeps 90% of those lists still nominates for 86.6% of lists without it. Either way, the score is not the probability that the top structure is right.

One more check belongs before any ranking. In a post hoc analysis, added after the main results, 21% of test spectra had precursor values within 0.01 ppm of the known structure's exact mass, far closer than instrument accuracy allows, which suggests values recomputed from the structure. Those spectra supplied about half of mass error's hits. Check how many decimals your precursor carries and its ppm error against your candidates before trusting any list.

## Try it: inspect the recorded results

This example reads the corrected analysis tables. It trains nothing, runs no model and downloads no weights. You need only `curl` and Python 3.9 or later. The address is pinned to the correction commit of the study repository.

```bash
mkdir -p msms-results && cd msms-results
BASE=https://raw.githubusercontent.com/rewire-bio/msms-model-selection/8b650adabc3f2cd833acb778dd7dd140d0f0e6f6/evidence/corrected-analysis/20261006/analysis
for f in metrics.csv contrasts.csv abstention.csv; do curl -fsSLO "$BASE/$f"; done
```

Save this as `inspect_results.py` in the same folder:

```python
# Print the recorded MS/MS shortlist results. Reads three CSV files; no training or inference.
import csv

NAMES = {
    "random": "Random ordering",
    "mass": "Precursor mass error",
    "deepsets": "DeepSets fingerprint predictor",
    "embcos": "Emb-Cos",
    "msalign": "DreaMS + Morgan",
    "fusion": "Alignment + mass fusion (exploratory)",
}


def read(name):
    with open(name, newline="") as f:
        return list(csv.DictReader(f))


metrics = read("metrics.csv")

# 1. Main result: Recall@5 on the official pools with repeated structures removed,
#    ties counted at their expected value (the study's primary rule).
print("Recall@5 (%), 10,648 test spectra, pools of median 252 structures")
for r in metrics:
    if (r["pool"], r["rule"], r["k"]) == ("official_dedup", "expected", "5"):
        print(f'  {NAMES[r["method"]]:<38} {float(r["estimate"]):5.1f}'
              f'  [{float(r["ci_low"]):.1f}, {float(r["ci_high"]):.1f}]')

# 2. The three contrasts declared before any test score existed.
print("\nPre-declared paired differences in Recall@5 (points)")
for r in read("contrasts.csv"):
    if r["primary"] == "True":
        print(f'  {r["contrast"]}: {NAMES[r["a"]]} minus {NAMES[r["b"]]}:'
              f' {float(r["estimate"]):+.2f} [{float(r["ci_low"]):+.2f}, {float(r["ci_high"]):+.2f}]')

# 3. Longer candidate lists give fewer hits (median list size before each value).
print("\nRecall@5 (%) as the candidate list grows")
pools = [("sub16", 16), ("sub64", 64), ("official_dedup", 252), ("expanded1024", 449)]
for method in ("msalign", "embcos"):
    values = {r["pool"]: float(r["estimate"]) for r in metrics
              if r["method"] == method and r["rule"] == "expected" and r["k"] == "5"}
    print(f'  {NAMES[method]:<16}' + "".join(f"{size:>5}: {values[p]:4.1f}" for p, size in pools))

# 4. Declining to nominate, with each test pool scored intact and with its answer removed.
r = next(r for r in read("abstention.csv")
         if (r["method"], r["confidence"], r["threshold"]) == ("msalign", "top1", "tau_fn10"))
print(f'\nDreaMS + Morgan, decline threshold {float(r["tau"]):.3f} fitted on validation:')
print(f'  shortlist given when the answer is present: {100 * float(r["coverage_present_estimate"]):.1f}%')
print(f'  shortlist given when the answer was removed: {100 * float(r["false_nomination_absent_estimate"]):.1f}%')
```

Then run `python3 inspect_results.py`. It finishes in under a second and prints:

```text
Recall@5 (%), 10,648 test spectra, pools of median 252 structures
  Precursor mass error                    13.3  [11.2, 15.6]
  DreaMS + Morgan                         61.4  [56.2, 66.3]
  Emb-Cos                                 63.2  [58.4, 67.5]
  DeepSets fingerprint predictor          31.3  [27.2, 35.5]
  Alignment + mass fusion (exploratory)   64.8  [59.6, 69.9]
  Random ordering                          2.1  [2.1, 2.2]

Pre-declared paired differences in Recall@5 (points)
  C1: DreaMS + Morgan minus Precursor mass error: +48.04 [+42.19, +53.59]
  C2: DreaMS + Morgan minus Emb-Cos: -1.85 [-5.19, +1.35]
  C3: DeepSets fingerprint predictor minus Precursor mass error: +18.02 [+13.40, +22.49]

Recall@5 (%) as the candidate list grows
  DreaMS + Morgan    16: 94.5   64: 81.4  252: 61.4  449: 41.3
  Emb-Cos            16: 93.8   64: 80.4  252: 63.2  449: 45.9

DreaMS + Morgan, decline threshold 0.599 fitted on validation:
  shortlist given when the answer is present: 21.3%
  shortlist given when the answer was removed: 13.2%
```

Change the filters to see Recall@1 or other scoring rules. To rank your own spectra, use the command-line tool described in the [companion README](https://github.com/rewire-bio/msms-model-selection/blob/main/companion/README.md); its model run needs the trained model and the 468 MB DreaMS weights.

## Limits

- One split, one training run: the intervals reflect which molecules were sampled, not variation between data splits or retraining. Retrained with the released code and scored by its rules, Emb-Cos fell below a band of two standard deviations around the [MSAlign v2](https://arxiv.org/abs/2605.19752v2) mean at the top 1, 5 and 20, and DreaMS + Morgan fell just below its band at the top 1.
- Strongest published models not run: MSAlign's best models pair DreaMS with the MolDeBERTa molecule model, and their trained checkpoints were not released. Other published methods were not run either.
- Benchmark lists, not real searches: the lists were centred on the known structure's mass, so the answer was always present. About 7% of test spectra lie more than 10 ppm from the known structure, and a real search centred on the measured precursor would miss them.
- Scoring rules matter: ties were counted at their expected value. Repeated structures were removed. Under the released code's rules, which keep repeats and count every tied candidate ahead of the answer, mass error falls from 13.3% to 6.3%.
- Exploratory and post hoc parts: the fusion model, the precursor analysis and the expanded-list comparison were not among the three comparisons declared before testing.
- Experimental confirmation: test the shortlisted candidates against reference standards. The [Metabolomics Standards Initiative](https://doi.org/10.1007/s11306-007-0082-2) asks for two independent, orthogonal measurements against an authentic standard before calling a known compound identified.
- Review and disclosure: the study, companion code and charts come from this site's own project. AI coding agents (Claude Opus) ran the original experiments and drafted the original article, this shorter version and the paper; Codex agents performed the correction and updated the write-ups. All review so far was automated; no human scientist has reviewed the work. The correction reanalysed cached scores from the original training runs. It did not retrain the models or independently reproduce their predictions; that work remains pending.

The [splicing study in this series](/blog/choosing-a-splicing-score-for-a-fixed-minigene-budget/) asks the same question, which score to use for a fixed testing budget, for minigene tests.

## Sources and artifacts

- Study repository with the historical detailed article, current companion code, recorded results and updated paper: [rewire-bio/msms-model-selection](https://github.com/rewire-bio/msms-model-selection) ([original detailed article](https://github.com/rewire-bio/msms-model-selection/blob/main/article/original.md), [paper PDF](https://github.com/rewire-bio/msms-model-selection/blob/main/paper/build/main.pdf)).
- Bushuiev R, Bushuiev A, de Jonge NF, et al. [MassSpecGym: A benchmark for the discovery and identification of molecules](https://arxiv.org/abs/2410.23326). NeurIPS 2024, Datasets and Benchmarks.
- Krzakala P, Melo G, Lançon C, et al. [MSAlign: Aligning Molecule and Mass Spectra representations for Metabolite Identification](https://arxiv.org/abs/2605.19752v2). arXiv:2605.19752v2, 2026.
- Bushuiev R, Bushuiev A, Samusevich R, et al. [Self-supervised learning of molecular representations from millions of tandem mass spectra using DreaMS](https://doi.org/10.1038/s41587-025-02663-3). *Nat Biotechnol* 2026;44(4):630-640.
- De Waele G, Wydmuch M, Dembczyński K, et al. [Small molecule retrieval from tandem mass spectrometry: what are we optimizing for?](https://arxiv.org/abs/2602.16507) arXiv:2602.16507, 2026.
- Rogers D, Hahn M. [Extended-connectivity fingerprints](https://doi.org/10.1021/ci100050t). *J Chem Inf Model* 2010;50(5):742-754.
- Sumner LW, Amberg A, Barrett D, et al. [Proposed minimum reporting standards for chemical analysis](https://doi.org/10.1007/s11306-007-0082-2). *Metabolomics* 2007;3(3):211-221.
- Historical companion code and recorded results as published with the original article (these archives do not include the later fixes): [code](/downloads/an-msms-shortlist-is-not-an-identification/msms-shortlist-companion-code.tar.gz) and [results archive](/downloads/an-msms-shortlist-is-not-an-identification/msms-shortlist-results.tar.gz).
