# yao_circuit.jl
#
# Circuit construction helpers — mirrors Yao.jl's builder API.
#
# In real Yao.jl these are high-level constructors with extensive type
# dispatch. Here we provide the same API surface over our struct hierarchy.

include("yao_types.jl")

# -----------------------------------------------------------------------
# chain: sequential composition
# -----------------------------------------------------------------------

"""
    chain(nqubits, blocks...)

Compose blocks sequentially on a `nqubits`-qubit register.
Each block is applied to the full register in the order given.

Yao.jl equivalent: `chain(n, gate1, gate2, ...)`

# Example
```julia
circuit = chain(2, put(2, [1], H()), control(2, [1], X()))
```
"""
function chain(nq::Int, blocks::AbstractBlock...)::ChainBlock
    return ChainBlock(nq, collect(AbstractBlock, blocks))
end

# Variadic version accepting a Vector
function chain(nq::Int, blocks::Vector{<:AbstractBlock})::ChainBlock
    return ChainBlock(nq, Vector{AbstractBlock}(blocks))
end

# -----------------------------------------------------------------------
# kron: parallel composition
# -----------------------------------------------------------------------

"""
    kron(nqubits, pairs...)

Apply blocks in parallel to disjoint qubit subsets.
Each `pair` is `loc => block` where `loc` is the 1-based starting qubit.

Yao.jl equivalent: `kron(n, 1 => H(), 2 => X(), ...)`

# Example
```julia
layer = kron(3, 1 => H(), 2 => X(), 3 => Z())
```
"""
function kron(nq::Int, pairs::Pair{Int,<:AbstractBlock}...)::KronBlock
    locs   = Int[p.first for p in pairs]
    blocks = AbstractBlock[p.second for p in pairs]
    return KronBlock(nq, locs, blocks)
end

# -----------------------------------------------------------------------
# control: add control lines to a target block
# -----------------------------------------------------------------------

"""
    control(nqubits, ctrl_locs, target_loc => target_block)

Create a ControlBlock that applies `target_block` on `target_loc` when
all control qubits in `ctrl_locs` are 1.

Yao.jl equivalent: `control(n, ctrl_locs, target_loc => gate)`

# Examples
```julia
# CNOT: control q1, target q2
cx = control(2, [1], 2 => X())

# Toffoli: controls q1,q2, target q3
ccx = control(3, [1,2], 3 => X())
```
"""
function control(nq::Int, ctrl_locs::Vector{Int}, target::Pair{Int,<:AbstractBlock})::ControlBlock
    ctrl_bits = ones(Int, length(ctrl_locs))  # default: control on |1⟩
    # Wrap target in PutBlock so location is encoded
    tgt_block = put(nq, [target.first], target.second)
    return ControlBlock(nq, ctrl_locs, ctrl_bits, tgt_block)
end

"""
    control(nqubits, ctrl_locs, target_block)

Simplified form when target qubit positions are already embedded in
`target_block` (e.g., a PutBlock or ControlBlock).
"""
function control(nq::Int, ctrl_locs::Vector{Int}, target::AbstractBlock)::ControlBlock
    ctrl_bits = ones(Int, length(ctrl_locs))
    return ControlBlock(nq, ctrl_locs, ctrl_bits, target)
end

# -----------------------------------------------------------------------
# put: locate a block inside a larger register
# -----------------------------------------------------------------------

"""
    put(nqubits, locs, block)

Place `block` at qubit positions `locs` inside an `nqubits`-qubit register.
`locs` are 1-based. `length(locs)` must equal `nqubits(block)`.

Yao.jl equivalent: `put(n, locs => block)`

# Example
```julia
# Place H on qubit 1 inside a 3-qubit register
put(3, [1], H())
```
"""
function put(nq::Int, locs::Vector{Int}, block::AbstractBlock)::PutBlock
    if length(locs) != nqubits(block)
        error("put: locs length ($(length(locs))) must equal nqubits(block) ($(nqubits(block)))")
    end
    return PutBlock(nq, locs, block)
end

# -----------------------------------------------------------------------
# measure: create a measurement block
# -----------------------------------------------------------------------

"""
    measure(nqubits, locs)

Measure qubits at `locs` (1-based) inside an `nqubits`-qubit register.

Yao.jl equivalent: `Measure(n, locs=locs)`

# Example
```julia
m = measure(2, [1, 2])
```
"""
function measure(nq::Int, locs::Vector{Int})::MeasureBlock
    return MeasureBlock(nq, locs)
end

# -----------------------------------------------------------------------
# Utility: nqubits is already defined in yao_types.jl (exported here)
# -----------------------------------------------------------------------

# Re-export for users who include yao_circuit.jl directly
export chain, kron, control, put, measure, nqubits
export AbstractBlock, PrimitiveGate, ChainBlock, KronBlock
export ControlBlock, PutBlock, MeasureBlock
export H, X, Y, Z, T, S, Rx, Ry, Rz, CNOT, Toffoli
