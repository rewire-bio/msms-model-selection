.PHONY: smoke reproduce analysis paper paper-imported test data

data:
	uv run --frozen python scripts/data.py --fetch

test:
	uv run --frozen python -m unittest discover -s tests -v

smoke: data test
	uv run --frozen python scripts/experiment.py --config configs/smoke.json --output results/smoke

reproduce: data test
	uv run --frozen python scripts/experiment.py --config configs/full.json --output results/full
	$(MAKE) analysis paper

analysis:
	uv run --frozen python scripts/analyse.py --results results/full/results.json

paper:
	uv run --frozen python scripts/build_paper.py

# Imported-evidence manuscript: formats archived historical results and compiles with local TeX Live.
# No experiment, data fetch or uv environment creation. Compiling is not scientific verification.
paper-imported:
	python3 scripts/build_paper.py
