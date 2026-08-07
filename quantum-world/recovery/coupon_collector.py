"""
Coupon Collector Analysis

Classical and quantum coupon collector problem analysis for
sparse quantum support recovery.

Made with Bob
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ..quantum.measurement import MeasurementCounts, QuantumSupport


# =============================================================================
# HARMONIC NUMBER & EULER-MASCHERONI
# =============================================================================

EULER_MASCHERONI = 0.5772156649015329

_HARMONIC_CACHE = [
    0.0,                    # H_0
    1.0,                    # H_1
    1.5,                    # H_2
    1.8333333333333333,     # H_3
    2.083333333333333,      # H_4
    2.283333333333333,      # H_5
    2.4499999999999997,     # H_6
    2.5928571428571425,     # H_7
    2.7178571428571425,     # H_8
    2.8289682539682537,     # H_9
    2.9289682539682538,     # H_10
]


def harmonic_number(n: int) -> float:
    if n < len(_HARMONIC_CACHE):
        return _HARMONIC_CACHE[n]
    return math.log(n) + EULER_MASCHERONI


# =============================================================================
# CORE COUPON COLLECTOR FORMULAS
# =============================================================================

def expected_shots_uniform(atom_count: int) -> float:
    """E[S] = A * H_A"""
    if atom_count <= 0:
        return 0.0
    return atom_count * harmonic_number(atom_count)


def expected_shots_with_confidence(atom_count: int, confidence: float) -> float:
    """S_epsilon ~ A * (ln(A) + ln(1/epsilon))"""
    if atom_count <= 0:
        return 0.0
    if not (0 < confidence < 1):
        raise ValueError("Confidence must be in (0, 1)")
    epsilon = 1.0 - confidence
    return atom_count * (math.log(atom_count) + math.log(1.0 / epsilon))


def expected_shots_with_noise(
    atom_count: int, confidence: float, valid_shot_probability: float
) -> float:
    """S_epsilon,eta ~ (A / eta) * (ln(A) + ln(1/epsilon))"""
    if not (0 < valid_shot_probability <= 1):
        raise ValueError("Valid shot probability must be in (0, 1]")
    base = expected_shots_with_confidence(atom_count, confidence)
    return base / valid_shot_probability


def expected_shots_nonuniform(
    atom_count: int, confidence: float, min_probability: float
) -> float:
    """S >= (ln(A) + ln(1/epsilon)) / p_min"""
    if not (0 < min_probability <= 1):
        raise ValueError("Minimum probability must be in (0, 1]")
    epsilon = 1.0 - confidence
    return (math.log(atom_count) + math.log(1.0 / epsilon)) / min_probability


def estimate_min_probability(
    measurements: MeasurementCounts, support: QuantumSupport
) -> float:
    """Estimate minimum probability from measurement counts."""
    occupied_set = set(support.occupied_indices)
    min_count = float("inf")
    total_valid = 0
    for index, count in measurements.counts.items():
        if index in occupied_set:
            if count < min_count:
                min_count = count
            total_valid += count
    if total_valid == 0:
        return 0.0
    return min_count / measurements.total_shots


def probability_missing_atoms(atom_count: int, shots: int) -> float:
    """P(missing >= 1) ~ A * exp(-S/A) for uniform case."""
    if atom_count <= 0 or shots <= 0:
        return 1.0
    per_atom_miss = math.exp(-shots / atom_count)
    upper_bound = atom_count * per_atom_miss
    return min(1.0, upper_bound)


def probability_complete_recovery(atom_count: int, shots: int) -> float:
    return 1.0 - probability_missing_atoms(atom_count, shots)


def shots_for_target_probability(atom_count: int, target_probability: float) -> float:
    """Invert P(complete) = 1 - A * exp(-S/A). Returns S."""
    if not (0 < target_probability < 1):
        raise ValueError("Target probability must be in (0, 1)")
    miss_probability = 1.0 - target_probability
    if miss_probability >= atom_count:
        return 0.0
    return -atom_count * math.log(miss_probability / atom_count)


# =============================================================================
# RECOVERY PROGRESS ANALYSIS
# =============================================================================

@dataclass
class RecoveryProgress:
    atom_count: int
    unique_atoms_found: int
    total_shots: int
    recall: float

    # Uniform estimates
    expected_shots_uniform: float
    progress_fraction_uniform: float

    # With confidence
    expected_shots_with_confidence: float
    target_confidence: float

    # With noise
    valid_shot_probability: float
    expected_shots_with_noise: float

    # Nonuniform
    min_probability: float
    expected_shots_nonuniform: float

    # Completion probability
    probability_complete: float
    probability_missing: float

    # Recommendations
    recommended_additional_shots: int
    is_likely_complete: bool


def analyze_recovery_progress(
    atom_count: int,
    unique_atoms_found: int,
    total_shots: int,
    valid_shot_probability: float,
    min_probability: float,
    target_confidence: float = 0.99,
) -> RecoveryProgress:
    recall = unique_atoms_found / atom_count if atom_count > 0 else 0.0

    exp_shots_uniform = expected_shots_uniform(atom_count)
    progress_uniform = total_shots / exp_shots_uniform if exp_shots_uniform > 0 else 0.0

    exp_shots_confidence = expected_shots_with_confidence(atom_count, target_confidence)
    exp_shots_noise = expected_shots_with_noise(
        atom_count, target_confidence, valid_shot_probability
    )
    exp_shots_nonuniform = expected_shots_nonuniform(
        atom_count, target_confidence, min_probability
    )

    prob_complete = probability_complete_recovery(atom_count, total_shots)
    prob_missing = probability_missing_atoms(atom_count, total_shots)

    shots_needed = max(exp_shots_confidence, exp_shots_noise, exp_shots_nonuniform)
    recommended_additional = max(0, math.ceil(shots_needed - total_shots))
    is_likely_complete = prob_complete >= target_confidence

    return RecoveryProgress(
        atom_count=atom_count,
        unique_atoms_found=unique_atoms_found,
        total_shots=total_shots,
        recall=recall,
        expected_shots_uniform=exp_shots_uniform,
        progress_fraction_uniform=progress_uniform,
        expected_shots_with_confidence=exp_shots_confidence,
        target_confidence=target_confidence,
        valid_shot_probability=valid_shot_probability,
        expected_shots_with_noise=exp_shots_noise,
        min_probability=min_probability,
        expected_shots_nonuniform=exp_shots_nonuniform,
        probability_complete=prob_complete,
        probability_missing=prob_missing,
        recommended_additional_shots=recommended_additional,
        is_likely_complete=is_likely_complete,
    )


# =============================================================================
# VARIANCE AND CONFIDENCE INTERVALS
# =============================================================================

def variance_shots_uniform(atom_count: int) -> float:
    """Var[S] ~ A^2 * (pi^2/6 - 1)"""
    pi_sq_over_6 = math.pi * math.pi / 6.0
    return atom_count * atom_count * (pi_sq_over_6 - 1.0)


def std_dev_shots_uniform(atom_count: int) -> float:
    return math.sqrt(variance_shots_uniform(atom_count))


def _inverse_erf(x: float) -> float:
    """Abramowitz and Stegun approximation for inverse erf."""
    a = 0.147
    ln_term = math.log(1.0 - x * x)
    b = 2.0 / (math.pi * a) + ln_term / 2.0
    c = ln_term / a
    discriminant = b * b - c
    if discriminant < 0:
        discriminant = 0.0
    sign = -1.0 if x < 0 else 1.0
    return sign * math.sqrt(math.sqrt(discriminant) - b)


def shots_confidence_interval(
    atom_count: int, confidence_level: float = 0.95
) -> Dict:
    """Compute confidence interval for shots required (normal approximation)."""
    mean = expected_shots_uniform(atom_count)
    std_dev = std_dev_shots_uniform(atom_count)

    if confidence_level >= 0.99:
        z_score = 2.576
    elif confidence_level >= 0.95:
        z_score = 1.96
    elif confidence_level >= 0.90:
        z_score = 1.645
    else:
        alpha = 1.0 - confidence_level
        z_score = math.sqrt(2.0) * _inverse_erf(1.0 - alpha)

    return {
        "lower": max(0.0, mean - z_score * std_dev),
        "upper": mean + z_score * std_dev,
        "mean": mean,
        "std_dev": std_dev,
    }


# =============================================================================
# SIMULATION
# =============================================================================

def simulate_coupon_collector(
    atom_count: int,
    max_shots: int,
    rng_func: Callable[[], float],
) -> Dict:
    """Simulate coupon collector process for validation."""
    collected: set = set()
    unique_per_shot: List[int] = []

    for shot in range(max_shots):
        coupon = int(rng_func() * atom_count)
        collected.add(coupon)
        unique_per_shot.append(len(collected))
        if len(collected) == atom_count:
            return {
                "shots_to_complete": shot + 1,
                "unique_per_shot": unique_per_shot,
                "complete": True,
            }

    return {
        "shots_to_complete": max_shots,
        "unique_per_shot": unique_per_shot,
        "complete": False,
    }


def batch_simulate_coupon_collector(
    atom_count: int,
    max_shots: int,
    repetitions: int,
    seed: int,
) -> Dict:
    """Batch simulation for statistical validation."""
    # LCG PRNG for reproducibility (matches TS implementation)
    state = seed

    def _rng() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 0x100000000

    shots_to_complete: List[int] = []
    completed_count = 0

    for _ in range(repetitions):
        result = simulate_coupon_collector(atom_count, max_shots, _rng)
        if result["complete"]:
            shots_to_complete.append(result["shots_to_complete"])
            completed_count += 1

    if shots_to_complete:
        mean = sum(shots_to_complete) / len(shots_to_complete)
        variance = (
            sum((x - mean) ** 2 for x in shots_to_complete) / (len(shots_to_complete) - 1)
            if len(shots_to_complete) > 1
            else 0.0
        )
    else:
        mean = 0.0
        variance = 0.0

    return {
        "mean_shots_to_complete": mean,
        "std_dev_shots_to_complete": math.sqrt(variance),
        "completion_rate": completed_count / repetitions,
        "shots_distribution": shots_to_complete,
        "theoretical_mean": expected_shots_uniform(atom_count),
        "theoretical_std_dev": std_dev_shots_uniform(atom_count),
    }
