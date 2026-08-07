"""
Quantum Measurement Simulator + Support State Construction

Simulates computational-basis measurements of sparse quantum support states
with configurable NISQ noise channels.

Also contains all support state functions from supportState.ts.

Made with Bob
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..voxel.cartesian_voxelizer import (
    VoxelGrid,
    Vec3,
    decode_combined_index,
    voxel_center_position,
    voxelize_molecule,
    create_voxel_grid,
    create_atom_type_map,
    extract_atom_types,
    Molecule,
    CartesianVoxelAddress,
)


# =============================================================================
# DATA TYPES
# =============================================================================

@dataclass
class QuantumSupport:
    occupied_indices: List[int]   # M* = {c_1, ..., c_A}
    atom_count: int               # A
    amplitudes: List[float]       # 1/sqrt(A) for each occupied index
    valid_subspace: Tuple[int, int]    # (0, C-1)
    invalid_subspace: Tuple[int, int]  # (C, 2^n - 1)


@dataclass
class NoiseProfile:
    name: str
    amplitude_damping: float    # T1 relaxation
    dephasing: float            # T2 dephasing
    depolarizing_1q: float      # single-qubit depolarizing
    depolarizing_2q: float      # two-qubit depolarizing
    readout_zero_to_one: float  # |0> -> |1> assignment error
    readout_one_to_zero: float  # |1> -> |0> assignment error
    ground_state_bias: float    # bias toward |0>
    leakage: float              # leakage to non-computational states
    gate_error_rate: Optional[float] = None
    coherence_time: Optional[float] = None  # microseconds


@dataclass
class MeasurementOutcome:
    basis_index: int
    count: int
    classification: str  # 'correct_atom' | 'empty_voxel' | 'invalid_index'
    decoded_position: Optional[Vec3] = None
    decoded_atom_type: Optional[str] = None


@dataclass
class MeasurementCounts:
    total_shots: int
    counts: Dict[int, int]
    unique_indices: int
    valid_atom_count: int
    empty_voxel_count: int
    invalid_index_count: int


@dataclass
class ShotBatch:
    batch_number: int
    batch_size: int
    cumulative_shots: int
    outcomes: List[MeasurementOutcome]
    timestamp: float


# Noise presets
NOISE_PRESETS: Dict[str, NoiseProfile] = {
    "ideal": NoiseProfile(
        name="Ideal (No Noise)",
        amplitude_damping=0.0,
        dephasing=0.0,
        depolarizing_1q=0.0,
        depolarizing_2q=0.0,
        readout_zero_to_one=0.0,
        readout_one_to_zero=0.0,
        ground_state_bias=0.0,
        leakage=0.0,
    ),
    "erasure": NoiseProfile(
        name="Erasure-like",
        amplitude_damping=0.15,
        dephasing=0.05,
        depolarizing_1q=0.001,
        depolarizing_2q=0.01,
        readout_zero_to_one=0.02,
        readout_one_to_zero=0.02,
        ground_state_bias=0.1,
        leakage=0.0,
    ),
    "kingston": NoiseProfile(
        name="Kingston-like (Paper Hardware)",
        amplitude_damping=0.25,
        dephasing=0.15,
        depolarizing_1q=0.002,
        depolarizing_2q=0.02,
        readout_zero_to_one=0.039,
        readout_one_to_zero=0.015,
        ground_state_bias=0.35,
        leakage=0.005,
    ),
    "depolarizing": NoiseProfile(
        name="Uniform Depolarizing",
        amplitude_damping=0.0,
        dephasing=0.0,
        depolarizing_1q=0.01,
        depolarizing_2q=0.05,
        readout_zero_to_one=0.01,
        readout_one_to_zero=0.01,
        ground_state_bias=0.0,
        leakage=0.0,
    ),
}


@dataclass
class MeasurementSimulator:
    support: QuantumSupport
    grid: VoxelGrid
    noise_profile: NoiseProfile
    atom_type_map: Dict[int, str]  # type_index -> element string
    _rng_seed: int = 0
    _rng: Optional[random.Random] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self._rng_seed)

    def rand(self) -> float:
        return self._rng.random()


# =============================================================================
# MEASUREMENT SIMULATOR FACTORY
# =============================================================================

def create_measurement_simulator(
    support: QuantumSupport,
    grid: VoxelGrid,
    noise_profile: NoiseProfile,
    atom_type_map: Dict[int, str],
    seed: int,
) -> MeasurementSimulator:
    sim = MeasurementSimulator(
        support=support,
        grid=grid,
        noise_profile=noise_profile,
        atom_type_map=atom_type_map,
        _rng_seed=seed,
    )
    return sim


# =============================================================================
# NOISE CHANNELS
# =============================================================================

def _apply_amplitude_damping(
    basis_index: int, damping_rate: float, rng: random.Random
) -> int:
    if damping_rate == 0:
        return basis_index
    n_qubits = math.ceil(math.log2(max(basis_index + 1, 2)))
    result = basis_index
    for q in range(n_qubits):
        bit_mask = 1 << q
        if (result & bit_mask) != 0:
            if rng.random() < damping_rate:
                result &= ~bit_mask
    return result


def _apply_depolarizing(
    basis_index: int,
    depolarizing_rate: float,
    max_index: int,
    rng: random.Random,
) -> int:
    if depolarizing_rate == 0:
        return basis_index
    if rng.random() < depolarizing_rate:
        return int(rng.random() * (max_index + 1))
    return basis_index


def _apply_readout_error(
    basis_index: int,
    zero_to_one: float,
    one_to_zero: float,
    rng: random.Random,
) -> int:
    n_qubits = math.ceil(math.log2(max(basis_index + 1, 2)))
    result = basis_index
    for q in range(n_qubits):
        bit_mask = 1 << q
        if (result & bit_mask) != 0:
            if rng.random() < one_to_zero:
                result &= ~bit_mask
        else:
            if rng.random() < zero_to_one:
                result |= bit_mask
    return result


def _apply_ground_state_bias(
    basis_index: int, bias_rate: float, rng: random.Random
) -> int:
    if bias_rate == 0 or basis_index == 0:
        return basis_index
    if rng.random() < bias_rate:
        return 0
    return basis_index


# =============================================================================
# IDEAL / NOISY MEASUREMENT
# =============================================================================

def measure_ideal(simulator: MeasurementSimulator) -> int:
    """Simulate ideal measurement (no noise)."""
    idx = int(simulator.rand() * len(simulator.support.occupied_indices))
    return simulator.support.occupied_indices[idx]


def measure_noisy(simulator: MeasurementSimulator) -> int:
    """Simulate noisy measurement."""
    rng = simulator._rng
    np_ = simulator.noise_profile
    grid = simulator.grid

    basis_index = measure_ideal(simulator)
    basis_index = _apply_amplitude_damping(basis_index, np_.amplitude_damping, rng)
    basis_index = _apply_ground_state_bias(basis_index, np_.ground_state_bias, rng)
    max_index = (1 << grid.required_qubits) - 1
    basis_index = _apply_depolarizing(basis_index, np_.depolarizing_1q, max_index, rng)
    basis_index = _apply_readout_error(
        basis_index, np_.readout_zero_to_one, np_.readout_one_to_zero, rng
    )
    if np_.leakage > 0 and rng.random() < np_.leakage:
        invalid_start = grid.encoding_dimension
        invalid_end = (1 << grid.required_qubits) - 1
        if invalid_start <= invalid_end:
            basis_index = invalid_start + int(
                rng.random() * (invalid_end - invalid_start + 1)
            )
    return basis_index


def classify_outcome(
    basis_index: int,
    support: QuantumSupport,
    grid: VoxelGrid,
) -> str:
    if basis_index >= grid.encoding_dimension:
        return "invalid_index"
    if basis_index in support.occupied_indices:
        return "correct_atom"
    return "empty_voxel"


def decode_outcome(
    basis_index: int,
    grid: VoxelGrid,
    atom_type_map: Dict[int, str],
    support: QuantumSupport,
) -> MeasurementOutcome:
    classification = classify_outcome(basis_index, support, grid)
    decoded_position: Optional[Vec3] = None
    decoded_atom_type: Optional[str] = None

    if classification != "invalid_index":
        decoded = decode_combined_index(basis_index, grid)
        decoded_position = voxel_center_position(
            decoded["i"], decoded["j"], decoded["k"], grid
        )
        decoded_atom_type = atom_type_map.get(decoded["type_index"])

    return MeasurementOutcome(
        basis_index=basis_index,
        count=1,
        classification=classification,
        decoded_position=decoded_position,
        decoded_atom_type=decoded_atom_type,
    )


def run_measurement_batch(
    simulator: MeasurementSimulator,
    shots: int,
    use_noise: bool,
) -> ShotBatch:
    """Run a measurement batch of 'shots' measurements."""
    counts: Dict[int, int] = {}
    for _ in range(shots):
        idx = measure_noisy(simulator) if use_noise else measure_ideal(simulator)
        counts[idx] = counts.get(idx, 0) + 1

    outcomes: List[MeasurementOutcome] = []
    for basis_index, count in counts.items():
        outcome = decode_outcome(
            basis_index, simulator.grid, simulator.atom_type_map, simulator.support
        )
        outcome.count = count
        outcomes.append(outcome)

    return ShotBatch(
        batch_number=0,
        batch_size=shots,
        cumulative_shots=shots,
        outcomes=outcomes,
        timestamp=time.time(),
    )


def aggregate_measurements(batches: List[ShotBatch]) -> MeasurementCounts:
    """Aggregate measurement counts across batches."""
    counts: Dict[int, int] = {}
    total_shots = 0
    valid_atom_count = 0
    empty_voxel_count = 0
    invalid_index_count = 0

    for batch in batches:
        total_shots += batch.batch_size
        for outcome in batch.outcomes:
            counts[outcome.basis_index] = (
                counts.get(outcome.basis_index, 0) + outcome.count
            )
            if outcome.classification == "correct_atom":
                valid_atom_count += outcome.count
            elif outcome.classification == "empty_voxel":
                empty_voxel_count += outcome.count
            elif outcome.classification == "invalid_index":
                invalid_index_count += outcome.count

    return MeasurementCounts(
        total_shots=total_shots,
        counts=counts,
        unique_indices=len(counts),
        valid_atom_count=valid_atom_count,
        empty_voxel_count=empty_voxel_count,
        invalid_index_count=invalid_index_count,
    )


def compute_snr(
    measurements: MeasurementCounts,
    support: QuantumSupport,
    grid: VoxelGrid,
) -> float:
    """Compute signal-to-noise ratio."""
    occupied_set = set(support.occupied_indices)
    atom_counts_sum = 0
    atom_indices_count = 0
    empty_count_sum = 0
    empty_indices_count = 0

    for index, count in measurements.counts.items():
        if index in occupied_set:
            atom_counts_sum += count
            atom_indices_count += 1
        elif index < grid.encoding_dimension:
            empty_count_sum += count
            empty_indices_count += 1

    mean_atom = atom_counts_sum / atom_indices_count if atom_indices_count > 0 else 0.0
    mean_empty = empty_count_sum / empty_indices_count if empty_indices_count > 0 else 0.0
    return mean_atom / mean_empty if mean_empty > 0 else float("inf")


def compute_useful_shot_fraction(measurements: MeasurementCounts) -> float:
    if measurements.total_shots == 0:
        return 0.0
    return measurements.valid_atom_count / measurements.total_shots


def compute_wasted_shot_fraction(measurements: MeasurementCounts) -> float:
    if measurements.total_shots == 0:
        return 0.0
    wasted = measurements.empty_voxel_count + measurements.invalid_index_count
    return wasted / measurements.total_shots


# =============================================================================
# SUPPORT STATE CONSTRUCTION  (from supportState.ts)
# =============================================================================

def create_quantum_support(
    occupied_indices: List[int], grid: VoxelGrid
) -> QuantumSupport:
    """Create quantum support state from voxelization result."""
    a = len(occupied_indices)
    if a == 0:
        raise ValueError("Cannot create support state with zero atoms")

    amplitude = 1.0 / math.sqrt(a)
    amplitudes = [amplitude] * a
    valid_subspace = (0, grid.encoding_dimension - 1)
    max_index = (1 << grid.required_qubits) - 1
    invalid_subspace = (grid.encoding_dimension, max_index)

    return QuantumSupport(
        occupied_indices=sorted(occupied_indices),
        atom_count=a,
        amplitudes=amplitudes,
        valid_subspace=valid_subspace,
        invalid_subspace=invalid_subspace,
    )


def create_quantum_support_from_molecule(
    molecule: Molecule,
    voxel_resolution: int,
    voxel_size: float,
) -> Dict:
    """Create quantum support directly from molecule."""
    atom_types = extract_atom_types(molecule)
    atom_type_map_str = create_atom_type_map(atom_types)
    grid = create_voxel_grid(voxel_resolution, voxel_size, len(atom_types))
    voxelization = voxelize_molecule(molecule, grid, atom_type_map_str)

    if voxelization.collisions:
        raise ValueError(
            f"Voxelization produced {len(voxelization.collisions)} collisions. "
            "Increase voxel size or grid resolution."
        )

    occupied_indices = sorted(
        addr.combined_index for addr in voxelization.atom_addresses.values()
    )
    support = create_quantum_support(occupied_indices, grid)
    return {
        "support": support,
        "grid": grid,
        "atom_addresses": voxelization.atom_addresses,
    }


def verify_support_normalization(support: QuantumSupport) -> Dict:
    """Verify support state normalization; sum of |amplitude|^2 should equal 1."""
    total_prob = sum(a * a for a in support.amplitudes)
    error = abs(total_prob - 1.0)
    return {
        "normalized": error < 1e-10,
        "total_probability": total_prob,
        "error": error,
    }


def analyze_support_properties(support: QuantumSupport, grid: VoxelGrid) -> Dict:
    """Compute support state properties."""
    a = support.atom_count
    c = grid.encoding_dimension
    n = grid.required_qubits
    max_index = (1 << n) - 1

    min_idx = min(support.occupied_indices)
    max_idx_occ = max(support.occupied_indices)
    index_span = max_idx_occ - min_idx + 1
    valid_subspace_size = c
    invalid_subspace_size = max_index - c + 1
    sparsity_fraction = a / c
    wasted_qubits = math.log2(max(invalid_subspace_size, 1))
    uniform_amplitude = 1.0 / math.sqrt(a)
    amplitude_variance = (
        sum((amp - uniform_amplitude) ** 2 for amp in support.amplitudes) / a
    )
    norm = verify_support_normalization(support)

    return {
        "atom_count": a,
        "occupied_indices": support.occupied_indices,
        "min_index": min_idx,
        "max_index": max_idx_occ,
        "index_span": index_span,
        "encoding_dimension": c,
        "valid_subspace_size": valid_subspace_size,
        "invalid_subspace_size": invalid_subspace_size,
        "sparsity_fraction": sparsity_fraction,
        "valid_sparsity_fraction": a / valid_subspace_size,
        "required_qubits": n,
        "wasted_qubits": wasted_qubits,
        "uniform_amplitude": uniform_amplitude,
        "amplitude_variance": amplitude_variance,
        "normalized": norm["normalized"],
        "normalization_error": norm["error"],
    }


def compute_support_overlap(
    support1: QuantumSupport, support2: QuantumSupport
) -> float:
    """Compute |<psi1|psi2>|^2."""
    indices2_map = {
        idx: j for j, idx in enumerate(support2.occupied_indices)
    }
    overlap = 0.0
    for i, index in enumerate(support1.occupied_indices):
        j = indices2_map.get(index)
        if j is not None:
            overlap += support1.amplitudes[i] * support2.amplitudes[j]
    return overlap * overlap


def compute_support_fidelity(
    support1: QuantumSupport, support2: QuantumSupport
) -> float:
    """Compute fidelity F = |<psi1|psi2>|^2."""
    return compute_support_overlap(support1, support2)


def create_dense_probability_distribution(
    support: QuantumSupport, max_index: int
) -> List[float]:
    distribution = [0.0] * (max_index + 1)
    for i, index in enumerate(support.occupied_indices):
        amp = support.amplitudes[i]
        distribution[index] = amp * amp
    return distribution


def sample_from_support(support: QuantumSupport, rng_func) -> int:
    """Sample from support state (ideal measurement)."""
    r = rng_func()
    cumulative = 0.0
    for i, index in enumerate(support.occupied_indices):
        amp = support.amplitudes[i]
        cumulative += amp * amp
        if r < cumulative:
            return index
    return support.occupied_indices[-1]


def compute_support_entropy(support: QuantumSupport) -> float:
    """Compute Shannon entropy S = -sum p_i log2(p_i)."""
    entropy = 0.0
    for amp in support.amplitudes:
        prob = amp * amp
        if prob > 0:
            entropy -= prob * math.log2(prob)
    return entropy


def max_support_entropy(atom_count: int) -> float:
    """Compute maximum entropy S_max = log2(A)."""
    return math.log2(atom_count) if atom_count > 0 else 0.0


def is_maximally_mixed(
    support: QuantumSupport, tolerance: float = 1e-10
) -> bool:
    uniform = 1.0 / math.sqrt(support.atom_count)
    return all(abs(amp - uniform) <= tolerance for amp in support.amplitudes)


def create_custom_support(
    occupied_indices: List[int],
    amplitudes: List[float],
    grid: VoxelGrid,
) -> QuantumSupport:
    if len(occupied_indices) != len(amplitudes):
        raise ValueError("Indices and amplitudes must have same length")
    a = len(occupied_indices)
    valid_subspace = (0, grid.encoding_dimension - 1)
    max_index = (1 << grid.required_qubits) - 1
    invalid_subspace = (grid.encoding_dimension, max_index)
    support = QuantumSupport(
        occupied_indices=list(occupied_indices),
        atom_count=a,
        amplitudes=list(amplitudes),
        valid_subspace=valid_subspace,
        invalid_subspace=invalid_subspace,
    )
    norm = verify_support_normalization(support)
    if not norm["normalized"]:
        import warnings
        warnings.warn(
            f"Custom support is not normalized: "
            f"total probability = {norm['total_probability']}"
        )
    return support


def renormalize_support(support: QuantumSupport) -> QuantumSupport:
    total_prob = sum(a * a for a in support.amplitudes)
    if total_prob == 0:
        raise ValueError("Cannot renormalize zero state")
    norm_factor = 1.0 / math.sqrt(total_prob)
    normalized_amplitudes = [amp * norm_factor for amp in support.amplitudes]
    return QuantumSupport(
        occupied_indices=support.occupied_indices,
        atom_count=support.atom_count,
        amplitudes=normalized_amplitudes,
        valid_subspace=support.valid_subspace,
        invalid_subspace=support.invalid_subspace,
    )
