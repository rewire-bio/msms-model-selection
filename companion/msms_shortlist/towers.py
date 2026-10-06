"""Inference-only copy of the MSAlign alignment towers.

Adapted from MSAlign (https://github.com/KrzakalaPaul/MSAlign-NeurIPS2026,
commit c2ef425b6874, files models/MSAlign/{model,modules,encoders}.py),
Copyright (c) 2026 KrzakalaPaul, MIT License. Training code, Lightning and the
loss are removed; module names and arithmetic are unchanged so that released
state dicts load with strict=True.
"""

from __future__ import annotations

import torch
from torch import nn


class MLP(nn.Module):
    def __init__(self, d_in, d_hidden, d_out, n_hidden_layers, dropout):
        super().__init__()
        layers, width = [], d_in
        for _ in range(n_hidden_layers):
            layers.extend((nn.Linear(width, d_hidden), nn.LayerNorm(d_hidden), nn.GELU(), nn.Dropout(dropout)))
            width = d_hidden
        layers.append(nn.Linear(width, d_out))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


class CollisionEnergyEncoder(nn.Module):
    def __init__(self, d_out):
        super().__init__()
        positions = torch.arange(0, d_out, 2, dtype=torch.float32)
        self.register_buffer("frequencies", 10_000.0 ** (positions / d_out))
        self.missing = nn.Parameter(torch.empty(d_out))

    def forward(self, energy):
        missing = torch.isnan(energy)
        angles = energy.nan_to_num().unsqueeze(-1) / 100.0 / self.frequencies
        encoded = torch.stack((angles.sin(), angles.cos()), dim=-1).flatten(-2)
        return torch.where(missing.unsqueeze(-1), self.missing, encoded)


class AdductEncoder(nn.Module):
    def __init__(self, n_adducts, d_out, unknown_index, adduct_signs):
        super().__init__()
        self.category = nn.Embedding(n_adducts, d_out // 2)
        self.sign = nn.Embedding(3, d_out // 2)
        signs = torch.as_tensor(adduct_signs)
        self.register_buffer("sign_indices", torch.where(signs == 0, 2, (signs + 1) // 2).long())
        self.unknown_index = int(unknown_index)

    def forward(self, adduct):
        return torch.cat((self.category(adduct), self.sign(self.sign_indices[adduct])), dim=-1)


class AlignmentTowers(nn.Module):
    def __init__(self, config, dims):
        super().__init__()
        m = config["model"]
        d_shared, d_hidden, d_meta = int(m["d_shared"]), int(m["d_hidden"]), int(m["d_metadata"])
        dropout = float(m["dropout"])
        use_energy = bool(m.get("use_collision_energy", True))
        use_adduct = bool(m.get("use_adduct", True))
        n_meta = int(use_energy) + int(use_adduct)
        part = d_meta // n_meta if n_meta else 0
        self.ms_pre = MLP(int(dims["d_ms"]), d_hidden, d_shared, int(m["n_hidden_layers_ms_pre"]), dropout)
        self.energy_encoder = CollisionEnergyEncoder(part) if use_energy else None
        self.adduct_encoder = (AdductEncoder(int(dims["n_adducts"]), part, int(dims["unknown_adduct_index"]),
                                             dims["adduct_signs"]) if use_adduct else None)
        self.ms_post = MLP(d_shared + (d_meta if n_meta else 0), d_hidden, d_shared,
                           int(m["n_hidden_layers_ms_post"]), dropout)
        self.mol = MLP(int(dims["d_mol"]), d_hidden, d_shared, int(m["n_hidden_layers_mol"]), dropout)
        self.log_temperature = nn.Parameter(torch.tensor(0.0))

    def encode_spectrum(self, spectrum, metadata):
        x = self.ms_pre(spectrum.float())
        parts = []
        if self.energy_encoder is not None:
            parts.append(self.energy_encoder(metadata["collision_energy"]))
        if self.adduct_encoder is not None:
            parts.append(self.adduct_encoder(metadata["adduct"]))
        if parts:
            x = torch.cat((x, *parts), dim=-1)
        return self.ms_post(x)

    def encode_molecule(self, molecule):
        return self.mol(molecule.float())


def build_model(bundle: dict) -> AlignmentTowers:
    model = AlignmentTowers(bundle["config"], bundle["input_dimensions"])
    model.load_state_dict({k: v.float() for k, v in bundle["state_dict"].items()}, strict=True)
    return model.eval().requires_grad_(False)


def export_bundle(lightning_checkpoint: str, out_path: str, half: bool = True) -> dict:
    """Strip optimiser state from a released-code checkpoint for distribution."""
    payload = torch.load(lightning_checkpoint, map_location="cpu", weights_only=False)
    hp = payload["hyper_parameters"]
    state = {k: (v.half() if half and v.is_floating_point() else v) for k, v in payload["state_dict"].items()}
    bundle = {"config": hp["config"], "input_dimensions": hp["input_dimensions"], "state_dict": state,
              "source_checkpoint_global_step": payload.get("global_step"),
              "dtype": "float16" if half else "float32"}
    torch.save(bundle, out_path)
    return bundle
