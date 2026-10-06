.PHONY: verify smoke reproduce analysis paper paper-imported test data

# Use the companion lockfile for the scientific Python dependencies needed by tests.
PYTHON = uv run --project companion --frozen python

data:
	$(PYTHON) scripts/reanalyse.py --output results/input-validation --validate-only

test:
	$(PYTHON) -m unittest discover -s tests -v

verify: test
	$(PYTHON) scripts/verify.py

smoke reproduce:
	@echo "Scientific reproduction unavailable: complete the MS/MS harness migration and approve its protocol first. Run make verify for historical evidence and regression checks." >&2
	@exit 2

analysis:
	$(PYTHON) scripts/analyse.py --results results/full/results.json

paper paper-imported:
	python3 scripts/build_paper.py

.PHONY: corrected-analysis
corrected-analysis:
	$(PYTHON) scripts/reanalyse.py --config configs/corrected-analysis.json --output results/corrected-analysis

.PHONY: reproduce-corrected
reproduce-corrected:
	$(PYTHON) scripts/reproduce_corrected.py
