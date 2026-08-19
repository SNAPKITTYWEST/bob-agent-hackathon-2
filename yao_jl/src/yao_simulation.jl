# yao_simulation.jl
#
# Statevector simulation of Yao.jl block circuits.
#
# This is CLASSICAL SIMULATION on CPU via dense linear algebra.
# No QPU, no quantum hardware, no sampling — purely matrix math.
#
# Mathematical basis:
#   - A pure quantum state on n qubits lives in ℂ^(2^n)
#   - A gate acting on qubit k is represented as:
#       I_0 ⊗ ... ⊗ G_k ⊗ ... ⊗ I_{n-1}   (tensor product)
#   - Circuit application is sequential matrix-vector multiplication
#   - Initial state: |0⟩^n = e_0 in ℂ^(2^n)
#
# Convention: qubit ordering is big-endian (qubit 1 = most significant bit).
# Basis state |b_{n-1}...b_1 b_0⟩ maps to index sum(b_k * 2^k).

include("yao_types.jl")

using LinearAlgebra

# -----------------------------------------------------------------------
# 2×2 gate matrices (ComplexF64)
# -----------------------------------------------------------------------

const INV_SQRT2 = 1.0 / sqrt(2.0)

"""Standard 2×2 gate matrices keyed by name."""
const GATE_MATRIX = Dict{String, Matrix{ComplexF64}}(
    "H" => ComplexF64[INV_SQRT2  INV_SQRT2;
                      INV_SQRT2 -INV_SQRT2],
    "X" => ComplexF64[0 1; 1 0],
    "Y" => ComplexF64[0 -1im; 1im 0],
    "Z" => ComplexF64[1 0; 0 -1],
    "T" => ComplexF64[1 0; 0 exp(1im*π/4)],
    "S" => ComplexF64[1 0; 0 1im],
    "I" => ComplexF64[1 0; 0 1],
)

"""
    gate_matrix(g::PrimitiveGate)

Return the 2^k × 2^k unitary matrix for gate `g` (k = g.nqubits).
Parameterized gates (Rx, Ry, Rz) are constructed from the parameter.
"""
function gate_matrix(g::PrimitiveGate)::Matrix{ComplexF64}
    if g.name == "Rx"
        θ = g.params[1]
        return ComplexF64[cos(θ/2) -1im*sin(θ/2);
                         -1im*sin(θ/2) cos(θ/2)]
    elseif g.name == "Ry"
        θ = g.params[1]
        return ComplexF64[cos(θ/2)  -sin(θ/2);
                          sin(θ/2)   cos(θ/2)]
    elseif g.name == "Rz"
        φ = g.params[1]
        return ComplexF64[exp(-1im*φ/2) 0;
                          0 exp(1im*φ/2)]
    elseif haskey(GATE_MATRIX, g.name)
        return GATE_MATRIX[g.name]
    else
        error("Unknown gate: $(g.name) — add it to GATE_MATRIX or gate_matrix()")
    end
end

# -----------------------------------------------------------------------
# Tensor product embedding of a single-qubit gate
# -----------------------------------------------------------------------

"""
    embed_gate(U::Matrix{ComplexF64}, qubit::Int, nq::Int)

Build the 2^nq × 2^nq matrix for gate U acting on `qubit` (1-based)
within an `nq`-qubit register via Kronecker products.

For qubit k (1-based):
  M = I_{2^(k-1)} ⊗ U ⊗ I_{2^(nq-k)}
"""
function embed_gate(U::Matrix{ComplexF64}, qubit::Int, nq::Int)::Matrix{ComplexF64}
    @assert 1 <= qubit <= nq "qubit index $qubit out of range [1,$nq]"
    I2 = ComplexF64[1 0; 0 1]
    # Build left side: I ⊗ I ⊗ ... (qubit-1 times)
    left  = (qubit > 1) ? foldl(kron, (I2 for _ in 1:(qubit-1))) : Matrix{ComplexF64}(I, 1, 1)
    # Build right side: I ⊗ I ⊗ ... (nq-qubit times)
    right = (qubit < nq) ? foldl(kron, (I2 for _ in 1:(nq-qubit))) : Matrix{ComplexF64}(I, 1, 1)
    return kron(kron(left, U), right)
end

# -----------------------------------------------------------------------
# Controlled-gate embedding
# -----------------------------------------------------------------------

"""
    embed_controlled_gate(ctrl_qubits, target_qubit, U, nq)

Build the 2^nq × 2^nq unitary for U applied to `target_qubit` controlled
on each qubit in `ctrl_qubits` being in state |1⟩.

Uses projector decomposition:
  C-U = |0⟩⟨0| ⊗ I + |1⟩⟨1| ⊗ U    (for single control)
Extended iteratively for multiple controls.
"""
function embed_controlled_gate(
    ctrl_qubits::Vector{Int},
    target_qubit::Int,
    U::Matrix{ComplexF64},
    nq::Int
)::Matrix{ComplexF64}

    dim = 2^nq
    # Start with full identity
    result = Matrix{ComplexF64}(I, dim, dim)

    # Build the controlled unitary projector-by-projector.
    # For a single control c and target t, the 2-qubit CU is:
    #   |0⟩⟨0|_c ⊗ I_t  +  |1⟩⟨1|_c ⊗ U_t
    # For multiple controls (c1, c2, ...) we project onto |11...1⟩ subspace.
    #
    # Implementation: iterate over all 2^nq basis states. For those where
    # all control qubits are 1, apply U to the target qubit.

    I2 = ComplexF64[1 0; 0 1]

    # Build "all controls off" matrix: identity on full space
    M = zeros(ComplexF64, dim, dim)

    for basis_in in 0:(dim-1)
        # Check if all ctrl qubits are 1 for this basis state
        # Qubit k (1-based) is at bit position (nq - k) in big-endian convention
        all_ctrl_one = all(
            (basis_in >> (nq - c)) & 1 == 1 for c in ctrl_qubits
        )

        if all_ctrl_one
            # Extract target qubit state
            tgt_bit = (basis_in >> (nq - target_qubit)) & 1
            tgt_mask = 1 << (nq - target_qubit)
            # Apply U to target qubit: sum over target output states
            for tgt_out in 0:1
                coeff = U[tgt_out+1, tgt_bit+1]
                if abs(coeff) > 1e-15
                    basis_out = (basis_in & ~tgt_mask) | (tgt_out << (nq - target_qubit))
                    M[basis_out+1, basis_in+1] += coeff
                end
            end
        else
            # Pass through unchanged
            M[basis_in+1, basis_in+1] += 1.0
        end
    end

    return M
end

# -----------------------------------------------------------------------
# State application
# -----------------------------------------------------------------------

"""
    apply_primitive(state, gate, locs, nq)

Apply a PrimitiveGate to the statevector `state` on the qubits in `locs`.
For 1-qubit gates: use embed_gate.
For 2-qubit primitives (CX etc.): specialized handling.
"""
function apply_primitive(
    state::Vector{ComplexF64},
    gate::PrimitiveGate,
    locs::Vector{Int},
    nq::Int
)::Vector{ComplexF64}
    U = gate_matrix(gate)
    if gate.nqubits == 1
        M = embed_gate(U, locs[1], nq)
        return M * state
    else
        error("apply_primitive: multi-qubit PrimitiveGate $(gate.name) not directly supported; use ControlBlock instead")
    end
end

"""
    apply_block(state, block, nq)

Recursively apply a block tree to a statevector of `nq` qubits.
Returns the updated statevector.
"""
function apply_block(state::Vector{ComplexF64}, block::AbstractBlock, nq::Int)::Vector{ComplexF64}
    if isa(block, PrimitiveGate)
        # Bare primitive without location context — assume qubit 1
        locs = collect(1:block.nqubits)
        return apply_primitive(state, block, locs, nq)

    elseif isa(block, PutBlock)
        # Apply the inner block to the specified locations
        inner = block.block
        if isa(inner, PrimitiveGate)
            return apply_primitive(state, inner, block.locs, nq)
        else
            return apply_block(state, inner, nq)
        end

    elseif isa(block, ChainBlock)
        # Sequential: apply each sub-block in order
        s = state
        for b in block.blocks
            s = apply_block(s, b, nq)
        end
        return s

    elseif isa(block, KronBlock)
        # Parallel: apply each sub-block to its designated qubits
        # (Order doesn't matter for disjoint qubits, but we serialize)
        s = state
        for (loc, b) in zip(block.locs, block.blocks)
            if isa(b, PrimitiveGate)
                locs = collect(loc : loc + b.nqubits - 1)
                s = apply_primitive(s, b, locs, nq)
            else
                s = apply_block(s, b, nq)
            end
        end
        return s

    elseif isa(block, ControlBlock)
        # Controlled block: find control qubits and target
        ctrl_locs = block.ctrl_locs
        inner     = block.block

        if isa(inner, PutBlock)
            # Most common case: PutBlock wrapping a PrimitiveGate
            if isa(inner.block, PrimitiveGate)
                U = gate_matrix(inner.block)
                target_qubit = inner.locs[1]
                M = embed_controlled_gate(ctrl_locs, target_qubit, U, nq)
                return M * state
            else
                error("ControlBlock with non-primitive inner PutBlock not yet supported")
            end
        elseif isa(inner, PrimitiveGate)
            # Fallback: apply controlled gate assuming target follows controls
            U = gate_matrix(inner)
            target_qubit = maximum(ctrl_locs) + 1
            M = embed_controlled_gate(ctrl_locs, target_qubit, U, nq)
            return M * state
        else
            error("ControlBlock inner block type $(typeof(inner)) not yet supported")
        end

    elseif isa(block, MeasureBlock)
        # Measurement is a no-op in statevector simulation
        # (Collapse not implemented — full state is preserved for analysis)
        @warn "MeasureBlock encountered during statevector simulation — state not collapsed (use sample() for measurement outcomes)"
        return state

    else
        error("apply_block: unsupported block type $(typeof(block))")
    end
end

# -----------------------------------------------------------------------
# Top-level simulate
# -----------------------------------------------------------------------

"""
    simulate(circuit::ChainBlock) -> Vector{ComplexF64}

Simulate the full circuit starting from |0⟩^n state.
Returns the final statevector of length 2^n.

This is CLASSICAL STATEVECTOR SIMULATION — O(4^n) memory, O(8^n) time
for dense matrix ops. No QPU execution. No sampling.

# Example
```julia
circuit = chain(2, put(2,[1],H()), control(2,[1],2=>X()))
sv = simulate(circuit)
# sv ≈ [1/√2, 0, 0, 1/√2] for Bell state (|00⟩+|11⟩)/√2
```
"""
function simulate(circuit::ChainBlock)::Vector{ComplexF64}
    nq  = circuit.nqubits
    dim = 2^nq
    # Initial state |0...0⟩
    state = zeros(ComplexF64, dim)
    state[1] = 1.0 + 0.0im
    # Apply the circuit
    return apply_block(state, circuit, nq)
end

"""
    zero_state(nq::Int) -> Vector{ComplexF64}

Return the |0⟩^n statevector (length 2^n, first element = 1).
"""
function zero_state(nq::Int)::Vector{ComplexF64}
    s = zeros(ComplexF64, 2^nq)
    s[1] = 1.0 + 0.0im
    return s
end

"""
    statevec_to_probabilities(sv::Vector{ComplexF64}) -> Vector{Float64}

Convert statevector amplitudes to measurement probabilities.
P(k) = |sv[k]|^2, normalized so sum = 1.
"""
function statevec_to_probabilities(sv::Vector{ComplexF64})::Vector{Float64}
    probs = abs2.(sv)
    s = sum(probs)
    return probs ./ s
end

"""
    basis_label(k::Int, nq::Int) -> String

Return the computational basis label for index k (0-based) with nq qubits.
Example: basis_label(3, 3) => "|011⟩"
"""
function basis_label(k::Int, nq::Int)::String
    bits = join([((k >> (nq-1-i)) & 1) for i in 0:(nq-1)])
    return "|" * bits * "⟩"
end

"""
    print_statevec(sv::Vector{ComplexF64}, nq::Int; tol=1e-10)

Pretty-print the statevector, skipping near-zero amplitudes.
"""
function print_statevec(sv::Vector{ComplexF64}, nq::Int; tol::Float64=1e-10)
    println("Statevector (nq=$nq, dim=$(length(sv))):")
    for (k, amp) in enumerate(sv)
        if abs(amp) > tol
            re = real(amp)
            im_part = imag(amp)
            lbl = basis_label(k-1, nq)
            if abs(im_part) < tol
                @printf("  %s  amplitude: %+.6f\n", lbl, re)
            else
                @printf("  %s  amplitude: %+.6f %+.6fim\n", lbl, re, im_part)
            end
        end
    end
    println("  Probabilities:")
    for (k, p) in enumerate(statevec_to_probabilities(sv))
        if p > tol
            @printf("  P(%s) = %.6f\n", basis_label(k-1, nq), p)
        end
    end
end

# Load Printf for formatted output
using Printf
