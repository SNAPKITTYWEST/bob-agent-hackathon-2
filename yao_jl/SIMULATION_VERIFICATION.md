# Simulation Verification — Yao.jl Model

**CRITICAL DECLARATION:**
This is **statevector simulation on classical hardware**. No QPU. No quantum hardware.
All computation is dense matrix-vector multiplication on CPU using `ComplexF64` arithmetic.

---

## Matrix Operations Used

### Single-Qubit Gate Matrices (2×2, ComplexF64)

All gates are represented as unitary 2×2 matrices over ℂ:

```
H = (1/√2) * [ 1   1 ]
              [ 1  -1 ]

X = [ 0  1 ]    Y = [ 0  -i ]    Z = [ 1   0 ]
    [ 1  0 ]        [ i   0 ]        [ 0  -1 ]

T = [ 1       0       ]    S = [ 1  0 ]
    [ 0  e^{iπ/4}     ]        [ 0  i ]

Rx(θ) = [ cos(θ/2)      -i·sin(θ/2) ]
        [ -i·sin(θ/2)    cos(θ/2)   ]

Ry(θ) = [ cos(θ/2)   -sin(θ/2) ]
        [ sin(θ/2)    cos(θ/2) ]

Rz(φ) = [ e^{-iφ/2}   0        ]
        [ 0            e^{iφ/2} ]
```

### Tensor Product Embedding

A single-qubit gate G applied to qubit k of an n-qubit register is embedded as:

```
M_k = I_{2^{k-1}} ⊗ G ⊗ I_{2^{n-k}}
```

where ⊗ is the Kronecker product and I_{2^j} is the 2^j × 2^j identity matrix.

This produces a 2^n × 2^n unitary that acts as G on qubit k and as identity on all others.

### Controlled Gate Construction

For a controlled-U gate with controls C = {c₁, c₂, ...} and target qubit t:

The 2^n × 2^n matrix is constructed by iterating over all basis states:
- For each basis state |b⟩ where all control qubits are 1: apply U to the target qubit amplitude
- For all other basis states: pass through unchanged (identity)

This implements: U_ctrl = Π_k |0⟩⟨0|_{c_k} ⊗ I_t + Π_k |1⟩⟨1|_{c_k} ⊗ U_t

---

## Bell State Verification

### Initial State

```
|ψ₀⟩ = |00⟩ = [1, 0, 0, 0]^T   (basis ordering: |00⟩, |01⟩, |10⟩, |11⟩)
```

### Step 1: Apply H ⊗ I to |00⟩

H ⊗ I is the 4×4 matrix:

```
H ⊗ I = (1/√2) [ 1  0  1  0 ]
                [ 0  1  0  1 ]
                [ 1  0 -1  0 ]
                [ 0  1  0 -1 ]
```

Applied to |00⟩ = [1, 0, 0, 0]^T:

```
(H ⊗ I)|00⟩ = (1/√2)[1, 0, 1, 0]^T
             = (1/√2)(|00⟩ + |10⟩)
             = (|0⟩ + |1⟩)/√2 ⊗ |0⟩
```

Intermediate statevector after H:
- |00⟩: amplitude = +1/√2 ≈ +0.707107
- |01⟩: amplitude = 0
- |10⟩: amplitude = +1/√2 ≈ +0.707107
- |11⟩: amplitude = 0

### Step 2: Apply CNOT (ctrl=q1, tgt=q2)

CNOT matrix (in the |00⟩,|01⟩,|10⟩,|11⟩ basis, ctrl = qubit 1 = MSB):

```
CNOT = [ 1  0  0  0 ]
       [ 0  1  0  0 ]
       [ 0  0  0  1 ]
       [ 0  0  1  0 ]
```

Applied to (1/√2)[1, 0, 1, 0]^T:

```
CNOT · (1/√2)[1, 0, 1, 0]^T = (1/√2)[1, 0, 0, 1]^T
```

### Final Bell State

```
|Φ+⟩ = (|00⟩ + |11⟩) / √2 = (1/√2)[1, 0, 0, 1]^T
```

Amplitudes:
- |00⟩: α₀₀ = 1/√2 ≈ 0.707107,   |α₀₀|² = 0.5
- |01⟩: α₀₁ = 0,                  |α₀₁|² = 0.0
- |10⟩: α₁₀ = 0,                  |α₁₀|² = 0.0
- |11⟩: α₁₁ = 1/√2 ≈ 0.707107,   |α₁₁|² = 0.5

Normalization: |α₀₀|² + |α₀₁|² + |α₁₀|² + |α₁₁|² = 0.5 + 0 + 0 + 0.5 = 1.0 ✓

---

## What This Simulation Is NOT

1. **Not a QPU**: No quantum hardware is involved. All operations are floating-point matrix multiplications on CPU.
2. **Not sampling**: The full statevector is maintained. Measurement in `MeasureBlock` is a no-op in this simulation layer (state not collapsed).
3. **Not fault-tolerant**: No error correction. Amplitudes are exact (up to floating-point precision).
4. **Not scalable**: Memory is O(2^n) and runtime is O(4^n) for dense matrix operations. Practical limit ≈ 25 qubits on a laptop.
5. **Not the real Yao.jl**: The actual Yao.jl library uses efficient sparse representations, AD through circuits, GPU acceleration, and the full Julia type system. This models its API surface only.

---

## Qubit Index Convention

- **Yao.jl model**: 1-based qubit indices (Julia convention)
- **QuantumIR / QIR JSON**: 0-based qubit indices (C/Python convention)
- **Statevector**: big-endian bit ordering — qubit 1 is the most significant bit
  - Basis state |b_{n-1}...b_1 b_0⟩ maps to index k = Σ b_j · 2^j

Example for n=2:
```
Index 0 → |00⟩   (q1=0, q2=0)
Index 1 → |01⟩   (q1=0, q2=1)
Index 2 → |10⟩   (q1=1, q2=0)
Index 3 → |11⟩   (q1=1, q2=1)
```
