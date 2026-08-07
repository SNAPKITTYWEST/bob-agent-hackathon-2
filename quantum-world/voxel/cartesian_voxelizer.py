"""
Cartesian Voxelization - Paper Algorithm Implementation

Implements the exact voxelization scheme from:
"Sparse Quantum Voxel Encoding for Readout-Efficient
Molecular Geometry Reconstruction on NISQ Devices"

Made with Bob
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# =============================================================================
# DATA TYPES (mirroring quantum.ts)
# =============================================================================

@dataclass
class Vec3:
    x: float
    y: float
    z: float


@dataclass
class Atom:
    id: str
    element: str
    type_index: int
    position: Vec3
    mass: Optional[float] = None
    charge: Optional[float] = None


@dataclass
class Bond:
    id: str
    atom1_id: str
    atom2_id: str
    order: float  # 1, 2, 3, or 1.5 (aromatic)
    length: Optional[float] = None


@dataclass
class BoundingBox:
    min: Vec3
    max: Vec3


@dataclass
class Molecule:
    id: str
    name: str
    atoms: List[Atom]
    formula: Optional[str] = None
    smiles: Optional[str] = None
    bonds: Optional[List[Bond]] = None
    centroid: Optional[Vec3] = None
    bounding_box: Optional[BoundingBox] = None


@dataclass
class CartesianVoxelAddress:
    i: int           # x-axis voxel index
    j: int           # y-axis voxel index
    k: int           # z-axis voxel index
    voxel_index: int  # linear: i*V^2 + j*V + k
    type_index: int  # atom type index
    combined_index: int  # voxel_index * T + type_index


@dataclass
class VoxelGrid:
    resolution: int         # V (voxels per axis)
    voxel_size: float       # s_voxel (angstroms)
    grid_half_extent: float  # r_grid = V * s_voxel / 2
    total_voxels: int       # V^3
    atom_type_count: int    # T
    encoding_dimension: int  # C = V^3 * T
    required_qubits: int    # n = ceil(log2(C))


@dataclass
class VoxelizationResult:
    grid: VoxelGrid
    atom_addresses: Dict[str, CartesianVoxelAddress]  # atom_id -> address
    occupied_voxels: Set[int]
    collisions: List[Dict]  # [{"atom_ids": [...], "voxel_index": int}]
    clipped_atoms: List[str]
    centered_molecule: Molecule


# =============================================================================
# FUNCTIONS
# =============================================================================

def center_molecule(molecule: Molecule) -> Molecule:
    """
    Center molecule at centroid.
    c = (1/A) * sum(r_a)
    r'_a = r_a - c
    """
    atoms = molecule.atoms
    a_count = len(atoms)

    if a_count == 0:
        return Molecule(
            id=molecule.id,
            name=molecule.name,
            atoms=[],
            formula=molecule.formula,
            smiles=molecule.smiles,
            bonds=molecule.bonds,
            centroid=Vec3(0.0, 0.0, 0.0),
        )

    cx = sum(a.position.x for a in atoms) / a_count
    cy = sum(a.position.y for a in atoms) / a_count
    cz = sum(a.position.z for a in atoms) / a_count
    centroid = Vec3(cx, cy, cz)

    centered_atoms = [
        Atom(
            id=a.id,
            element=a.element,
            type_index=a.type_index,
            position=Vec3(
                a.position.x - cx,
                a.position.y - cy,
                a.position.z - cz,
            ),
            mass=a.mass,
            charge=a.charge,
        )
        for a in atoms
    ]

    xs = [a.position.x for a in centered_atoms]
    ys = [a.position.y for a in centered_atoms]
    zs = [a.position.z for a in centered_atoms]
    bounding_box = BoundingBox(
        min=Vec3(min(xs), min(ys), min(zs)),
        max=Vec3(max(xs), max(ys), max(zs)),
    )

    return Molecule(
        id=molecule.id,
        name=molecule.name,
        atoms=centered_atoms,
        formula=molecule.formula,
        smiles=molecule.smiles,
        bonds=molecule.bonds,
        centroid=centroid,
        bounding_box=bounding_box,
    )


def create_voxel_grid(
    resolution: int,
    voxel_size: float,
    atom_type_count: int,
) -> VoxelGrid:
    """Create voxel grid configuration."""
    v = resolution
    s_voxel = voxel_size
    r_grid = (v * s_voxel) / 2.0
    total_voxels = v * v * v
    t = atom_type_count
    encoding_dim = total_voxels * t
    n = math.ceil(math.log2(encoding_dim)) if encoding_dim > 1 else 1
    return VoxelGrid(
        resolution=v,
        voxel_size=s_voxel,
        grid_half_extent=r_grid,
        total_voxels=total_voxels,
        atom_type_count=t,
        encoding_dimension=encoding_dim,
        required_qubits=n,
    )


def _coordinate_to_voxel_index(
    coord: float,
    grid_half_extent: float,
    voxel_size: float,
    resolution: int,
) -> Tuple[int, bool]:
    """Map continuous coordinate to voxel index. Returns (index, clipped)."""
    raw_index = int(math.floor((coord + grid_half_extent) / voxel_size))
    clipped = raw_index < 0 or raw_index >= resolution
    index = max(0, min(resolution - 1, raw_index))
    return index, clipped


def _compute_linear_voxel_index(i: int, j: int, k: int, v: int) -> int:
    """Compute linear voxel index: v = i * V^2 + j * V + k"""
    return i * v * v + j * v + k


def _compute_combined_index(voxel_index: int, type_index: int, t: int) -> int:
    """Compute combined atom index: c = v * T + tau"""
    return voxel_index * t + type_index


def decode_combined_index(combined_index: int, grid: VoxelGrid) -> Dict:
    """Decode combined index back to voxel and type."""
    t = grid.atom_type_count
    v = grid.resolution
    type_index = combined_index % t
    voxel_index = combined_index // t
    i = voxel_index // (v * v)
    remainder = voxel_index % (v * v)
    j = remainder // v
    k = remainder % v
    return {
        "voxel_index": voxel_index,
        "type_index": type_index,
        "i": i,
        "j": j,
        "k": k,
    }


def voxel_center_position(i: int, j: int, k: int, grid: VoxelGrid) -> Vec3:
    """Compute voxel center position: x_hat = (i + 0.5) * s_voxel - r_grid"""
    s = grid.voxel_size
    r = grid.grid_half_extent
    return Vec3(
        x=(i + 0.5) * s - r,
        y=(j + 0.5) * s - r,
        z=(k + 0.5) * s - r,
    )


def quantization_bounds(grid: VoxelGrid) -> Dict:
    """Compute quantization error bounds."""
    s = grid.voxel_size
    return {
        "per_axis_max": s / 2.0,
        "euclidean_max": (math.sqrt(3) * s) / 2.0,
        "rms_uniform": s / 2.0,
    }


def check_collision_constraint(
    min_interatomic_distance: float,
    voxel_size: float,
) -> Dict:
    """Check collision constraint: sqrt(3) * s_voxel < d_min"""
    required = math.sqrt(3) * voxel_size
    satisfied = required < min_interatomic_distance
    margin = min_interatomic_distance - required
    return {"satisfied": satisfied, "margin": margin}


def compute_min_interatomic_distance(molecule: Molecule) -> float:
    """Compute minimum interatomic distance."""
    atoms = molecule.atoms
    min_dist = float("inf")
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            a = atoms[i].position
            b = atoms[j].position
            dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < min_dist:
                min_dist = dist
    return min_dist


def voxelize_molecule(
    molecule: Molecule,
    grid: VoxelGrid,
    atom_type_map: Dict[str, int],
) -> VoxelizationResult:
    """Main voxelization function - implements paper algorithm."""
    centered = center_molecule(molecule)
    atom_addresses: Dict[str, CartesianVoxelAddress] = {}
    occupied_voxels: Set[int] = set()
    voxel_to_atoms: Dict[int, List[str]] = {}
    clipped_atoms: List[str] = []

    for atom in centered.atoms:
        type_index = atom_type_map.get(atom.element)
        if type_index is None:
            raise ValueError(f"Unknown atom type: {atom.element}")

        i, i_clipped = _coordinate_to_voxel_index(
            atom.position.x, grid.grid_half_extent, grid.voxel_size, grid.resolution
        )
        j, j_clipped = _coordinate_to_voxel_index(
            atom.position.y, grid.grid_half_extent, grid.voxel_size, grid.resolution
        )
        k, k_clipped = _coordinate_to_voxel_index(
            atom.position.z, grid.grid_half_extent, grid.voxel_size, grid.resolution
        )

        if i_clipped or j_clipped or k_clipped:
            clipped_atoms.append(atom.id)

        voxel_index = _compute_linear_voxel_index(i, j, k, grid.resolution)
        combined_index = _compute_combined_index(voxel_index, type_index, grid.atom_type_count)

        atom_addresses[atom.id] = CartesianVoxelAddress(
            i=i,
            j=j,
            k=k,
            voxel_index=voxel_index,
            type_index=type_index,
            combined_index=combined_index,
        )
        occupied_voxels.add(voxel_index)
        voxel_to_atoms.setdefault(voxel_index, []).append(atom.id)

    collisions = [
        {"atom_ids": atom_ids, "voxel_index": vi}
        for vi, atom_ids in voxel_to_atoms.items()
        if len(atom_ids) > 1
    ]

    return VoxelizationResult(
        grid=grid,
        atom_addresses=atom_addresses,
        occupied_voxels=occupied_voxels,
        collisions=collisions,
        clipped_atoms=clipped_atoms,
        centered_molecule=centered,
    )


def create_atom_type_map(atom_types: List[str]) -> Dict[str, int]:
    """Create atom type mapping from list of types."""
    return {t: idx for idx, t in enumerate(atom_types)}


def extract_atom_types(molecule: Molecule) -> List[str]:
    """Extract unique atom types from molecule, sorted."""
    return sorted({a.element for a in molecule.atoms})


def validate_voxelization(result: VoxelizationResult) -> Dict:
    """Validate voxelization result."""
    errors: List[str] = []
    warnings: List[str] = []

    if result.collisions:
        errors.append(
            f"Found {len(result.collisions)} voxel collisions "
            "(multiple atoms in same voxel)"
        )

    if result.clipped_atoms:
        warnings.append(
            f"{len(result.clipped_atoms)} atoms were clipped to grid boundaries"
        )

    if result.atom_addresses:
        max_combined = max(
            addr.combined_index for addr in result.atom_addresses.values()
        )
        if max_combined >= result.grid.encoding_dimension:
            errors.append(
                f"Combined index {max_combined} exceeds encoding dimension "
                f"{result.grid.encoding_dimension}"
            )

    required_bits = (
        math.ceil(math.log2(result.grid.encoding_dimension))
        if result.grid.encoding_dimension > 1
        else 1
    )
    if required_bits != result.grid.required_qubits:
        errors.append(
            f"Qubit count mismatch: computed {required_bits}, "
            f"expected {result.grid.required_qubits}"
        )

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def compute_reconstruction_error(
    original_molecule: Molecule,
    voxelization_result: VoxelizationResult,
) -> Dict:
    """Compute reconstruction error for a voxelized molecule."""
    errors: Dict[str, float] = {}
    sum_sq = 0.0
    max_err = 0.0

    centered_by_id = {a.id: a for a in voxelization_result.centered_molecule.atoms}

    for atom in original_molecule.atoms:
        address = voxelization_result.atom_addresses.get(atom.id)
        if address is None:
            continue
        centered_atom = centered_by_id.get(atom.id)
        if centered_atom is None:
            continue

        vc = voxel_center_position(address.i, address.j, address.k, voxelization_result.grid)
        dx = centered_atom.position.x - vc.x
        dy = centered_atom.position.y - vc.y
        dz = centered_atom.position.z - vc.z
        error = math.sqrt(dx * dx + dy * dy + dz * dz)

        errors[atom.id] = error
        sum_sq += error * error
        if error > max_err:
            max_err = error

    n = len(errors)
    rmsd = math.sqrt(sum_sq / n) if n > 0 else 0.0
    mean_error = math.sqrt(sum_sq) / n if n > 0 else 0.0

    return {
        "per_atom_errors": errors,
        "mean_error": mean_error,
        "max_error": max_err,
        "rmsd": rmsd,
    }
