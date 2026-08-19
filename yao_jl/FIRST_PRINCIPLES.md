# First Principles — Yao.jl Quantum Circuit Model

This document answers eight foundational questions about the mathematical
object we are building, how we represent it, and what we guarantee.

---

## WHAT IS THE MATHEMATICAL OBJECT?

A **quantum circuit** is a finite sequence of quantum operations on a register
of n two-level quantum systems (qubits). Mathematically it is:

1. **A Hilbert space**: H = ℂ^{2^n} — the state space of n qubits
2. **A pure state**: a unit vector |ψ⟩ ∈ H, |ψ⟩ normalized: ⟨ψ|ψ⟩ = 1
3. **A circuit**: a composition of unitary operators U = U_d · U_{d-1} · ... · U_1, each U_i ∈ U(2^n)
4. **Measurement**: a set of projection operators {P_k = |k⟩⟨k|} in the computational basis, collapsing |ψ⟩ to |k⟩ with probability |⟨k|ψ⟩|²

The circuit computes |ψ_out⟩ = U|ψ_in⟩, where |ψ_in⟩ = |0...0⟩ by convention.

In Yao.jl's framework specifically, circuits are **block trees** — a recursive
composition algebra where blocks are the primitive elements. This is not just a
flat list of gates but a structured, composable intermediate representation.

---

## WHAT IS ITS REPRESENTATION?

### Source representation (Yao.jl block tree)

A circuit is represented as a tree of `AbstractBlock` subtypes:

```
AbstractBlock
├── PrimitiveGate       — leaf node: named gate + parameters
├── ChainBlock          — sequential composition (left-to-right)
├── KronBlock           — parallel composition (disjoint qubits)
├── ControlBlock        — conditional gate (control qubits + target block)
├── PutBlock            — location injection (places block at specific qubits)
└── MeasureBlock        — measurement (collapse to computational basis)
```

This tree IS the circuit. There is no separate AST — the Julia struct tree
serves as the program representation.

### Target representation (QuantumIR JSON)

A flat, sequential list of operations:
- `gate` ops: name, params (radians), qubit indices (0-based)
- `measure` ops: qubit, cbit
- `barrier` ops: synchronization markers
- `reset` ops: qubit reset to |0⟩

QuantumIR is **less expressive** than the block tree — it cannot represent
parallelism, nesting, or AD metadata. This is an intentional design choice:
QIR is an interchange format, not a full IR.

### Simulation representation (statevector)

The quantum state is a `Vector{ComplexF64}` of length 2^n. Index k represents
basis state |k⟩ in big-endian binary encoding. Each gate application is a
dense matrix-vector multiplication. This is O(4^n) per gate operation.

---

## WHAT OPERATIONS ARE VALID?

### On the block tree

- `chain(n, b1, b2, ...)` — sequential composition (all blocks must act on n qubits)
- `kron(n, i=>b1, j=>b2, ...)` — parallel composition (locs must be disjoint)
- `control(n, ctrl_locs, target)` — conditional gate (ctrl_locs ∩ target_locs = ∅)
- `put(n, locs, b)` — location injection (length(locs) == nqubits(b))
- `measure(n, locs)` — measurement (locs ⊆ 1:n)

### On the statevector

- `apply_block(state, block, nq)` — apply a block to a statevector
- `simulate(circuit)` — full simulation from |0⟩^n
- Composition of unitary operations preserves normalization: ∑|αk|² = 1

### On the QIR JSON

- Gates: any name in the gate dictionary, with matching parameter count
- Measurements: qubit index in [0, qubits-1], cbit index in [0, cbits-1]
- Ops are ordered: the sequence IS the execution order

---

## WHAT INVARIANTS MUST HOLD?

### Structural invariants (block tree)

1. **Qubit count consistency**: for every PutBlock(n, locs, b), length(locs) == nqubits(b)
2. **KronBlock disjointness**: all `locs` in a KronBlock must be distinct
3. **Control-target disjointness**: ctrl_locs ∩ target_locs == ∅
4. **Qubit bounds**: all qubit indices in [1, nqubits(parent)]

### Simulation invariants (statevector)

5. **Normalization**: ∑|αk|² = 1 throughout (within floating-point tolerance ~1e-10)
6. **Unitarity**: each gate matrix U satisfies U†U = I (checked via GATE_MATRIX)
7. **Dimension**: statevector length = 2^n where n = nqubits(circuit)

### QIR invariants (IR output)

8. **Explicit unsupported list**: `metadata.unsupported` is NEVER empty — every lowering includes at least the three canonical semantic gaps
9. **Qubit bounds**: all op qubit indices in [0, ir["qubits"]-1]
10. **Cbit bounds**: all measure cbit indices in [0, ir["cbits"]-1]
11. **Version match**: `version` == `metadata.version` == "0.1.0"

---

## HOW IS IT LOWERED?

The lowering is a recursive tree walk: `yao_to_ir(circuit)` calls `lower_block!`
on the circuit root, which dispatches on block type:

```
ChainBlock  → iterate sub-blocks in order (sequential semantics preserved)
KronBlock   → iterate (loc, block) pairs in order (PARALLEL → SEQUENTIAL loss)
PutBlock    → recurse with explicit qubit location context
ControlBlock → emit CX/CCX/C-<name> gate with ctrl+target qubit list
MeasureBlock → emit measure ops with incrementing cbit counter
PrimitiveGate → emit gate op with name, params, qubit locs (0-based)
```

Resource analysis is post-pass over the flat op list:
- `gate_count`: count ops of type "gate"
- `depth`: critical-path depth using per-qubit layer tracking
- `t_count`: count ops whose name is "T" or equivalent (Tdg, T†)
- `width`: n (all qubits active)

Qubit index conversion: Yao.jl uses 1-based, QIR uses 0-based. All locs are
decremented by 1 exactly once at the point of IR op construction.

---

## HOW IS IT TESTED?

The test suite (`test/test_yao.jl`) verifies:

1. **Type construction**: all struct constructors produce correct field values
2. **nqubits accessor**: correct for all block types
3. **Circuit construction**: chain, kron, put, control, measure builder functions
4. **Bell state amplitudes**: |00⟩ and |11⟩ coefficients are exactly 1/√2 ± 1e-10
5. **Gate matrix algebra**: H² = I, X² = I, T^8 = I, Rx(0) = I, Rz(π) = -iZ
6. **Normalization invariant**: ∑|αk|² = 1 ± 1e-10 after any circuit
7. **QIR schema**: Bell state IR has correct source_lang, qubits, cbits, op count
8. **Unsupported non-empty**: every IR output has at least 3 unsupported items
9. **QFT T-count**: QFT3 resource analysis produces non-negative t_count
10. **Resources structure**: all four resource fields present and non-negative
11. **JSON serialization**: output is a string containing required field names

Tests use Julia's built-in `Test.jl` stdlib with `@test`, `@testset`, `@test_throws`.

---

## WHAT INFORMATION IS LOST?

When lowering from Yao.jl block tree to QuantumIR JSON:

1. **Parallelism (KronBlock)**: KronBlock's simultaneous application is serialized. A circuit that could execute in depth D with parallel single-qubit gates becomes depth D' ≥ D in QIR. This is a **semantic loss**.

2. **Automatic differentiation metadata**: Yao.jl supports differentiating through circuits via ChainRules.jl and Zygote.jl. Rotation angles (Rx, Rz parameters) can be differentiated. QIR v0.1 has no gradient or AD metadata fields. This is a **capability loss**.

3. **Block nesting structure**: ChainBlock of ChainBlocks is flattened to a single linear op sequence. The hierarchical composition algebra is lost. Sub-circuit identity (e.g., a named QFT sub-circuit) is erased. This is a **structural loss**.

4. **Global phase**: QIR gate names are phase-canonical (T vs. Rz(π/4) differ by global phase). The IR records the gate name, not the matrix, so global phase differences between equivalent descriptions are implicit.

5. **Measurement semantics**: Yao.jl supports various measurement modes (total, partial, density matrix). QIR measure ops only capture computational-basis collapse. Shot-based sampling and mid-circuit measurement feedback are not representable.

These losses are **always declared** in `metadata.unsupported`. They are never silently omitted.

---

## WHAT BACKEND ASSUMPTIONS EXIST?

### In the simulation layer (`yao_simulation.jl`)

1. **Dense statevector**: we allocate 2^n complex numbers. For n > 25 this exceeds typical RAM. The simulation does not use sparse representations, tensor network methods, or GPU acceleration.

2. **Exact arithmetic**: all amplitudes are `ComplexF64` (64-bit IEEE 754 complex). There is no noise model, no decoherence, no shot noise. The simulation is **ideal**.

3. **Big-endian qubit ordering**: qubit 1 is the MSB. This matches Yao.jl's default convention. Some other frameworks (Qiskit) use little-endian. Cross-framework comparisons must account for this.

4. **No mid-circuit measurement feedback**: MeasureBlock is a no-op in simulation. Classical control flow conditioned on mid-circuit measurement results is not implemented.

### In the QIR lowering layer (`yao_to_ir.jl`)

5. **Gate name completeness**: if a gate name is not in `YAO_TO_IR_NAME`, it is passed through unchanged. Unknown gate names in the IR may not be recognized by downstream consumers.

6. **Control-on-|1⟩ only**: ControlBlock defaults to control bit value 1. Control on |0⟩ (anti-control) is not emitted as a distinct QIR op type.

7. **QIR version 0.1.0 only**: the schema and lowering target version 0.1.0. Future QIR versions with different field names or op types will require a new lowering pass.

8. **No circuit optimization**: the lowering is a faithful 1-to-1 translation. No gate cancellation, commutation rewriting, or basis translation is performed.
