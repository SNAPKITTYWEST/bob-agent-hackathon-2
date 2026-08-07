"""
Sparse State Preparation Estimators

Estimates circuit complexity for preparing sparse quantum support states.

Made with Bob
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


# =============================================================================
# DATA TYPES
# =============================================================================

@dataclass
class QuantumSupport:
    occupied_indices: List[int]   # M* = {c_1, c_2, ..., c_A}
    atom_count: int               # A
    amplitudes: List[float]       # 1/sqrt(A) for each occupied index
    valid_subspace: tuple         # (0, C-1)
    invalid_subspace: tuple       # (C, 2^n - 1)


@dataclass
class VoxelGrid:
    resolution: int
    voxel_size: float
    grid_half_extent: float
    total_voxels: int
    atom_type_count: int
    encoding_dimension: int
    required_qubits: int


@dataclass
class StatePreparationEstimate:
    method: Literal["isometry", "bdd", "trie", "qrom", "gray", "variational"]
    one_qubit_gates: int
    two_qubit_gates: int
    depth: int
    ancilla_qubits: int
    swap_count: int
    estimated_error: float
    complexity: str


# =============================================================================
# ESTIMATION FUNCTIONS
# =============================================================================

def estimate_isometry_preparation(
    support: QuantumSupport, grid: VoxelGrid
) -> StatePreparationEstimate:
    """Estimate generic isometry-based state preparation."""
    a = support.atom_count
    n = grid.required_qubits

    scaling_factor = 2.1
    total_gates = math.ceil((a * (1 << n)) / scaling_factor)
    two_qubit_gates = math.ceil(total_gates * 0.8)
    one_qubit_gates = total_gates - two_qubit_gates
    depth = math.ceil(n * math.log2(max(a, 2)) * 1.5)
    ancilla_qubits = 0
    swap_count = math.ceil(n * n * 0.3)
    estimated_error = total_gates * 0.001

    return StatePreparationEstimate(
        method="isometry",
        one_qubit_gates=one_qubit_gates,
        two_qubit_gates=two_qubit_gates,
        depth=depth,
        ancilla_qubits=ancilla_qubits,
        swap_count=swap_count,
        estimated_error=estimated_error,
        complexity=f"O(A x 2^n) = O({a} x {1 << n})",
    )


def estimate_bdd_preparation(
    support: QuantumSupport, grid: VoxelGrid
) -> StatePreparationEstimate:
    """Estimate binary decision diagram (BDD) preparation."""
    a = support.atom_count
    n = grid.required_qubits

    structure_factor = math.log2(max(a, 2))
    total_gates = math.ceil(n * a * structure_factor)
    two_qubit_gates = math.ceil(total_gates * 0.6)
    one_qubit_gates = total_gates - two_qubit_gates
    depth = math.ceil(n * structure_factor)
    ancilla_qubits = math.ceil(math.log2(a)) if a > 1 else 1
    swap_count = math.ceil(n * math.log2(n)) if n > 1 else 0
    estimated_error = total_gates * 0.0008

    return StatePreparationEstimate(
        method="bdd",
        one_qubit_gates=one_qubit_gates,
        two_qubit_gates=two_qubit_gates,
        depth=depth,
        ancilla_qubits=ancilla_qubits,
        swap_count=swap_count,
        estimated_error=estimated_error,
        complexity=(
            f"O(n x A x log A) = O({n} x {a} x {math.ceil(math.log2(max(a, 2)))})"
        ),
    )


def estimate_trie_preparation(
    support: QuantumSupport, grid: VoxelGrid
) -> StatePreparationEstimate:
    """Estimate trie-based uniformly controlled rotations."""
    a = support.atom_count
    n = grid.required_qubits

    gates_per_atom = max(1.0, n - math.log2(max(a, 2)))
    total_gates = math.ceil(a * gates_per_atom * 1.2)
    two_qubit_gates = math.ceil(total_gates * 0.7)
    one_qubit_gates = total_gates - two_qubit_gates
    depth = math.ceil(gates_per_atom * math.log2(max(a, 2)))
    ancilla_qubits = 1
    swap_count = math.ceil(n * 0.5)
    estimated_error = total_gates * 0.0009

    return StatePreparationEstimate(
        method="trie",
        one_qubit_gates=one_qubit_gates,
        two_qubit_gates=two_qubit_gates,
        depth=depth,
        ancilla_qubits=ancilla_qubits,
        swap_count=swap_count,
        estimated_error=estimated_error,
        complexity=f"O(A x (n - log A)) = O({a} x {math.ceil(gates_per_atom)})",
    )


def estimate_qrom_preparation(
    support: QuantumSupport, grid: VoxelGrid
) -> StatePreparationEstimate:
    """Estimate QROM-assisted sparse support loading."""
    a = support.atom_count
    n = grid.required_qubits

    address_qubits = math.ceil(math.log2(max(a, 2)))
    qrom_gates = a * 2
    addressing_gates = address_qubits * 3
    total_gates = qrom_gates + addressing_gates
    two_qubit_gates = math.ceil(total_gates * 0.5)
    one_qubit_gates = total_gates - two_qubit_gates
    depth = math.ceil(math.log2(max(a, 2)) * 2)
    ancilla_qubits = address_qubits
    swap_count = math.ceil(address_qubits * 0.8)
    estimated_error = total_gates * 0.0007

    return StatePreparationEstimate(
        method="qrom",
        one_qubit_gates=one_qubit_gates,
        two_qubit_gates=two_qubit_gates,
        depth=depth,
        ancilla_qubits=ancilla_qubits,
        swap_count=swap_count,
        estimated_error=estimated_error,
        complexity=f"O(A + log A) = O({a} + {address_qubits})",
    )


def estimate_gray_code_preparation(
    support: QuantumSupport, grid: VoxelGrid
) -> StatePreparationEstimate:
    """Estimate Gray code traversal preparation."""
    a = support.atom_count
    n = grid.required_qubits

    avg_hamming_distance = n / 2.0
    total_gates = math.ceil(a * avg_hamming_distance * 1.5)
    two_qubit_gates = math.ceil(total_gates * 0.4)
    one_qubit_gates = total_gates - two_qubit_gates
    depth = math.ceil(a * 0.6)
    ancilla_qubits = 0
    swap_count = math.ceil(n * 0.4)
    estimated_error = total_gates * 0.0008

    return StatePreparationEstimate(
        method="gray",
        one_qubit_gates=one_qubit_gates,
        two_qubit_gates=two_qubit_gates,
        depth=depth,
        ancilla_qubits=ancilla_qubits,
        swap_count=swap_count,
        estimated_error=estimated_error,
        complexity=f"O(A x n) = O({a} x {n})",
    )


def estimate_variational_preparation(
    support: QuantumSupport, grid: VoxelGrid
) -> StatePreparationEstimate:
    """Estimate variational sparse-support ansatz."""
    a = support.atom_count
    n = grid.required_qubits

    layers = math.ceil(math.log2(max(a, 2)) * 1.5)
    one_qubit_gates_per_layer = n * 3  # RX, RY, RZ per qubit
    two_qubit_gates_per_layer = n - 1  # linear entanglement
    one_qubit_gates = one_qubit_gates_per_layer * layers
    two_qubit_gates = two_qubit_gates_per_layer * layers
    depth = layers * 4
    ancilla_qubits = 0
    swap_count = math.ceil((n - 1) * layers * 0.2)
    estimated_error = 0.01  # 1% typical for well-optimized ansatz

    log_a = math.ceil(math.log2(max(a, 2)))
    return StatePreparationEstimate(
        method="variational",
        one_qubit_gates=one_qubit_gates,
        two_qubit_gates=two_qubit_gates,
        depth=depth,
        ancilla_qubits=ancilla_qubits,
        swap_count=swap_count,
        estimated_error=estimated_error,
        complexity=(
            f"O(n x log A) layers = O({n} x {log_a}) = {layers} layers"
        ),
    )


# =============================================================================
# COMPARISON & TOTAL RESOURCE ESTIMATION
# =============================================================================

@dataclass
class PreparationComparison:
    methods: List[StatePreparationEstimate]
    recommended: StatePreparationEstimate
    ranking: List[Dict]  # [{"method": str, "score": float}]


def compare_preparation_methods(
    support: QuantumSupport,
    grid: VoxelGrid,
    weights: Optional[Dict[str, float]] = None,
) -> PreparationComparison:
    """Compare all preparation methods and recommend best."""
    if weights is None:
        weights = {
            "depth": 1.0,
            "two_qubit_gates": 0.5,
            "swaps": 0.3,
            "error": 2.0,
        }

    methods = [
        estimate_isometry_preparation(support, grid),
        estimate_bdd_preparation(support, grid),
        estimate_trie_preparation(support, grid),
        estimate_qrom_preparation(support, grid),
        estimate_gray_code_preparation(support, grid),
        estimate_variational_preparation(support, grid),
    ]

    max_depth = max(m.depth for m in methods) or 1
    max_two_qubit = max(m.two_qubit_gates for m in methods) or 1
    max_swaps = max(m.swap_count for m in methods) or 1
    max_error = max(m.estimated_error for m in methods) or 1.0

    scores: List[float] = []
    for m in methods:
        score = (
            weights["depth"] * (m.depth / max_depth)
            + weights["two_qubit_gates"] * (m.two_qubit_gates / max_two_qubit)
            + weights["swaps"] * (m.swap_count / max_swaps)
            + weights["error"] * (m.estimated_error / max_error)
        )
        scores.append(score)

    best_index = scores.index(min(scores))
    recommended = methods[best_index]

    ranking = sorted(
        [{"method": m.method, "score": scores[i]} for i, m in enumerate(methods)],
        key=lambda x: x["score"],
    )

    return PreparationComparison(
        methods=methods,
        recommended=recommended,
        ranking=ranking,
    )


@dataclass
class TotalCircuitResources:
    preparation: StatePreparationEstimate
    measurement_depth: int
    total_depth: int
    total_one_qubit_gates: int
    total_two_qubit_gates: int
    total_gates: int
    total_ancilla_qubits: int
    total_swap_count: int
    estimated_fidelity: float


def estimate_total_circuit_resources(
    support: QuantumSupport,
    grid: VoxelGrid,
    preparation_method: str = "isometry",
) -> TotalCircuitResources:
    """Estimate total circuit resources including measurement."""
    dispatch = {
        "bdd": estimate_bdd_preparation,
        "trie": estimate_trie_preparation,
        "qrom": estimate_qrom_preparation,
        "gray": estimate_gray_code_preparation,
        "variational": estimate_variational_preparation,
    }

    if preparation_method in dispatch:
        preparation = dispatch[preparation_method](support, grid)
    else:
        preparation = estimate_isometry_preparation(support, grid)

    measurement_depth = 1
    total_depth = preparation.depth + measurement_depth
    total_one_qubit_gates = preparation.one_qubit_gates
    total_two_qubit_gates = preparation.two_qubit_gates
    total_gates = total_one_qubit_gates + total_two_qubit_gates
    estimated_fidelity = max(0.0, 1.0 - preparation.estimated_error)

    return TotalCircuitResources(
        preparation=preparation,
        measurement_depth=measurement_depth,
        total_depth=total_depth,
        total_one_qubit_gates=total_one_qubit_gates,
        total_two_qubit_gates=total_two_qubit_gates,
        total_gates=total_gates,
        total_ancilla_qubits=preparation.ancilla_qubits,
        total_swap_count=preparation.swap_count,
        estimated_fidelity=estimated_fidelity,
    )
