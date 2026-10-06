"""Train one released MSAlign representation pair with explicit, recorded overrides.

Run from the MSAlign source checkout (commit c2ef425b6874) so that its relative
``data/`` paths resolve. The released ``train_msalign.py`` only accepts its three
named configurations; this wrapper loads one of them, applies the declared
overrides (representation pair, step budget, seed, output path) and calls the
released ``train_MSAlign`` unchanged.

Example::

    python train_msalign_variant.py --config massspecgym_formula \
        --split formula_seed1 --spectrum dreams --molecule morgan_2_4096 \
        --max-steps 30000 --seed 42 --out /path/to/run/checkpoints/model.ckpt
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from argparse import Namespace
from pathlib import Path

import torch
import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True,
                        choices=("massspecgym_formula", "massspecgym_mces"))
    parser.add_argument("--split", required=True)
    parser.add_argument("--spectrum", required=True, choices=("dreams", "bins"))
    parser.add_argument("--molecule", required=True, choices=("morgan_2_4096",))
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--warmup-steps", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--accelerator", default="mps")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--val-every-steps", type=int,
                        help="validate every N training steps instead of every epoch")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(Path.cwd()))
    from models.MSAlign import main as msalign_main  # released code
    from models.MSAlign.main import train_MSAlign

    config = yaml.safe_load(
        (Path("models/MSAlign/configs") / f"{args.config}.yaml").read_text())
    overrides = {
        "representations.spectrum": args.spectrum,
        "representations.molecule": args.molecule,
        "training.n_max_steps": args.max_steps,
        "training.accelerator": args.accelerator,
        "seed": args.seed,
    }
    config["representations"] = {"spectrum": args.spectrum, "molecule": args.molecule}
    config["training"]["n_max_steps"] = args.max_steps
    config["training"]["accelerator"] = args.accelerator
    if args.warmup_steps is not None:
        config["training"]["n_warmup_steps"] = args.warmup_steps
        overrides["training.n_warmup_steps"] = args.warmup_steps
    config["seed"] = args.seed

    if args.val_every_steps:
        # Released Trainer validates once per epoch; expose a step interval for
        # short smoke runs only. The full runs keep the released behaviour.
        original_trainer = msalign_main.Trainer

        def trainer_with_interval(*a, **kw):
            kw["val_check_interval"] = args.val_every_steps
            kw["check_val_every_n_epoch"] = None
            return original_trainer(*a, **kw)

        msalign_main.Trainer = trainer_with_interval
        overrides["trainer.val_check_interval"] = args.val_every_steps

    args.out.parent.mkdir(parents=True, exist_ok=True)
    run_args = Namespace(
        labelled_dataset_name="massspecgym",
        candidate_map_name="official_candidates_by_mass",
        split_method=args.split,
        n_workers=args.workers,
        batch_size_test=16,
        wandb_project=None,
        wandb_run_name=None,
        no_logger=True,
        output_checkpoint=str(args.out),
    )
    receipt = {
        "script": Path(__file__).name,
        "config_name": args.config,
        "overrides": overrides,
        "effective_config": config,
        "split": args.split,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "machine": platform.machine(),
        "mps_available": torch.backends.mps.is_available(),
        "threads": torch.get_num_threads(),
        "started_unix": time.time(),
    }
    start = time.perf_counter()
    best = train_MSAlign(run_args, config)
    receipt["wall_seconds"] = time.perf_counter() - start
    receipt["best_checkpoint"] = str(best)
    receipt["finished_unix"] = time.time()
    (args.out.parent / "train-receipt.json").write_text(json.dumps(receipt, indent=2, default=str))
    print(json.dumps({k: receipt[k] for k in ("wall_seconds", "best_checkpoint")}))


if __name__ == "__main__":
    main()
