"""Execute a saved experiment configuration without importing the harness."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from study.monte_carlo import estimate_pi
from data import verify_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config.get("study_kind") != "monte_carlo_pi":
        raise SystemExit("Study is unconfigured. Complete the protocol and implement the experiment first.")
    if config.get("mode") not in ("smoke", "full"):
        raise SystemExit("Configuration mode must be smoke or full")
    verify_data(ROOT / "data/manifest.json", ROOT)
    result = {
        "schema_version": 1, "mode": config["mode"], "study_kind": config["study_kind"],
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "metrics": estimate_pi(config["n"], config["seed"]),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "results.json"
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if destination.exists():
        if destination.read_text() != encoded:
            raise SystemExit("Existing results differ. Preserve them and select a new output directory.")
    else:
        with destination.open("x") as output:
            output.write(encoded)
    print(destination)


if __name__ == "__main__":
    main()
