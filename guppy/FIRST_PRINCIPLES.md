# First Principles — Guppy Quantum Frontend

This document answers the eight canonical questions for any component
in the sovereign stack.

---

## 1. WHAT IS THE MATHEMATICAL OBJECT?

A Guppy quantum circuit is a **morphism** in the category of
finite-dimensional Hilbert spaces:

    f : H_{in} -> H_{out}

where H_{in} = C^{2^n} (n input qubits) and H_{out} = C^{2^m} otimes C^2^k
(m output qubits plus k classical bits from measurements).

The circuit is composed of:

- **Unitary gates**: reversible linear maps U : (C^2)^k -> (C^2)^k
  represented by unitary matrices in U(2^k).
- **Measurement**: a completely positive trace-preserving (CPTP) map
  Measure : C^2 -> {0, 1}  that collapses the quantum state and
  produces a classical outcome.
- **State preparation**: the zero state |0...0> in (C^2)^n.

The **linear type system** models the **quantum no-cloning theorem**
(Wootters & Zurek 1982): there is no unitary U such that
U|psi>|0> = |psi>|psi> for all |psi>.  Linearity enforces this
structurally: a qubit variable can appear on the left-hand side of
exactly one consuming expression.

---

## 2. WHAT IS ITS REPRESENTATION?

**In the real Guppy compiler**:
A HUGR graph (Hierarchical Unified Graph Representation).
Nodes = operations.  Edges = data-flow dependencies with linear types.

**In our Python simulation**:
- `GuppyCircuit`: a container holding a list of `GuppyOp` records and
  a list of `QubitRef` handles.
- `QubitRef`: a Python object with an `id` (integer qubit index) and a
  `_consumed` boolean flag.
- `GuppyOp`: a record of (op_type, name, qubit_ids, params, cbit_id).
- The op list is a **sequential tape** — parallelism is not represented.

---

## 3. WHAT OPERATIONS ARE VALID?

### Single-qubit gates
| Name | Matrix | T-count |
|------|--------|---------|
| H    | (X+Z)/sqrt(2) | 0 |
| T    | diag(1, e^{i pi/4}) | 1 |
| Tdg  | diag(1, e^{-i pi/4}) | 1 |
| S    | diag(1, i) = T^2 | 0 |
| Sdg  | diag(1, -i) | 0 |
| X    | Pauli-X (NOT) | 0 |
| Y    | Pauli-Y | 0 |
| Z    | Pauli-Z | 0 |
| Rx(t)| e^{-i t/2 X} | parametric |
| Ry(t)| e^{-i t/2 Y} | parametric |
| Rz(p)| e^{-i p/2 Z} | parametric |

### Two-qubit gates
| Name | Description | T-count |
|------|-------------|---------|
| CX   | Controlled-NOT | 0 |
| CZ   | Controlled-Z | 0 |
| SWAP | Swap two qubits | 0 |

### Three-qubit gates
| Name | Description | T-count |
|------|-------------|---------|
| CCX  | Toffoli (doubly controlled NOT) | 7 (Selinger decomposition) |

### Non-gate operations
- `measure(q)`: consumes qubit, returns ClassicalBit.
- `init_qubit()`: allocates a new qubit in |0>.
- `reset_qubit(q)`: destructive reset to |0>.
- `barrier(*qubits)`: scheduling hint, does not consume qubits.

### Type rules
- Every gate f : Qubit^k -> Qubit^k.  Input refs consumed, fresh refs returned.
- `measure` : Qubit -> ClassicalBit.  Input ref consumed, classical output returned.
- Barriers borrow qubits (no consume/return).

---

## 4. WHAT INVARIANTS MUST HOLD?

### Linear resource invariants
1. **No-cloning**: a QubitRef may be consumed at most once.
   Violation: `LinearityViolation("already been consumed")`.

2. **No-discard**: every allocated QubitRef must be consumed before
   `check_all_consumed()` is called.
   Violation: `LinearityViolation("Linear resource leak")`.

3. **Freshness**: after a gate consumes ref q, the only live ref for
   that qubit is the new ref returned by the gate.  The old ref is
   dead and raises on any further use.

### Circuit invariants
4. **Qubit index validity**: every qubit_id in a GuppyOp must be in
   [0, circuit.n_qubits).

5. **Sequential consistency**: the op list records the causal order of
   the circuit.  An op cannot reference a qubit before it is allocated.

### QIR invariants
6. **unsupported non-empty**: every QIR output from a Guppy circuit
   must contain at least one entry in `metadata.unsupported` (the HUGR
   flattening note).

7. **gate_count accuracy**: `resources.gate_count` equals exactly the
   number of ops with `type == "gate"`.

8. **t_count accuracy**: `resources.t_count` equals the count of T +
   Tdg ops plus 7 times the count of CCX ops.

---

## 5. HOW IS IT LOWERED?

Lowering path: GuppyCircuit -> QuantumIR JSON

1. **Op translation** (`guppy_to_ir.py`): iterate circ.ops in order;
   call `op.to_ir_dict()` on each; append to `ops` list.

2. **Resource estimation** (`_compute_resources`): single pass over ops
   tracking per-qubit depth counters (greedy critical-path
   approximation).

3. **Unsupported detection** (`_detect_extra_unsupported`): scan for
   CCX (T-count approximation note) and rotation gates (float64
   precision note).

4. **JSON assembly**: pack version, source_lang, qubits, cbits, ops,
   metadata (with mandatory unsupported list), resources.

5. **Validation** (`validate_ir`): lightweight structural check before
   returning.

What is NOT done during lowering:
- No gate fusion or peephole optimisation.
- No qubit routing or layout.
- No decomposition of high-level gates into primitive gate sets.
- No simulation of quantum state.

---

## 6. HOW IS IT TESTED?

Tests live in `guppy/tests/test_guppy.py` (48 tests, all passing).

### Test categories
| Class | Coverage |
|-------|----------|
| `TestLinearityViolations` | No-cloning, no-discard, CX self-reference, unconsumed qubits, measure type |
| `TestBellStateQIR` | Source lang, qubit/cbit counts, op list structure, gate names, measure ops, gate_count, t_count, width, JSON parsing, validate_ir |
| `TestUnsupportedList` | Presence, type, non-empty, HUGR note, extra propagation |
| `TestResourceCounting` | gate_count excludes measures, T/Tdg/CCX t-count, width, serial depth, parallel depth |
| `TestRotationGates` | Rx/Rz parameter preservation |
| `TestTwoQubitGates` | CX qubit order, CZ/SWAP names |
| `TestGroverCircuit` | Full Grover lowering |
| `TestSchemaVersion` | QIR version string, required keys |

Run:
    pytest guppy/tests/test_guppy.py -v

---

## 7. WHAT INFORMATION IS LOST?

When lowering from GuppyCircuit -> QIR:

1. **Graph structure**: the HUGR DAG becomes a flat sequential list.
   Data-flow parallelism is lost.

2. **Port types**: HUGR encodes types on edges.  QIR uses only qubit
   indices and a string gate name.

3. **Hierarchical nesting**: conditionals, loops, function calls inside
   HUGR become unexpandable in QIR v0.1.

4. **Inductive type recursion**: Guppy supports algebraic data types;
   QIR has no notion of them.

5. **Optimisation pass results**: no gate fusion or routing is applied.

6. **Compile-time vs runtime checking**: type violations are caught at
   runtime here, not at parse/import time.

7. **Parametric gate precision**: rotation angles are float64, not
   exact symbolic expressions.

All items 1-4 are recorded in `metadata.unsupported` in every QIR
output so that downstream consumers can make informed decisions.

---

## 8. WHAT BACKEND ASSUMPTIONS EXIST?

Our QIR JSON output assumes a backend that:

1. Accepts sequential op lists (no parallel scheduling metadata).
2. Understands the gate names: H, T, Tdg, S, Sdg, X, Y, Z, Rx, Ry,
   Rz, CX, CZ, SWAP, CCX.
3. Treats `measure` as a terminal qubit operation that produces a
   classical bit.
4. Does not rely on Guppy-specific HUGR semantics absent from the
   `ops` list.
5. Reads `metadata.unsupported` to understand what semantics are absent.

This QIR format is compatible with the shared QuantumIR schema defined
in `ir/quantum_ir_schema.json`, consumed by all agents in the
bob-agent-hackathon-2 pipeline.

---

*AGENT_02 (NETON) | Guppy Python frontend | 2026-08-19*
