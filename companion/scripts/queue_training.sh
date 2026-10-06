#!/bin/bash
# Sequential full training queue for protocol section 4 (one heavy job at a time).
# Usage: queue_training.sh <workspace-runs-dir>
# Each run writes an immutable directory runs/T0x-<name>-<UTC>/ with log.txt,
# /usr/bin/time resource lines, and (for model_zoo runs) the released result JSON.
set -u
RUNS="$1"
SRC="$RUNS/external/msalign-src"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
export OMP_NUM_THREADS=4

stamp() { date -u +%Y%m%dT%H%M%SZ; }

# T01: MSAlign released code, DreaMS + Morgan pair, released formula config, 30k steps.
RD="$RUNS/T01-msalign-dreams-morgan-formula1-$(stamp)"; mkdir -p "$RD"
( cd "$SRC" && echo "start $(date -u +%FT%TZ)" && \
  /usr/bin/time -l .venv/bin/python "$SCRIPTS/train_msalign_variant.py" --config massspecgym_formula \
    --split formula_seed1 --spectrum dreams --molecule morgan_2_4096 --max-steps 30000 \
    --seed 42 --workers 3 --out "$RD/checkpoints/dreams_morgan_formula_seed1.ckpt"; \
  echo "exit $? end $(date -u +%FT%TZ)" ) > "$RD/log.txt" 2>&1

# T02: Emb-Cos released config (16k steps); released script also runs its own test evaluation.
RD="$RUNS/T02-embcos-formula1-$(stamp)"; mkdir -p "$RD"
( cd "$SRC" && echo "start $(date -u +%FT%TZ)" && \
  /usr/bin/time -l .venv/bin/python -m model_zoo.train embcos --dataset massspecgym \
    --candidate-map official_candidates_by_mass --split formula_seed1 --workers 3 --no-logger \
    --wandb-run-name embcos_formula_seed1 --result-path "$RD/released-result.json"; \
  echo "exit $? end $(date -u +%FT%TZ)"; \
  mv checkpoints/paper_competitors/embcos_formula_seed1 "$RD/checkpoints" ) > "$RD/log.txt" 2>&1

# T03: DeepSets + Fourier features released config (50 epochs).
RD="$RUNS/T03-deepsets-formula1-$(stamp)"; mkdir -p "$RD"
( cd "$SRC" && echo "start $(date -u +%FT%TZ)" && \
  /usr/bin/time -l .venv/bin/python -m model_zoo.train deepsets --dataset massspecgym \
    --candidate-map official_candidates_by_mass --split formula_seed1 --workers 3 --no-logger \
    --wandb-run-name deepsets_formula_seed1 --result-path "$RD/released-result.json"; \
  echo "exit $? end $(date -u +%FT%TZ)"; \
  mv checkpoints/paper_competitors/deepsets_formula_seed1 "$RD/checkpoints" ) > "$RD/log.txt" 2>&1
echo "queue finished $(date -u +%FT%TZ)" > "$RUNS/queue-finished.txt"
