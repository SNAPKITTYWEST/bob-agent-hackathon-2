# Voxel Computational Model
## BURT-IMMA — Quantum Voxel Frontend — Phase 10-12

---

### 1. WHAT IS THE MATHEMATICAL OBJECT?

A voxel in this system is a **typed coordinate in {time, qubit, depth} space**:

```
Voxel = (t ∈ ℕ, q ∈ ℕ, z ∈ ℕ, κ ∈ {1..8})
```

where:
- `t` = gate sequence index (time axis, 0-based, X axis in MagicaVoxel space)
- `q` = qubit index (0-based, Y axis)
- `z` = depth layer (Z axis; currently always 0 for flat circuit layout)
- `κ` = quantum state color index (1–8, encodes the semantic type of the operation at this coordinate)

The coordinate space `{t, q, z}` is a **finite lattice** — a sublattice of ℕ³ bounded by the circuit dimensions. No two distinct ops produce the same `(t, q, z)` coordinate (the lattice is injective under the lowering map, modulo multi-qubit gates which write different `q` values at the same `t`).

The color index `κ` is drawn from a fixed 8-element type algebra:

| κ | Quantum State | Hex Color | Meaning |
|---|---------------|-----------|---------|
| 1 | `\|1⟩` flip  | #e63946   | Pauli-X / Y / Z gate applied (bit flip) |
| 2 | `\|0⟩` reset | #457b9d   | Qubit reset to ground state |
| 3 | Superposition | #f1faee  | Hadamard gate — equal-weight superposition |
| 4 | Gate active   | #ffb703  | Generic unitary (T, S, Rz, Rx, CX control) |
| 5 | Measured      | #2dc653  | Quantum measurement — wavefunction collapsed |
| 6 | Entangled     | #8338ec  | CNOT target — entangled pair |
| 7 | WORM sealed   | #fb5607  | Circuit state immutably sealed (orange override) |
| 8 | Sovereign agent | #00b4d8 | Autonomous agent marker |

---

### 2. WHAT IS ITS REPRESENTATION?

A quantum circuit is represented simultaneously in three forms:

**A. .vox RIFF binary (MagicaVoxel format)**
- 4-byte magic `VOX ` + uint32 version 150
- MAIN chunk containing child chunks:
  - `SIZE`: x, y, z bounding box (uint32 each, little-endian)
  - `XYZI`: count (uint32) + per-voxel [x,y,z,colorIndex] (uint8 each)
  - `RGBA`: 256-entry color palette (4 bytes r,g,b,a each)
- Indices 1–8 in RGBA encode the canonical quantum state colors

**B. QuantumIR JSON**
- Flat sequential op list: `{type, name, qubits, params}` per gate
- Measurement ops: `{type: "measure", qubit, cbit}`
- Metadata: `{source_lang, version, unsupported[]}`
- Resources: `{gate_count, depth, t_count, width}`

**C. Three.js instanced mesh (WebGL2)**
- `THREE.InstancedMesh` — one mesh per color index group
- Each instance: 4×4 transform matrix (position) + material color
- Rendered in a single draw call per color group for performance
- Color-per-instance via `MeshStandardMaterial` with `emissive` tint

---

### 3. WHAT OPERATIONS ARE VALID?

On the voxel lattice, exactly three operations are defined:

1. **Gate mapping**: `gate(name, qubits) → voxel(t, q, z=0, κ)`
   - Maps gate semantics to a color index per qubit role (control/target/solo)
   - Barrier gates are **excluded** (no voxel emitted)

2. **Measurement collapse**: `measure(qubit) → voxel(t, qubit, z=0, κ=5)`
   - A measurement collapses the qubit to a classical outcome
   - The voxel at this coordinate is permanently colored green (κ=5)
   - WORM sealed variant: κ=7 (orange)

3. **Entanglement marking**: `CX(control, target) → voxel(t, control, 0, κ=4) + voxel(t, target, 0, κ=6)`
   - CNOT writes two voxels at the same time step on different qubits
   - Control = gold (κ=4), target = purple (κ=6) to visually encode the pair

The following operations are **explicitly NOT valid on voxels**:
- Reading a voxel back as classical control (no classical feedback loop in .vox)
- Writing two voxels at the same `(t, q, z)` coordinate (position is unique per qubit per time step)
- Modifying a voxel after emission (voxels are write-once — they model WORM semantics)

---

### 4. WHAT INVARIANTS MUST HOLD?

Four structural invariants are enforced by the lowering pass and tested by the test suite:

1. **Color index validity**: `κ ∈ {1..8}` for every emitted voxel. Index 0 is reserved for empty/transparent and must never appear in XYZI.

2. **No voxel at barrier position**: Barrier ops do not advance the time counter and emit no voxel. ∀ barrier op: `|voxels at (t_barrier, *, *)| = 0`.

3. **Time axis monotonically non-decreasing**: The sequence of emitted voxels is produced in time order. `t(voxel_i) ≤ t(voxel_{i+1})` for all `i` (except multi-qubit gates which share `t` across their qubits at the same time step).

4. **Palette identity**: The RGBA chunk at indices 1–8 must exactly match the canonical quantum state color table. Any consumer (MagicaVoxel, Three.js, Metal shader) may rely on this mapping being stable across all QIR sources.

Additional invariant for cross-language equivalence:
- The Bell state QIR from all three language agents (quipper, guppy, yao) must produce **identical voxel output**: 5 voxels at the same `(x, y, z, colorIndex)` positions. The emitter is the single source of truth for this mapping.

---

### 5. HOW IS IT LOWERED?

The lowering pipeline is:

```
[Source Language]              [Toolchain Step]                [Output]
─────────────────────────────────────────────────────────────────────────
Quipper (Haskell)      ─→  ir/ToJSON.hs              ─→  QIR JSON
Guppy   (Python sim)   ─→  guppy/guppy_to_ir.py      ─→  QIR JSON
Yao.jl  (Julia sim)    ─→  yao_jl/src/yao_to_ir.jl   ─→  QIR JSON
                                      ↓
                       voxel/emitter/qir_to_vox.py
                       (Python, single pass over ops[])
                                      ↓
                         .vox binary (MagicaVoxel format)
                         Three.js JSON (instanced mesh data)
                         C# stream (chunk packets via TCP)
                         Metal/Swift (GPU voxel instances)
```

The lowering pass (`qir_to_vox.py`) is a **single-pass, stateless** scan:
1. Read `ops[]` in order
2. For each non-barrier op, assign `t = current_time_step`
3. Map op type + gate name → color index κ
4. Emit voxel `(t, qubit, 0, κ)`
5. Advance `t`

No backtracking, no lookahead, no circuit transformation.

---

### 6. HOW IS IT TESTED?

**Python emitter (pytest):**
- `voxel/emitter/tests/test_emitter.py` — 34 tests, 34 passing
- Bell state: 5-voxel count, correct positions, correct colors
- Palette: 256 entries, indices 1–8 exact match
- Magic bytes: `b"VOX "` prefix, version 150
- SIZE chunk: reflects qubit/time-step bounding box
- WORM sealed: color 7 override
- Barrier skip: no voxel, no time advance
- Reset: color 2 (blue)
- Schema key compatibility: both `"type"` and `"op"` keys accepted

**Visual verification:**
- Open `voxel/frontend/index.html` in a WebGL2-capable browser
- Bell state renders: 1 white voxel (H), 2 voxels at step 1 (gold control + purple target), 2 green voxels (measurements)
- MagicaVoxel: open any emitted `.vox` file to verify palette and voxel positions

**Cross-language equivalence:**
- Run emitter against all three Bell state demo files:
  `voxel/demo/bell_state_quipper.json`, `bell_state_guppy.json`, `bell_state_yao.json`
- All three must produce identical 5-voxel output

---

### 7. WHAT INFORMATION IS LOST?

The following quantum information is **deliberately dropped** during voxel lowering (documented per the QuantumIR `unsupported` convention):

1. **Gate rotation parameters**: `Rz(θ)`, `Rx(θ)`, `Ry(θ)` angles are collapsed to a single color index (κ=4, gold). The value of θ is not encoded spatially. A 90° and a 1° rotation look identical in the voxel representation.

2. **Classical control flow**: Measurement outcomes that conditionally control subsequent gates (dynamic lifting / mid-circuit feedback) are not spatially encoded. The voxel model is a static snapshot of the gate sequence, not a dynamic execution trace.

3. **Gate parallelism**: Operations on disjoint qubits that could execute simultaneously (e.g., in a KronBlock in Yao.jl) are serialized into sequential time steps. The spatial separation in X is an artifact of serialization, not necessarily a causal dependency.

4. **Phase information**: Global and relative phases are not represented. A Z gate (κ=1) and a T gate (κ=4) look different in color, but the continuous phase of a Rz(φ) is lost.

5. **Higher-order circuit structure**: Quipper's BoxedCircuit, Guppy's HUGR graph structure, and Yao.jl's ChainBlock nesting are all flattened to a linear op sequence before reaching the voxel emitter.

---

### 8. WHAT BACKEND ASSUMPTIONS EXIST?

**MagicaVoxel (.vox binary):**
- Palette is limited to 256 colors. The quantum model uses 8 (indices 1–8), leaving 247 slots for future extension.
- Voxel coordinates are uint8 — maximum bounding box is 255×255×255. For circuits with more than 255 qubits or 255 time steps, the emitter must chunk the output.
- Version 150 is assumed. MagicaVoxel versions prior to 0.98.1 may not parse RGBA chunks correctly.

**Three.js (Web frontend):**
- Requires WebGL2. WebGL1 does not support `InstancedMesh` with per-instance color attributes in all configurations.
- Import maps require a modern browser (Chrome 89+, Firefox 108+, Safari 16.4+).
- No build step — the single HTML file uses `<script type="importmap">` to resolve Three.js from unpkg.com at CDN version 0.160.0.

**Metal (native iOS/macOS viewer):**
- Requires Apple Silicon or Intel Mac with Metal support (macOS 10.11+ for Intel, all Apple Silicon).
- `MTLCreateSystemDefaultDevice()` returns `nil` on devices without Metal; the viewer will fatal-error gracefully.
- The MSL shader targets Metal 2.0 feature set. Metal 1.x devices (pre-A9) are not supported.
- No physical QPU execution is claimed or implied by this viewer. All circuit data is pre-compiled QIR.

**C# streaming server:**
- Requires .NET 6+ for `System.Text.Json` and `System.Net.Sockets` async APIs.
- ChunkPacket is serialized with `StructLayout(Pack=1)` — assumes little-endian host (all modern x86/ARM platforms).
- Maximum chunk coordinate: Int32 range. For circuits that fit in a single 32×32×32 chunk (all current Bell state demos), no chunking is needed.
