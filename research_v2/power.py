from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm


def effective_sample_size(n: int, *, mean_cluster_size: float = 1.0, icc: float = 0.0) -> float:
    if n < 1:
        raise ValueError("n must be >= 1")
    if mean_cluster_size < 1:
        raise ValueError("mean_cluster_size must be >= 1")
    if not 0 <= icc < 1:
        raise ValueError("icc must be in [0, 1)")
    design_effect = 1 + (mean_cluster_size - 1) * icc
    return float(n / design_effect)


def mde_two_proportion(
    n_fvg: int,
    n_control: int,
    *,
    baseline: float,
    alpha: float = 0.05,
    power: float = 0.80,
    design_effect: float = 1.0,
) -> float:
    """Approximate two-sided minimum detectable probability difference in percentage points."""
    if not 0 < baseline < 1:
        raise ValueError("baseline must be in (0, 1)")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be in (0, 1)")
    if n_fvg < 2 or n_control < 2 or design_effect < 1:
        raise ValueError("sample sizes must be >=2 and design_effect >=1")
    n1 = n_fvg / design_effect
    n2 = n_control / design_effect
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    se = math.sqrt(baseline * (1 - baseline) * (1 / n1 + 1 / n2))
    return float((z_alpha + z_power) * se * 100)


def detectable_r_mean(
    n: int,
    *,
    std_r: float = 1.0,
    alpha: float = 0.05,
    power: float = 0.80,
    design_effect: float = 1.0,
) -> float:
    if n < 2 or std_r <= 0 or design_effect < 1:
        raise ValueError("invalid sample-size/std/design-effect combination")
    effective_n = n / design_effect
    z = norm.ppf(1 - alpha / 2) + norm.ppf(power)
    return float(z * std_r / math.sqrt(effective_n))


def power_scenarios(
    sample_sizes: list[int],
    *,
    baseline: float,
    control_ratio: float = 1.0,
    design_effects: tuple[float, ...] = (1.0, 1.5, 2.0),
) -> pd.DataFrame:
    rows = []
    for n in sample_sizes:
        for deff in design_effects:
            control_n = max(2, int(round(n * control_ratio)))
            rows.append({
                "FVG N": int(n),
                "Control N": control_n,
                "Design effect": deff,
                "80% MDE (pp)": mde_two_proportion(
                    n,
                    control_n,
                    baseline=baseline,
                    power=0.80,
                    design_effect=deff,
                ),
                "90% MDE (pp)": mde_two_proportion(
                    n,
                    control_n,
                    baseline=baseline,
                    power=0.90,
                    design_effect=deff,
                ),
            })
    return pd.DataFrame(rows)
