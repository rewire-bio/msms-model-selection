"""A deterministic pi-estimation fixture with an analytical reference."""
from __future__ import annotations

import math
import random


def inside_quarter_circle(x: float, y: float) -> bool:
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise ValueError("Coordinates must lie in the unit square")
    return x * x + y * y <= 1


def estimate_pi(n: int, seed: int) -> dict:
    if type(n) is not int or not 1 <= n <= 10_000_000:
        raise ValueError("n must be an integer between 1 and 10,000,000")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    generator = random.Random(seed)
    inside = 0
    checkpoints = []
    stride = max(1, n // 20)
    for count in range(1, n + 1):
        inside += inside_quarter_circle(generator.random(), generator.random())
        if count % stride == 0 or count == n:
            checkpoints.append({"n": count, "estimate_pi": 4 * inside / count})
    probability = inside / n
    estimate = 4 * probability
    return {
        "n": n, "seed": seed, "inside": inside,
        "estimate_pi": estimate, "reference_pi": math.pi,
        "absolute_error": abs(estimate - math.pi),
        "standard_error": 4 * math.sqrt(probability * (1 - probability) / n),
        "checkpoints": checkpoints,
    }
