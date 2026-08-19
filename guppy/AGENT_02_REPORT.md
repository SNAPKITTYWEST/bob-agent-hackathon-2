AGENT_ID: AGENT_02 (NETON)
LANGUAGE: Guppy (Python simulation of guppylang semantics)
TASK: Guppy-to-IR translation with linear type enforcement
DATE: 2026-08-19

FILES_CREATED:
  ir/quantum_ir_schema.json          -- Shared QIR contract (JSON Schema draft-07).
                                        Produced by AGENT_02 since AGENT_01 had not
                                        yet pushed it when this branch was created.
  guppy/__init__.py                  -- Package exports
  guppy/guppy_types.py               -- Core type system: Linearity enum, QubitRef,
                                        ClassicalBit, GuppyCircuit, GuppyOp,
                                        LinearityViolation
  guppy/guppy_ops.py                 -- Gate operations: h, cx, t, t_dag, s, s_dag,
                                        x, y, z, rx, ry, rz, cz, swap, ccx,
                                        measure, init_qubit, barrier, reset_qubit
  guppy/guppy_to_ir.py               -- Lowering pass: circuit_to_ir(),
                                        circuit_to_ir_json(), validate_ir(),
                                        resource estimation
  guppy/examples/__init__.py
  guppy/examples/bell_state.py       -- Bell state: H(q0), CX(q0,q1), M(q0), M(q1)
  guppy/examples/grover_2qubit.py    -- 2-qubit Grover (oracle |11>, 1 iteration)
  guppy/tests/__init__.py
  guppy/tests/test_guppy.py          -- 48 pytest tests across 8 test classes
  guppy/HUGR_SKETCH.md               -- HUGR explanation and simulation gap analysis
  guppy/FIRST_PRINCIPLES.md          -- 8-question mathematical specification

FILES_MODIFIED: none

EXISTING_FILES_PRESERVED:
  quantum-world/               -- Python quantum world agents, AOQD, voxel tools
  mqs/                         -- Rust+Haskell+Prolog MQS substrate
  sovereign-voxel-civilization/ -- Rust voxel agents
  formal/SparseVoxelEncoding.lean -- Lean4 proof

IR_INTERFACE: ir/quantum_ir_schema.json
  - Produced by AGENT_02 (NETON) as AGENT_01 had not yet pushed it.
  - Schema is JSON Schema draft-07 with oneOf discriminated op union.
  - source_lang: "guppy" | "quipper" | "yao" | "qasm" | "unknown"
  - ops: gate | measure | barrier | reset
  - metadata.unsupported: REQUIRED non-empty list for all Guppy output

MATHEMATICAL_PRIMITIVES:

  Linear types (Girard linear logic)
  -----------------------------------
  A Qubit is a LINEAR type -- it must be used exactly once.
  This models the quantum no-cloning theorem (Wootters & Zurek 1982):
  no unitary U satisfies U|psi>|0> = |psi>|psi> for all |psi>.

  Implementation: QubitRef.consume() sets _consumed=True.
  Second call raises LinearityViolation.
  GuppyCircuit.check_all_consumed() reports any unreleased qubits.

  Classical/quantum boundary
  --------------------------
  measure() is the ONLY crossing point from quantum to classical.
  Input type: QubitRef (LINEAR -- consumed by measure)
  Output type: ClassicalBit (UNRESTRICTED -- freely copied)
  This boundary is architecturally enforced -- there is no other way
  to extract information from a quantum resource in this simulation.

  Gate semantics (consume-and-return)
  ------------------------------------
  Every gate function f(circ, q) -> q':
    - Calls q.consume() (raises if q already consumed)
    - Records GuppyOp to circ.ops
    - Returns QubitRef(q.id) -- a FRESH ref to the same physical qubit

  This means: you MUST use the RETURNED ref for subsequent operations.
  Keeping the old ref and passing it to another gate is a linearity
  violation, caught immediately.

  Resource metrics
  ----------------
  gate_count: count of ops with type=="gate" (excludes measure/reset/barrier)
  t_count: T + Tdg ops + 7 * CCX ops (Selinger T-gate decomposition)
  depth: greedy per-qubit critical-path approximation
  width: total allocated qubit count

TESTS_ADDED:
  guppy/tests/test_guppy.py -- 48 tests:
    TestLinearityViolations  (9 tests)  -- no-cloning, no-discard, type checks
    TestBellStateQIR         (12 tests) -- full Bell state QIR shape validation
    TestUnsupportedList      (5 tests)  -- unsupported field invariants
    TestResourceCounting     (8 tests)  -- gate_count, t_count, CCX, depth, width
    TestRotationGates        (2 tests)  -- Rx/Rz parameter preservation
    TestTwoQubitGates        (3 tests)  -- CX order, CZ/SWAP names
    TestGroverCircuit        (5 tests)  -- full Grover lowering
    TestSchemaVersion        (4 tests)  -- QIR version, required keys

TESTS_PASSING: 48/48
  Command: pytest guppy/tests/test_guppy.py -v
  Result:  48 passed in 0.27s

BELL_STATE_QIR_OUTPUT:
  {
    "version": "0.1.0",
    "source_lang": "guppy",
    "qubits": 2,
    "cbits": 2,
    "ops": [
      {"type": "gate", "name": "H",  "qubits": [0], "params": []},
      {"type": "gate", "name": "CX", "qubits": [0, 1], "params": []},
      {"type": "measure", "qubit": 0, "cbit": 0},
      {"type": "measure", "qubit": 1, "cbit": 1}
    ],
    "metadata": {
      "source_lang": "guppy",
      "version": "0.1.0",
      "unsupported": [
        "HUGR graph structure (flattened to sequential ops)",
        "inductive type recursion (not representable in QIR v0.1)"
      ]
    },
    "resources": {
      "gate_count": 2,
      "depth": 3,
      "t_count": 0,
      "width": 2
    }
  }

CROSS_LANGUAGE_DEPENDENCIES:
  ir/quantum_ir_schema.json -- shared with AGENT_01 (Quipper) and AGENT_03 (Yao)
  Cross-language equivalence test: compare Bell state QIR from all three agents.
  Expected invariants:
    - source_lang differs (guppy / quipper / yao)
    - qubits == 2 for all three
    - gate_count == 2 for all three (H + entangling gate)
    - t_count == 0 for all three
    - ops[0].name == "H" and ops[0].qubits == [0] for all three
    - Both measures present

ROUTER_HANDOFF: Guppy layer complete. Bell state QIR validated and confirmed.
  ir/quantum_ir_schema.json is live for AGENT_01 and AGENT_03 to consume.
  48/48 tests pass. Linear type violations raise correctly.
  Bell state ready for cross-language equivalence test.

BLOCKERS: none

SIMULATION_DISCLAIMER:
  This is NOT the real guppylang compiler. It is a Python simulation
  of Guppy's linear type semantics. No physical QPU execution.
  HUGR graph structure is not preserved. See guppy/HUGR_SKETCH.md.

NEXT_TASK: Cross-language equivalence test with AGENT_01 (Quipper Bell state)
           and AGENT_03 (Yao Bell state). Compare QIR outputs against shared
           ir/quantum_ir_schema.json invariants listed above.
