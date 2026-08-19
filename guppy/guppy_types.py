"""
guppy_types.py — Core type system for the Guppy Python simulation.

Mathematical objects
--------------------
A quantum circuit in Guppy is a morphism in the category of finite-dimensional
Hilbert spaces.  The key invariant enforced here is *linearity*: qubits are
resources that must be used exactly once.  This models the quantum no-cloning
theorem and no-discarding principle at the type level.

Linearity taxonomy (after Girard's linear logic):
  LINEAR       — must be consumed exactly once  (qubits, entangled pairs)
  AFFINE       — consumed at most once           (e.g. ancilla that may leak)
  UNRESTRICTED — classical values, freely copied (angles, indices, bits)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


# ---------------------------------------------------------------------------
# Linearity annotation
# ---------------------------------------------------------------------------

class Linearity(Enum):
    """Linearity descriptor, mirroring Guppy's type-level resource tracking."""
    LINEAR = auto()        # must be used exactly once (qubits)
    AFFINE = auto()        # must be used at most once
    UNRESTRICTED = auto()  # classical values — freely duplicated


# ---------------------------------------------------------------------------
# Linearity violation
# ---------------------------------------------------------------------------

class LinearityViolation(Exception):
    """Raised whenever a linear resource constraint is broken.

    This is the Python-level equivalent of a Guppy compile-time type error.
    Because our simulation is runtime-checked, violations surface here rather
    than at parse time.
    """
    pass


# ---------------------------------------------------------------------------
# QubitRef — the linear qubit resource
# ---------------------------------------------------------------------------

@dataclass
class QubitRef:
    """A handle to a single qubit — a *linear* resource.

    Invariants
    ----------
    1. A QubitRef may be consumed (passed to a gate) exactly once.
    2. Consuming an already-consumed QubitRef raises LinearityViolation.
    3. A QubitRef that has not been consumed by circuit end signals a linearity
       leak — GuppyCircuit.check_all_consumed() reports these.

    This models Guppy's compile-time ownership tracking at runtime.  In the
    real Guppy compiler, these violations are caught during type inference over
    the HUGR graph.
    """
    id: int
    _consumed: bool = field(default=False, repr=False, compare=False)

    @property
    def consumed(self) -> bool:
        return self._consumed

    def consume(self) -> "QubitRef":
        """Mark this qubit as consumed and return self (for chaining).

        Raises
        ------
        LinearityViolation
            If the qubit has already been consumed (no-cloning violation).
        """
        if self._consumed:
            raise LinearityViolation(
                f"Qubit {self.id} has already been consumed — "
                "linear resources cannot be copied or reused (no-cloning theorem). "
                "In guppylang this is a compile-time type error."
            )
        self._consumed = True
        return self

    def __repr__(self) -> str:
        status = "consumed" if self._consumed else "live"
        return f"QubitRef(id={self.id}, {status})"


# ---------------------------------------------------------------------------
# ClassicalBit — unrestricted classical result
# ---------------------------------------------------------------------------

@dataclass
class ClassicalBit:
    """The result of measuring a qubit.

    Classical bits are UNRESTRICTED — they may be copied, compared, and
    discarded freely.  In Guppy's type system, measurement produces a `bool`
    (or `int`) which is a classical, non-linear type.
    """
    cbit_id: int
    linearity: Linearity = field(default=Linearity.UNRESTRICTED, init=False)

    def __repr__(self) -> str:
        return f"ClassicalBit(cbit_id={self.cbit_id})"


# ---------------------------------------------------------------------------
# GuppyOp — internal operation record
# ---------------------------------------------------------------------------

@dataclass
class GuppyOp:
    """A single operation inside a GuppyCircuit.

    Fields
    ------
    op_type   : "gate" | "measure" | "barrier" | "reset"
    name      : gate name (e.g. "H", "CX", "T")
    qubit_ids : list of qubit indices this op touches
    params    : optional rotation parameters (e.g. theta for Rx)
    cbit_id   : classical bit index, only for measure ops
    """
    op_type: str
    name: str
    qubit_ids: List[int]
    params: List[float] = field(default_factory=list)
    cbit_id: Optional[int] = field(default=None)

    def to_ir_dict(self) -> dict:
        """Convert to QuantumIR-compatible op dict."""
        if self.op_type == "gate":
            d: dict = {
                "type": "gate",
                "name": self.name,
                "qubits": list(self.qubit_ids),
            }
            if self.params:
                d["params"] = list(self.params)
            else:
                d["params"] = []
            return d
        elif self.op_type == "measure":
            return {
                "type": "measure",
                "qubit": self.qubit_ids[0],
                "cbit": self.cbit_id,
            }
        elif self.op_type == "barrier":
            return {"type": "barrier", "qubits": list(self.qubit_ids)}
        elif self.op_type == "reset":
            return {"type": "reset", "qubit": self.qubit_ids[0]}
        else:
            raise ValueError(f"Unknown op_type: {self.op_type!r}")


# ---------------------------------------------------------------------------
# GuppyCircuit — the primary circuit container
# ---------------------------------------------------------------------------

@dataclass
class GuppyCircuit:
    """A quantum circuit with Guppy-style linear resource tracking.

    Usage
    -----
    >>> circ = GuppyCircuit(n_qubits=2)
    >>> q0, q1 = circ.qubit(0), circ.qubit(1)
    >>> from guppy.guppy_ops import h, cx, measure
    >>> q0 = h(circ, q0)
    >>> q0, q1 = cx(circ, q0, q1)
    >>> measure(circ, q0)
    >>> measure(circ, q1)
    >>> circ.check_all_consumed()   # passes — all qubits consumed

    Attributes
    ----------
    n_qubits  : initial qubit count
    n_cbits   : classical bit counter (auto-incremented by measure())
    ops       : ordered list of GuppyOp records
    """
    n_qubits: int
    n_cbits: int = field(default=0)
    ops: List[GuppyOp] = field(default_factory=list, repr=False)
    _qubit_refs: List[QubitRef] = field(default_factory=list, repr=False)
    _next_qubit_id: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        self._qubit_refs = [QubitRef(i) for i in range(self.n_qubits)]
        self._next_qubit_id = self.n_qubits

    # ------------------------------------------------------------------
    # Qubit access
    # ------------------------------------------------------------------

    def qubit(self, i: int) -> QubitRef:
        """Return the QubitRef for the i-th initial qubit (0-indexed).

        Raises
        ------
        IndexError
            If i is out of the initial qubit range.
        """
        if i < 0 or i >= self.n_qubits:
            raise IndexError(
                f"Qubit index {i} out of range for circuit with {self.n_qubits} qubits"
            )
        return self._qubit_refs[i]

    def _alloc_qubit(self) -> QubitRef:
        """Allocate a new qubit at runtime (mid-circuit ancilla)."""
        ref = QubitRef(self._next_qubit_id)
        self._qubit_refs.append(ref)
        self._next_qubit_id += 1
        return ref

    def _alloc_cbit(self) -> int:
        """Allocate a new classical bit, returning its index."""
        idx = self.n_cbits
        self.n_cbits += 1
        return idx

    # ------------------------------------------------------------------
    # Linearity audit
    # ------------------------------------------------------------------

    def check_all_consumed(self) -> None:
        """Assert that every qubit has been consumed (measured or reset).

        In Guppy, this is enforced at compile time — every qubit that enters
        a function scope must be explicitly consumed before the scope closes.
        Here we check it at runtime.

        Raises
        ------
        LinearityViolation
            If any qubit was allocated but never consumed.
        """
        unconsumed = [q for q in self._qubit_refs if not q.consumed]
        if unconsumed:
            ids = [q.id for q in unconsumed]
            raise LinearityViolation(
                f"Linear resource leak: qubits {ids} were allocated but never consumed. "
                "In guppylang, each qubit must be explicitly discarded or measured."
            )

    # ------------------------------------------------------------------
    # Op recording (called by guppy_ops.py functions)
    # ------------------------------------------------------------------

    def record_op(self, op: GuppyOp) -> None:
        """Append an operation to the circuit log."""
        self.ops.append(op)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"GuppyCircuit(n_qubits={self._next_qubit_id}, "
            f"n_cbits={self.n_cbits}, ops={len(self.ops)})"
        )
