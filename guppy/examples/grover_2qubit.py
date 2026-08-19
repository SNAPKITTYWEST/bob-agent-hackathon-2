"""
grover_2qubit.py — 2-qubit Grover's algorithm (oracle for |11⟩, 1 iteration).

Algorithm overview
------------------
Grover's algorithm amplifies the amplitude of a target state.  For 2 qubits
with target |11⟩ and 1 iteration:

1. INITIALISE: |ψ₀⟩ = H⊗H |00⟩ = (|00⟩+|01⟩+|10⟩+|11⟩)/2
2. ORACLE (phase kickback for |11⟩):
       |11⟩ → -|11⟩  (all others unchanged)
   Implemented as: CZ on (q0, q1)
3. DIFFUSION (Grover diffusion operator = 2|ψ⟩⟨ψ| - I):
   a. H⊗H
   b. Phase flip on |00⟩: X⊗X · CZ · X⊗X
   c. H⊗H
4. MEASURE

After 1 iteration on N=4, the |11⟩ amplitude is boosted to ~√2/2.

Circuit (Guppy linear ops)
--------------------------
  q0: H ─ ●  ─ H ─ X ─ ●  ─ X ─ H ─ M
           │           │
  q1: H ─ Z  ─ H ─ X ─ Z  ─ X ─ H ─ M

(CZ = controlled-Z; ● = control, Z = target for CZ)
"""

from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from guppy import GuppyCircuit, h, cx, measure, circuit_to_ir
from guppy.guppy_ops import cz, x
from guppy.guppy_to_ir import circuit_to_ir_json, validate_ir


def build_grover_2qubit() -> GuppyCircuit:
    """Build the 2-qubit Grover circuit (oracle for |11⟩, 1 iteration)."""
    circ = GuppyCircuit(n_qubits=2)

    q0 = circ.qubit(0)
    q1 = circ.qubit(1)

    # ---------------------------------------------------------------
    # STEP 1: Initialise uniform superposition
    # ---------------------------------------------------------------
    q0 = h(circ, q0)
    q1 = h(circ, q1)

    # ---------------------------------------------------------------
    # STEP 2: Oracle — phase flip |11⟩ via CZ
    # CZ|11⟩ = -|11⟩ (phase kickback)
    # ---------------------------------------------------------------
    q0, q1 = cz(circ, q0, q1)

    # ---------------------------------------------------------------
    # STEP 3: Diffusion operator  (2|ψ⟩⟨ψ| - I)
    # ---------------------------------------------------------------
    # 3a: H⊗H
    q0 = h(circ, q0)
    q1 = h(circ, q1)

    # 3b: Phase flip on |00⟩ = X⊗X · CZ · X⊗X
    q0 = x(circ, q0)
    q1 = x(circ, q1)
    q0, q1 = cz(circ, q0, q1)
    q0 = x(circ, q0)
    q1 = x(circ, q1)

    # 3c: H⊗H
    q0 = h(circ, q0)
    q1 = h(circ, q1)

    # ---------------------------------------------------------------
    # STEP 4: Measure
    # ---------------------------------------------------------------
    b0 = measure(circ, q0)
    b1 = measure(circ, q1)

    circ.check_all_consumed()
    return circ


def main() -> None:
    print("=" * 60)
    print("AGENT_02 (NETON) -- 2-Qubit Grover (oracle: |11>)")
    print("=" * 60)
    print()

    circ = build_grover_2qubit()
    print(f"Circuit: {circ}")
    print(f"Total ops: {len(circ.ops)}")
    print()

    for i, op in enumerate(circ.ops):
        print(f"  [{i:2d}] {op}")
    print()

    qir = circuit_to_ir(circ)
    errors = validate_ir(qir)
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("QIR validation passed.")
    print()

    qir_json = circuit_to_ir_json(circ)
    print("QuantumIR JSON:")
    print(qir_json)
    print()

    assert qir["source_lang"] == "guppy"
    assert qir["qubits"] == 2
    gate_ops = [op for op in qir["ops"] if op["type"] == "gate"]
    measure_ops = [op for op in qir["ops"] if op["type"] == "measure"]
    print(f"gate ops   : {len(gate_ops)}")
    print(f"measure ops: {len(measure_ops)}")
    print(f"gate_count : {qir['resources']['gate_count']}")
    print(f"depth      : {qir['resources']['depth']}")
    print(f"t_count    : {qir['resources']['t_count']}")
    print(f"width      : {qir['resources']['width']}")
    print()
    print("Unsupported semantics:")
    for item in qir["metadata"]["unsupported"]:
        print(f"  - {item}")
    print()
    print("Grover circuit lowered successfully to QIR.")


if __name__ == "__main__":
    main()
