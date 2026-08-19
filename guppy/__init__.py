"""
Guppy Python frontend — a faithful simulation of Guppy/guppylang semantics.

IMPORTANT DISCLAIMER
--------------------
This package is NOT the real Guppy compiler (guppylang).  It is a pure-Python
simulation of Guppy's linear type system and classical/quantum boundary, built
for the BOB Agent Hackathon 2 multi-language quantum pipeline.

What we model:
  - Linear qubit references (QubitRef) enforcing the no-cloning theorem at the
    Python level — consuming a qubit ref twice raises LinearityViolation.
  - Gate operations that consume-and-return qubit refs to track ownership.
  - Lowering to the shared QuantumIR JSON contract (ir/quantum_ir_schema.json).

What we do NOT model:
  - HUGR (Hierarchical Unified Graph Representation) — actual Guppy IR.
  - Dependent types, inductive type recursion.
  - Compile-time type inference (our checks are runtime).
  - Optimisation passes performed by the real compiler.

See guppy/HUGR_SKETCH.md for a detailed comparison.
"""

from .guppy_types import (
    Linearity,
    QubitRef,
    ClassicalBit,
    GuppyCircuit,
    LinearityViolation,
)
from .guppy_ops import h, cx, t, s, rx, rz, measure, init_qubit
from .guppy_to_ir import circuit_to_ir

__all__ = [
    "Linearity",
    "QubitRef",
    "ClassicalBit",
    "GuppyCircuit",
    "LinearityViolation",
    "h", "cx", "t", "s", "rx", "rz", "measure", "init_qubit",
    "circuit_to_ir",
]
