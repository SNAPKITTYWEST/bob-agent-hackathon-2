"""
Experiment Metrics Computation

Complete metrics for quantum molecular voxel encoding experiments.

Made with Bob
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..quantum.measurement import (
    MeasurementCounts,
    QuantumSupport,
    compute_snr,
    compute_useful_shot_fraction,
    compute_wasted_shot_fraction,
)
from ..voxel.cartesian_voxelizer import (
    Molecule,
    Vec3,
    VoxelGrid,
    decode_combined_index,
    voxel_center_position,
)


# =============================================================================
# RECOVERED ATOM TYPE
# =============================================================================

@dataclass
class RecoveredAtom:
    logical_index: int
    basis_index: int
    count: int
    posterior_occupied: float  # P(occupied | data)
    confidence: float
    atom_type: str
    type_index: int
    raw_position: Vec3       # voxel center
    refined_position: Optional[Vec3] = None


# =============================================================================
# INDIVIDUAL METRIC FUNCTIONS
# =============================================================================

def compute_recall(recovered_atoms: List[RecoveredAtom], true_atom_count: int) -> float:
    """Recall = unique_atoms_found / total_atoms"""
    if true_atom_count == 0:
        return 0.0
    unique_recovered = len({a.basis_index for a in recovered_atoms})
    return min(1.0, unique_recovered / true_atom_count)


def compute_precision(
    recovered_atoms: List[RecoveredAtom], true_support: QuantumSupport
) -> float:
    """Precision = true_positives / (true_positives + false_positives)"""
    if not recovered_atoms:
        return 0.0
    true_indices = set(true_support.occupied_indices)
    true_positives = sum(1 for a in recovered_atoms if a.basis_index in true_indices)
    return true_positives / len(recovered_atoms)


def compute_f1_score(precision: float, recall: float) -> float:
    """F1 = 2 * (precision * recall) / (precision + recall)"""
    if precision + recall == 0:
        return 0.0
    return (2.0 * precision * recall) / (precision + recall)


def compute_support_iou(
    recovered_atoms: List[RecoveredAtom], true_support: QuantumSupport
) -> float:
    """IoU = |recovered ∩ true| / |recovered ∪ true|"""
    recovered_indices = {a.basis_index for a in recovered_atoms}
    true_indices = set(true_support.occupied_indices)
    intersection = recovered_indices & true_indices
    union = recovered_indices | true_indices
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _find_matching_true_atom(
    recovered: RecoveredAtom, true_molecule: Molecule, grid: VoxelGrid
):
    """Find true atom matching by element type and approximate position."""
    for ta in true_molecule.atoms:
        if ta.element != recovered.atom_type:
            continue
        dx = ta.position.x - recovered.raw_position.x
        dy = ta.position.y - recovered.raw_position.y
        dz = ta.position.z - recovered.raw_position.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 2.0 * grid.voxel_size:
            return ta
    return None


def compute_coordinate_rmsd(
    recovered_atoms: List[RecoveredAtom],
    true_molecule: Molecule,
    grid: VoxelGrid,
) -> float:
    """Coordinate RMSD (angstroms)."""
    if not recovered_atoms:
        return 0.0
    sum_sq = 0.0
    count = 0
    for recovered in recovered_atoms:
        ta = _find_matching_true_atom(recovered, true_molecule, grid)
        if ta is not None:
            pos = recovered.refined_position or recovered.raw_position
            dx = ta.position.x - pos.x
            dy = ta.position.y - pos.y
            dz = ta.position.z - pos.z
            sum_sq += dx * dx + dy * dy + dz * dz
            count += 1
    return math.sqrt(sum_sq / count) if count > 0 else 0.0


def compute_max_coordinate_error(
    recovered_atoms: List[RecoveredAtom],
    true_molecule: Molecule,
    grid: VoxelGrid,
) -> float:
    max_err = 0.0
    for recovered in recovered_atoms:
        ta = _find_matching_true_atom(recovered, true_molecule, grid)
        if ta is not None:
            pos = recovered.refined_position or recovered.raw_position
            dx = ta.position.x - pos.x
            dy = ta.position.y - pos.y
            dz = ta.position.z - pos.z
            err = math.sqrt(dx * dx + dy * dy + dz * dz)
            if err > max_err:
                max_err = err
    return max_err


def compute_mean_coordinate_error(
    recovered_atoms: List[RecoveredAtom],
    true_molecule: Molecule,
    grid: VoxelGrid,
) -> float:
    total_err = 0.0
    count = 0
    for recovered in recovered_atoms:
        # For mean error, match by position only (no element check)
        for ta in true_molecule.atoms:
            dx = ta.position.x - recovered.raw_position.x
            dy = ta.position.y - recovered.raw_position.y
            dz = ta.position.z - recovered.raw_position.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < 2.0 * grid.voxel_size:
                pos = recovered.refined_position or recovered.raw_position
                dx2 = ta.position.x - pos.x
                dy2 = ta.position.y - pos.y
                dz2 = ta.position.z - pos.z
                total_err += math.sqrt(dx2 * dx2 + dy2 * dy2 + dz2 * dz2)
                count += 1
                break
    return total_err / count if count > 0 else 0.0


def compute_atom_type_accuracy(
    recovered_atoms: List[RecoveredAtom],
    true_molecule: Molecule,
    grid: VoxelGrid,
) -> float:
    if not recovered_atoms:
        return 0.0
    correct = 0
    total = 0
    for recovered in recovered_atoms:
        for ta in true_molecule.atoms:
            dx = ta.position.x - recovered.raw_position.x
            dy = ta.position.y - recovered.raw_position.y
            dz = ta.position.z - recovered.raw_position.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < 2.0 * grid.voxel_size:
                total += 1
                if ta.element == recovered.atom_type:
                    correct += 1
                break
    return correct / total if total > 0 else 0.0


# =============================================================================
# FULL EXPERIMENT METRICS
# =============================================================================

@dataclass
class ExperimentMetrics:
    # Support recovery
    recall: float
    precision: float
    f1_score: float
    support_iou: float

    # Coordinate accuracy
    coordinate_rmsd: float
    max_coordinate_error: float
    mean_coordinate_error: float

    # Atom type
    atom_type_accuracy: float

    # Shot efficiency
    total_shots: int
    useful_shots: int
    wasted_shots: int
    useful_shot_fraction: float
    wasted_shot_fraction: float

    # Noise composition
    valid_atom_fraction: float
    empty_voxel_fraction: float
    invalid_index_fraction: float

    # Signal quality
    snr: float
    mean_count_per_atom: float
    mean_count_per_empty_voxel: float

    # Coupon collector
    expected_shots_uniform: float
    expected_shots_nonuniform: float
    confidence_bound: float

    # Circuit complexity
    estimated_depth: int
    estimated_gate_count: int
    estimated_swap_count: int

    # Runtime
    preparation_time_ms: float
    measurement_time_ms: float
    recovery_time_ms: float
    total_time_ms: float


def compute_experiment_metrics(
    recovered_atoms: List[RecoveredAtom],
    true_molecule: Molecule,
    true_support: QuantumSupport,
    measurements: MeasurementCounts,
    grid: VoxelGrid,
    preparation_time_ms: float,
    measurement_time_ms: float,
    recovery_time_ms: float,
    estimated_depth: int,
    estimated_gate_count: int,
    estimated_swap_count: int,
) -> ExperimentMetrics:
    recall = compute_recall(recovered_atoms, true_support.atom_count)
    precision = compute_precision(recovered_atoms, true_support)
    f1_score = compute_f1_score(precision, recall)
    support_iou = compute_support_iou(recovered_atoms, true_support)

    coordinate_rmsd = compute_coordinate_rmsd(recovered_atoms, true_molecule, grid)
    max_coord_err = compute_max_coordinate_error(recovered_atoms, true_molecule, grid)
    mean_coord_err = compute_mean_coordinate_error(recovered_atoms, true_molecule, grid)
    atom_type_acc = compute_atom_type_accuracy(recovered_atoms, true_molecule, grid)

    total_shots = measurements.total_shots
    useful_shots = measurements.valid_atom_count
    wasted_shots = measurements.empty_voxel_count + measurements.invalid_index_count
    useful_frac = compute_useful_shot_fraction(measurements)
    wasted_frac = compute_wasted_shot_fraction(measurements)

    valid_frac = measurements.valid_atom_count / total_shots if total_shots > 0 else 0.0
    empty_frac = measurements.empty_voxel_count / total_shots if total_shots > 0 else 0.0
    invalid_frac = measurements.invalid_index_count / total_shots if total_shots > 0 else 0.0

    snr = compute_snr(measurements, true_support, grid)
    mean_count_per_atom = (
        measurements.valid_atom_count / max(1, measurements.unique_indices)
    )
    mean_count_per_empty = measurements.empty_voxel_count / max(
        1, grid.encoding_dimension - true_support.atom_count
    )

    a = true_support.atom_count
    exp_shots_uniform = a * (math.log(a) + 0.5772) if a > 0 else 0.0
    exp_shots_nonuniform = exp_shots_uniform * 1.2
    confidence_bound = exp_shots_uniform * 1.5

    total_time_ms = preparation_time_ms + measurement_time_ms + recovery_time_ms

    return ExperimentMetrics(
        recall=recall,
        precision=precision,
        f1_score=f1_score,
        support_iou=support_iou,
        coordinate_rmsd=coordinate_rmsd,
        max_coordinate_error=max_coord_err,
        mean_coordinate_error=mean_coord_err,
        atom_type_accuracy=atom_type_acc,
        total_shots=total_shots,
        useful_shots=useful_shots,
        wasted_shots=wasted_shots,
        useful_shot_fraction=useful_frac,
        wasted_shot_fraction=wasted_frac,
        valid_atom_fraction=valid_frac,
        empty_voxel_fraction=empty_frac,
        invalid_index_fraction=invalid_frac,
        snr=snr,
        mean_count_per_atom=mean_count_per_atom,
        mean_count_per_empty_voxel=mean_count_per_empty,
        expected_shots_uniform=exp_shots_uniform,
        expected_shots_nonuniform=exp_shots_nonuniform,
        confidence_bound=confidence_bound,
        estimated_depth=estimated_depth,
        estimated_gate_count=estimated_gate_count,
        estimated_swap_count=estimated_swap_count,
        preparation_time_ms=preparation_time_ms,
        measurement_time_ms=measurement_time_ms,
        recovery_time_ms=recovery_time_ms,
        total_time_ms=total_time_ms,
    )


@dataclass
class MetricsComparison:
    recall_delta: float
    precision_delta: float
    f1_delta: float
    rmsd_delta: float
    shots_delta: float
    wasted_shots_delta: float
    snr_delta: float
    time_delta: float
    improvement: bool


def compare_metrics(
    improved: ExperimentMetrics, baseline: ExperimentMetrics
) -> MetricsComparison:
    recall_delta = improved.recall - baseline.recall
    precision_delta = improved.precision - baseline.precision
    f1_delta = improved.f1_score - baseline.f1_score
    rmsd_delta = improved.coordinate_rmsd - baseline.coordinate_rmsd
    shots_delta = float(improved.total_shots - baseline.total_shots)
    wasted_shots_delta = improved.wasted_shot_fraction - baseline.wasted_shot_fraction
    snr_delta = improved.snr - baseline.snr
    time_delta = improved.total_time_ms - baseline.total_time_ms

    is_improvement = (
        recall_delta >= -0.01
        and precision_delta >= -0.01
        and rmsd_delta <= 0.01
        and wasted_shots_delta <= 0.01
    )
    return MetricsComparison(
        recall_delta=recall_delta,
        precision_delta=precision_delta,
        f1_delta=f1_delta,
        rmsd_delta=rmsd_delta,
        shots_delta=shots_delta,
        wasted_shots_delta=wasted_shots_delta,
        snr_delta=snr_delta,
        time_delta=time_delta,
        improvement=is_improvement,
    )


def format_metrics(metrics: ExperimentMetrics) -> Dict[str, str]:
    return {
        "Recall": f"{metrics.recall * 100:.1f}%",
        "Precision": f"{metrics.precision * 100:.1f}%",
        "F1 Score": f"{metrics.f1_score:.3f}",
        "Support IoU": f"{metrics.support_iou:.3f}",
        "Coordinate RMSD": f"{metrics.coordinate_rmsd:.3f} A",
        "Max Error": f"{metrics.max_coordinate_error:.3f} A",
        "Mean Error": f"{metrics.mean_coordinate_error:.3f} A",
        "Atom Type Accuracy": f"{metrics.atom_type_accuracy * 100:.1f}%",
        "Total Shots": str(metrics.total_shots),
        "Useful Shots": f"{metrics.useful_shots} ({metrics.useful_shot_fraction * 100:.1f}%)",
        "Wasted Shots": f"{metrics.wasted_shots} ({metrics.wasted_shot_fraction * 100:.1f}%)",
        "SNR": f"{metrics.snr:.2f}",
        "Valid Atom %": f"{metrics.valid_atom_fraction * 100:.1f}%",
        "Empty Voxel %": f"{metrics.empty_voxel_fraction * 100:.1f}%",
        "Invalid Index %": f"{metrics.invalid_index_fraction * 100:.1f}%",
        "Expected Shots (Uniform)": str(math.ceil(metrics.expected_shots_uniform)),
        "Estimated Depth": str(metrics.estimated_depth),
        "Estimated Gates": str(metrics.estimated_gate_count),
        "Total Time": f"{metrics.total_time_ms:.1f} ms",
    }
