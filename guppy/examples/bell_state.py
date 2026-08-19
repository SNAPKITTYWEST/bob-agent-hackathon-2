"""
bell_state.py -- Bell state circuit using the Guppy Python simulation.

Circuit
-------
    q0: --- H --- ctrl --- M --
                  |
    q1: --------- tgt  --- M --

Prepares the maximally entangled Bell state |Phi+> = (|00> + |11>)/sqrt(2).

Steps
-----
1. Apply H to q0  ->  q0 = (|0> + |1>)/sqrt(2)
2. Apply CX q0->q1 ->  (q0,q1) = (|00> + |11>)/sqrt(2)
3. Measure both qubits

Linearity check
---------------
Both qubits are consumed by measure(), so circ.check_all_consumed() passes.
"""

from __future__ import annotations

import json
import sys
import os

# Allow running directly: python guppy/examples/bell_state.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from guppy import GuppyCircuit, h, cx, measure, circuit_to_ir
from guppy.guppy_to_ir import circuit_to_ir_json, validate_ir


def build_bell_state() -> GuppyCircuit:
    """Build the Bell state circuit and return the completed GuppyCircuit."""
    # Allocate circuit
    circ = GuppyCircuit(n_qubits=2)

    # Get qubit refs
    q0 = circ.qubit(0)
    q1 = circ.qubit(1)

    # H gate on q0 -- creates superposition
    q0 = h(circ, q0)

    # CX gate: q0 is control, q1 is target -- creates entanglement
    q0, q1 = cx(circ, q0, q1)

    # Measure both qubits -- crosses the quantum/classical boundary
    b0 = measure(circ, q0)
    b1 = measure(circ, q1)

    # Linearity audit -- all qubits consumed, no linear resource leak
    circ.check_all_consumed()

    return circ


def main() -> None:
    print("=" * 60)
    print("AGENT_02 (NETON) -- Guppy Bell State Example")
    print("=" * 60)
    print()

    circ = build_bell_state()

    print("Circuit:", circ)
    print("Ops recorded:", len(circ.ops))
    for i, op in enumerate(circ.ops):
        print(f"  [{i}] {op}")
    print()

    # Lower to QuantumIR
    qir = circuit_to_ir(circ)

    # Validate
    errors = validate_ir(qir)
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print("QIR validation passed.")
    print()

    # Print QIR JSON
    qir_json = circuit_to_ir_json(circ)
    print("QuantumIR JSON:")
    print(qir_json)
    print()

    # Assertions for CI
    # Bell state: H(q0), CX(q0,q1), measure(q0), measure(q1) = 4 ops total
    assert qir["source_lang"] == "guppy", "source_lang must be guppy"
    assert qir["qubits"] == 2, "Bell state needs exactly 2 qubits"
    assert qir["cbits"] == 2, "Bell state produces 2 classical bits"
    assert len(qir["ops"]) == 4, (
        "Expected 4 ops: H, CX, measure(q0), measure(q1). Got " + str(len(qir["ops"]))
    )
    assert qir["metadata"]["unsupported"], "unsupported list must not be empty"
    assert qir["metadata"]["source_lang"] == "guppy"

    print("All assertions passed.")
    print()
    print("source_lang  :", qir["source_lang"])
    print("qubits       :", qir["qubits"])
    print("cbits        :", qir["cbits"])
    print("gate_count   :", qir["resources"]["gate_count"])
    print("t_count      :", qir["resources"]["t_count"])
    print("depth        :", qir["resources"]["depth"])
    print("width        :", qir["resources"]["width"])
    print()
    print("Unsupported semantics (explicit list):")
    for item in qir["metadata"]["unsupported"]:
        print("  -", item)


if __name__ == "__main__":
    main()
