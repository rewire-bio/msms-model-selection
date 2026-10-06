#!/bin/bash
# Sequential training; each invocation preserves a unique queue directory and status.
set -u
set -o pipefail
fail() { echo "queue_training: $*" >&2; exit 2; }
[ "$#" -eq 1 ] || fail "usage: queue_training.sh <workspace-runs-dir>"
[ -d "$1" ] || fail "missing runs directory / MSAlign checkout: $1/external/msalign-src"
RUNS="$(cd "$1" && pwd -P)" || fail "cannot resolve runs directory"
# Retire legacy global success markers without deleting historical evidence.
if [ -e "$RUNS/queue-finished.txt" ]; then
  LEGACY="$(mktemp -d "$RUNS/legacy-queue.XXXXXX")" || fail "cannot preserve old status"
  mv "$RUNS/queue-finished.txt" "$LEGACY/queue-finished.txt" || fail "cannot retire old status"
fi
SRC="$RUNS/external/msalign-src"
SCRIPTS="$(cd "$(dirname "$0")" && pwd -P)" || fail "cannot locate scripts"
[ -d "$SRC" ] || fail "missing MSAlign checkout: $SRC"
[ -x "$SRC/.venv/bin/python" ] || fail "missing MSAlign venv interpreter: $SRC/.venv/bin/python"
[ -f "$SCRIPTS/train_msalign_variant.py" ] || fail "missing training script"
for name in embcos_formula_seed1 deepsets_formula_seed1; do
  target="$SRC/checkpoints/paper_competitors/$name"
  [ ! -e "$target" ] && [ ! -L "$target" ] || fail "existing checkpoints must be preserved elsewhere before training: $target"
done
# Prevent simultaneous invocations from sharing model_zoo output paths.
LOCK="$RUNS/.queue-training.lock"
mkdir "$LOCK" 2>/dev/null || fail "queue lock exists: $LOCK; confirm no queue is running before removing it"
trap 'rmdir "$LOCK"' EXIT
QUEUE="$(mktemp -d "$RUNS/queue-$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")" || fail "cannot create queue directory"
echo "queue records: $QUEUE"
export OMP_NUM_THREADS=4
if /usr/bin/time -l true >/dev/null 2>&1; then
  TIME_CMD=(/usr/bin/time -l)
elif /usr/bin/time -v true >/dev/null 2>&1; then
  TIME_CMD=(/usr/bin/time -v)
else
  TIME_CMD=()
fi
ANY_FAILED=0
record() {
  printf '%s: %s\n' "$1" "$2" >> "$QUEUE/queue-summary.txt" || fail "cannot write queue summary"
  [ "$2" = ok ] || ANY_FAILED=1
}
run_command() {
  local rd="$1"; shift
  (
    cd "$SRC" || exit 2
    "${TIME_CMD[@]}" .venv/bin/python "$@"
    code=$?
    printf '%s\n' "$code" > "$rd/exit-code.txt" || exit 2
    exit "$code"
  ) > "$rd/log.txt" 2>&1
}
RD="$QUEUE/T01-msalign-dreams-morgan-formula1"
mkdir -p "$RD/checkpoints" || fail "cannot create T01 directory"
CKPT="$RD/checkpoints/dreams_morgan_formula_seed1.ckpt"
if run_command "$RD" "$SCRIPTS/train_msalign_variant.py" --config massspecgym_formula \
  --split formula_seed1 --spectrum dreams --molecule morgan_2_4096 --max-steps 30000 \
  --seed 42 --workers 3 --out "$CKPT"; then
  if [ -s "$CKPT" ]; then record T01 ok; else record T01 'failed: no nonempty checkpoint'; fi
else
  record T01 'failed: training subprocess (see log and exit-code.txt)'
fi
run_model() {
  local job="$1" method="$2" name="$3"
  local rd="$QUEUE/$job" checkpoint="$SRC/checkpoints/paper_competitors/$name"
  mkdir "$rd" || fail "cannot create $job directory"
  if ! run_command "$rd" -m model_zoo.train "$method" --dataset massspecgym \
    --candidate-map official_candidates_by_mass --split formula_seed1 --workers 3 --no-logger \
    --wandb-run-name "$name" --result-path "$rd/released-result.json"; then
    record "$job" 'failed: training subprocess (see log and exit-code.txt)'; return
  fi
  # Validate JSON and a nonempty checkpoint file before promoting any output.
  if ! "$SRC/.venv/bin/python" -c 'import json,pathlib,sys; value=json.load(open(sys.argv[1])); assert isinstance(value,dict) and value; assert any(p.is_file() and p.stat().st_size for p in pathlib.Path(sys.argv[2]).rglob("*.ckpt"))' \
    "$rd/released-result.json" "$checkpoint" >> "$rd/log.txt" 2>&1; then
    record "$job" 'failed: missing or invalid result/checkpoint'; return
  fi
  if ! mv "$checkpoint" "$rd/checkpoints"; then
    record "$job" 'failed: checkpoint promotion'; return
  fi
  record "$job" ok
}
run_model T02-embcos embcos embcos_formula_seed1
run_model T03-deepsets deepsets deepsets_formula_seed1
if [ "$ANY_FAILED" -ne 0 ]; then
  echo "queue failed; see $QUEUE/queue-summary.txt" >&2
  exit 1
fi
printf 'queue finished %s\n' "$(date -u +%FT%TZ)" > "$QUEUE/queue-finished.txt" || fail "cannot write success marker"
