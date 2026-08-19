"""
guppy_ops.py — Gate operations for the Guppy Python simulation.

Design principle
----------------
Every gate function:
  1. CONSUMES its input QubitRef(s) via .consume().
  2. Records a GuppyOp into the circuit.
  3. RETURNS a new QubitRef with the same id (representing the qubit *after*
     the gate is applied).

This consume-and-return pattern mirrors Guppy's linear function signatures,
e.g.:
    def h(q: Qubit) -> Qubit    -- takes ownership, returns new Qubit value

It is NOT the same as mutating a register (that is Qiskit's model).  In our
simulation, holding onto the old QubitRef after calling a gate will cause a
LinearityViolation on the next use — exactly as the Guppy type checker would
catch at compile time.

No external quantum library is required — this is pure Python.
"""

from __future__ import annotations

import math
from typing import Tuple

from .guppy_types import GuppyCircuit, GuppyOp, QubitRef, ClassicalBit, LinearityViolation


# ---------------------------------------------------------------------------
# Single-qubit gates
# ---------------------------------------------------------------------------

def h(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """Hadamard gate.

    Consumes qubit ref `q`, records H gate, returns fresh QubitRef with
    the same id representing the post-H qubit.

    Parameters
    ----------
    circ : GuppyCircuit
    q    : QubitRef — must be live (not yet consumed)

    Returns
    -------
    QubitRef representing q after H applied.
    """
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="H",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def t(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """T gate (pi/8 phase gate).

    T is the most expensive gate in fault-tolerant quantum computing —
    t_count is the primary resource metric for T-factory overhead.
    """
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="T",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def t_dag(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """T-dagger gate (conjugate of T)."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Tdg",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def s(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """S gate (phase gate, pi/2 rotation about Z)."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="S",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def s_dag(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """S-dagger gate."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Sdg",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def x(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """Pauli-X (NOT) gate."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="X",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def y(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """Pauli-Y gate."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Y",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def z(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """Pauli-Z gate."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Z",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)


def rx(circ: GuppyCircuit, theta: float, q: QubitRef) -> QubitRef:
    """Rx rotation — e^{-i theta/2 X}.

    Parameters
    ----------
    circ  : GuppyCircuit
    theta : rotation angle in radians (UNRESTRICTED classical value)
    q     : QubitRef — linear qubit input
    """
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Rx",
        qubit_ids=[consumed.id],
        params=[float(theta)],
    ))
    return QubitRef(consumed.id)


def ry(circ: GuppyCircuit, theta: float, q: QubitRef) -> QubitRef:
    """Ry rotation — e^{-i theta/2 Y}."""
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Ry",
        qubit_ids=[consumed.id],
        params=[float(theta)],
    ))
    return QubitRef(consumed.id)


def rz(circ: GuppyCircuit, phi: float, q: QubitRef) -> QubitRef:
    """Rz rotation — e^{-i phi/2 Z}.

    Parameters
    ----------
    circ : GuppyCircuit
    phi  : rotation angle in radians (classical)
    q    : QubitRef — linear qubit input
    """
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="Rz",
        qubit_ids=[consumed.id],
        params=[float(phi)],
    ))
    return QubitRef(consumed.id)


# ---------------------------------------------------------------------------
# Two-qubit gates
# ---------------------------------------------------------------------------

def cx(circ: GuppyCircuit, ctrl: QubitRef, tgt: QubitRef) -> Tuple[QubitRef, QubitRef]:
    """CNOT (controlled-X) gate.

    Consumes both ctrl and tgt, records CX, returns fresh refs for both.

    Linearity contract
    ------------------
    Both control and target are linear — passing the same QubitRef as both
    arguments would attempt to consume it twice, raising LinearityViolation.
    This is exactly what the no-cloning theorem forbids.
    """
    c_consumed = ctrl.consume()
    t_consumed = tgt.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="CX",
        qubit_ids=[c_consumed.id, t_consumed.id],
        params=[],
    ))
    return QubitRef(c_consumed.id), QubitRef(t_consumed.id)


def cz(circ: GuppyCircuit, ctrl: QubitRef, tgt: QubitRef) -> Tuple[QubitRef, QubitRef]:
    """Controlled-Z gate."""
    c_consumed = ctrl.consume()
    t_consumed = tgt.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="CZ",
        qubit_ids=[c_consumed.id, t_consumed.id],
        params=[],
    ))
    return QubitRef(c_consumed.id), QubitRef(t_consumed.id)


def swap(circ: GuppyCircuit, q0: QubitRef, q1: QubitRef) -> Tuple[QubitRef, QubitRef]:
    """SWAP gate — exchanges the states of two qubits."""
    c0 = q0.consume()
    c1 = q1.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="SWAP",
        qubit_ids=[c0.id, c1.id],
        params=[],
    ))
    # SWAP transposes ownership — return in swapped order for clarity,
    # though the ids are still the physical qubit ids.
    return QubitRef(c0.id), QubitRef(c1.id)


# ---------------------------------------------------------------------------
# Three-qubit gates
# ---------------------------------------------------------------------------

def ccx(
    circ: GuppyCircuit,
    ctrl0: QubitRef,
    ctrl1: QubitRef,
    tgt: QubitRef,
) -> Tuple[QubitRef, QubitRef, QubitRef]:
    """Toffoli (CCX) gate — doubly controlled NOT.

    Decomposes into 7 T gates, 2 Hadamards, and CNOT network.
    We record it as a single op; the t_count contribution is noted in
    resource metadata.
    """
    c0 = ctrl0.consume()
    c1 = ctrl1.consume()
    t_ = tgt.consume()
    circ.record_op(GuppyOp(
        op_type="gate",
        name="CCX",
        qubit_ids=[c0.id, c1.id, t_.id],
        params=[],
    ))
    return QubitRef(c0.id), QubitRef(c1.id), QubitRef(t_.id)


# ---------------------------------------------------------------------------
# Measurement — crosses the quantum/classical boundary
# ---------------------------------------------------------------------------

def measure(circ: GuppyCircuit, q: QubitRef) -> ClassicalBit:
    """Measure a qubit in the Z basis.

    This is the *quantum-to-classical* boundary crossing:
      - The qubit (linear) is CONSUMED — it no longer exists as a quantum resource.
      - A ClassicalBit (unrestricted) is RETURNED — it can be freely copied/used.

    In Guppy, measurement has type:  measure : Qubit -> bool
    The qubit is *moved into* the measurement, not borrowed.

    Returns
    -------
    ClassicalBit with an auto-assigned cbit_id.
    """
    consumed = q.consume()
    cbit_id = circ._alloc_cbit()
    circ.record_op(GuppyOp(
        op_type="measure",
        name="measure",
        qubit_ids=[consumed.id],
        cbit_id=cbit_id,
    ))
    return ClassicalBit(cbit_id=cbit_id)


# ---------------------------------------------------------------------------
# Qubit allocation
# ---------------------------------------------------------------------------

def init_qubit(circ: GuppyCircuit) -> QubitRef:
    """Allocate a fresh qubit in the |0> state.

    In Guppy, new qubits are introduced by the `qubit()` built-in.
    This function models mid-circuit ancilla allocation.

    Returns
    -------
    A fresh QubitRef with a new id, in the live (unconsumed) state.
    """
    ref = circ._alloc_qubit()
    circ.record_op(GuppyOp(
        op_type="reset",
        name="init",
        qubit_ids=[ref.id],
        params=[],
    ))
    return ref


# ---------------------------------------------------------------------------
# Barrier (scheduling hint, not a physical operation)
# ---------------------------------------------------------------------------

def barrier(circ: GuppyCircuit, *qubits: QubitRef) -> Tuple[QubitRef, ...]:
    """Insert a barrier across the given qubits.

    A barrier is a scheduling directive — it does not consume qubits (it is
    a *borrow*, not a move, in ownership terms).  In our simulation we model
    this by not consuming the refs.
    """
    ids = [q.id for q in qubits]
    circ.record_op(GuppyOp(
        op_type="barrier",
        name="barrier",
        qubit_ids=ids,
        params=[],
    ))
    return tuple(qubits)  # refs returned unchanged


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def reset_qubit(circ: GuppyCircuit, q: QubitRef) -> QubitRef:
    """Reset qubit to |0> state.

    In Guppy this is a destructive operation on the current qubit state
    followed by allocation of a fresh |0> state.  We model it as consuming
    the old ref and returning a new one with the same id.
    """
    consumed = q.consume()
    circ.record_op(GuppyOp(
        op_type="reset",
        name="reset",
        qubit_ids=[consumed.id],
        params=[],
    ))
    return QubitRef(consumed.id)
