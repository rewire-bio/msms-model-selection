"""Chemistry helpers shared by the benchmark scripts and the own-input CLI.

Identity convention: 2D structure. A molecule is represented by its RDKit
canonical SMILES without stereochemistry, which is the normalisation used by
the MSAlign release. Stereoisomers therefore share one identity.
"""

from __future__ import annotations

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Descriptors import ExactMolWt

RDLogger.DisableLog("rdApp.*")

# Neutral mass = (precursor m/z * |charge|) - ADDUCT_SHIFT. Shifts are the
# ion-minus-neutral masses used by MSAlign (`ion_to_mass`) for the two
# MassSpecGym adducts, plus three common additions for user data.
ADDUCTS = {
    "[M+H]+": {"charge": 1, "shift": 1.007276452},
    "[M+Na]+": {"charge": 1, "shift": 22.9892207},
    "[M+NH4]+": {"charge": 1, "shift": 18.033823},
    "[M+K]+": {"charge": 1, "shift": 38.963158},
    "[M-H]-": {"charge": -1, "shift": -1.007276452},
}

FP_BITS = 4096
FP_RADIUS = 2
_GENERATOR = None


def canonical_2d(smiles: str) -> str | None:
    """RDKit canonical SMILES without stereochemistry, or None if invalid."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=False)


def exact_mass(smiles: str) -> float:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse {smiles!r}")
    return float(ExactMolWt(mol))


def inchikey_block1(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    key = Chem.MolToInchiKey(mol)
    return key.split("-")[0] if key else None


def morgan_packed(smiles: str) -> np.ndarray:
    """Packed 4096-bit radius-2 Morgan fingerprint, little bit order.

    Identical to MSAlign's `morgan_2_4096` cache (no chirality, no features).
    """
    global _GENERATOR
    if _GENERATOR is None:
        _GENERATOR = rdFingerprintGenerator.GetMorganGenerator(
            radius=FP_RADIUS, fpSize=FP_BITS, includeChirality=False)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse {smiles!r}")
    bits = np.zeros(FP_BITS, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(_GENERATOR.GetFingerprint(mol), bits)
    return np.packbits(bits, bitorder="little")


def unpack(packed: np.ndarray) -> np.ndarray:
    return np.unpackbits(packed, axis=-1, count=FP_BITS, bitorder="little")


def neutral_mass(precursor_mz: float, adduct: str, charge: int | None = None) -> float:
    """Neutral monoisotopic mass implied by a precursor ion.

    Raises ValueError when the adduct is unknown or the charge disagrees with it.
    """
    if adduct not in ADDUCTS:
        raise ValueError(f"unsupported adduct {adduct!r}; supported: {sorted(ADDUCTS)}")
    spec = ADDUCTS[adduct]
    if charge is not None and int(charge) != spec["charge"]:
        raise ValueError(f"charge {charge} is inconsistent with adduct {adduct}")
    if not np.isfinite(precursor_mz) or precursor_mz <= 0:
        raise ValueError("precursor m/z must be a positive number")
    return float(precursor_mz) * abs(spec["charge"]) - spec["shift"]


def ppm_error(estimated: float | np.ndarray, candidate: float | np.ndarray) -> np.ndarray:
    candidate = np.asarray(candidate, dtype=np.float64)
    return 1e6 * (np.asarray(estimated, dtype=np.float64) - candidate) / candidate
