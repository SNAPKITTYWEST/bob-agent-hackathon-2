# yao_types.jl
#
# Yao.jl block hierarchy — modeled WITHOUT the actual Yao.jl package.
#
# This file faithfully models Yao.jl's block-based type system using
# Julia's standard library only (no external packages).
#
# Key design principle from real Yao.jl:
#   - Every quantum object is an AbstractBlock
#   - Circuits are trees of composable blocks, not flat gate lists
#   - PutBlock locates a smaller block inside a larger register
#   - ControlBlock adds control qubits to any existing block
#   - ChainBlock applies blocks sequentially
#   - KronBlock applies blocks to disjoint qubit subsets in parallel
#
# NOTE: Real Yao.jl uses parametric types and extensive dispatch machinery.
# Here we use a simplified but structurally faithful representation.

# -----------------------------------------------------------------------
# Abstract root
# -----------------------------------------------------------------------

"""Abstract base type for all Yao.jl blocks (circuits are block trees)."""
abstract type AbstractBlock end

# -----------------------------------------------------------------------
# Primitive (leaf) blocks
# -----------------------------------------------------------------------

"""
    PrimitiveGate <: AbstractBlock

A named, parameterized single/multi-qubit gate with no sub-blocks.
`params` holds rotation angles in radians.
`nqubits` is the intrinsic arity (1 for H/X/Y/Z/T/S/Rx/Rz, 2 for CX, etc.).
"""
struct PrimitiveGate <: AbstractBlock
    name::String
    params::Vector{Float64}
    nqubits::Int
end

# -----------------------------------------------------------------------
# Composite blocks
# -----------------------------------------------------------------------

"""
    ChainBlock <: AbstractBlock

Sequential composition: blocks applied left-to-right on `nqubits`.
Real Yao.jl: `chain(n, gate1, gate2, ...)`
"""
struct ChainBlock <: AbstractBlock
    nqubits::Int
    blocks::Vector{AbstractBlock}
end

"""
    KronBlock <: AbstractBlock

Parallel composition: each sub-block acts on its own disjoint qubits.
`locs[i]` is the starting qubit index (1-based, matching Yao.jl convention)
for `blocks[i]`.

NOTE: In Yao.jl, `kron(n, i => gate_i, j => gate_j)` means both gates
apply simultaneously. In the QIR lowering this becomes sequential.
"""
struct KronBlock <: AbstractBlock
    nqubits::Int
    locs::Vector{Int}         # 1-based start qubit for each sub-block
    blocks::Vector{AbstractBlock}
end

"""
    ControlBlock <: AbstractBlock

A block guarded by classical control lines.
`ctrl_locs`: qubit indices of control lines (1-based)
`ctrl_bits`: required value (0 or 1) for each control qubit
`block`: the sub-block applied when all controls are satisfied

Examples:
  CNOT  = ControlBlock(2, [1], [1], X())      # control q1, target q2
  CCX   = ControlBlock(3, [1,2], [1,1], X())  # Toffoli: controls q1,q2, target q3
"""
struct ControlBlock <: AbstractBlock
    nqubits::Int
    ctrl_locs::Vector{Int}
    ctrl_bits::Vector{Int}     # 0 or 1
    block::AbstractBlock
end

"""
    PutBlock <: AbstractBlock

Place a smaller block onto specific qubit locations inside a larger register.
`locs`: 1-based qubit indices this sub-block occupies.
`block`: the block to place (must have nqubits == length(locs)).

Real Yao.jl: `put(n, locs => block)`
"""
struct PutBlock <: AbstractBlock
    nqubits::Int
    locs::Vector{Int}
    block::AbstractBlock
end

"""
    MeasureBlock <: AbstractBlock

Measure specified qubits, collapsing them to classical bits.
`locs`: 1-based qubit indices to measure.
"""
struct MeasureBlock <: AbstractBlock
    nqubits::Int
    locs::Vector{Int}
end

# -----------------------------------------------------------------------
# Standard gate constructors (matching Yao.jl API surface)
# -----------------------------------------------------------------------

"""Hadamard gate: |+⟩ = H|0⟩, |−⟩ = H|1⟩"""
H() = PrimitiveGate("H", Float64[], 1)

"""Pauli-X (NOT) gate"""
X() = PrimitiveGate("X", Float64[], 1)

"""Pauli-Y gate"""
Y() = PrimitiveGate("Y", Float64[], 1)

"""Pauli-Z gate"""
Z() = PrimitiveGate("Z", Float64[], 1)

"""T gate: phase shift by π/4"""
T() = PrimitiveGate("T", Float64[], 1)

"""S gate: phase shift by π/2"""
S() = PrimitiveGate("S", Float64[], 1)

"""
    Rx(θ)

Rotation about X-axis by angle θ (radians).
Rx(θ) = exp(-iθX/2) = cos(θ/2)I - i·sin(θ/2)X
"""
Rx(θ::Float64) = PrimitiveGate("Rx", [θ], 1)

"""
    Ry(θ)

Rotation about Y-axis by angle θ (radians).
"""
Ry(θ::Float64) = PrimitiveGate("Ry", [θ], 1)

"""
    Rz(φ)

Rotation about Z-axis by angle φ (radians).
Rz(φ) = exp(-iφZ/2) = [exp(-iφ/2) 0; 0 exp(iφ/2)]
"""
Rz(φ::Float64) = PrimitiveGate("Rz", [φ], 1)

"""
    CNOT()

Controlled-NOT: control on qubit 1, target on qubit 2 (1-based).
In Yao.jl: `control(2, 1, 2 => X())`
"""
CNOT() = ControlBlock(2, [1], [1], X())

"""
    Toffoli()

Controlled-Controlled-NOT (CCX): controls on qubits 1,2, target on qubit 3.
In Yao.jl: `control(3, (1,2), 3 => X())`
"""
Toffoli() = ControlBlock(3, [1,2], [1,1], X())

# -----------------------------------------------------------------------
# nqubits accessor
# -----------------------------------------------------------------------

"""Return the number of qubits a block acts on."""
nqubits(b::PrimitiveGate) = b.nqubits
nqubits(b::ChainBlock)    = b.nqubits
nqubits(b::KronBlock)     = b.nqubits
nqubits(b::ControlBlock)  = b.nqubits
nqubits(b::PutBlock)      = b.nqubits
nqubits(b::MeasureBlock)  = b.nqubits
