-- quipper/src/Quipper/Primitives.hs
-- Primitive gate constructors for the Quipper-style frontend.
-- All functions return `Circ ()` and emit their gate into the accumulator.
-- Wire arguments are passed explicitly (Quipper convention).

module Quipper.Primitives
  ( -- * Single-qubit gates
    hadamard
  , pauliX, pauliY, pauliZ
  , tGate, tDag
  , sGate, sDag
  , rx, ry, rz
    -- * Two-qubit gates
  , cnot
  , cz
  , swapGate
    -- * Three-qubit gates
  , toffoli
  , fredkin
    -- * Measurement and lifecycle
  , measure
  , qinit, qinit0, qinit1
  , qdiscard
    -- * Convenience: allocate + apply
  , freshQubit
  ) where

import Quipper.Syntax

-- ── Single-qubit gates ────────────────────────────────────────────────────────

-- | Hadamard gate: |0⟩ ↦ (|0⟩+|1⟩)/√2, |1⟩ ↦ (|0⟩-|1⟩)/√2
hadamard :: Wire -> Circ ()
hadamard w = emitOp (Hadamard w)

-- | Pauli-X (bit flip): |0⟩ ↔ |1⟩
pauliX :: Wire -> Circ ()
pauliX w = emitOp (PauliX w)

-- | Pauli-Y: |0⟩ ↦ i|1⟩, |1⟩ ↦ -i|0⟩
pauliY :: Wire -> Circ ()
pauliY w = emitOp (PauliY w)

-- | Pauli-Z (phase flip): |1⟩ ↦ -|1⟩
pauliZ :: Wire -> Circ ()
pauliZ w = emitOp (PauliZ w)

-- | T gate: diag(1, exp(iπ/4))
-- Primary resource in fault-tolerant computation.
tGate :: Wire -> Circ ()
tGate w = emitOp (T w)

-- | T† (T-dagger): diag(1, exp(-iπ/4))
tDag :: Wire -> Circ ()
tDag w = emitOp (TDag w)

-- | S gate (phase gate): diag(1, i) = T²
sGate :: Wire -> Circ ()
sGate w = emitOp (S w)

-- | S† (S-dagger): diag(1, -i) = T†²
sDag :: Wire -> Circ ()
sDag w = emitOp (SDag w)

-- | Rx(θ): rotation about X-axis by angle θ (radians)
-- Rx(θ) = cos(θ/2)·I - i·sin(θ/2)·X
rx :: Double -> Wire -> Circ ()
rx theta w = emitOp (Rx theta w)

-- | Ry(θ): rotation about Y-axis by angle θ (radians)
ry :: Double -> Wire -> Circ ()
ry theta w = emitOp (Ry theta w)

-- | Rz(θ): rotation about Z-axis by angle θ (radians)
-- Rz(θ) = diag(exp(-iθ/2), exp(iθ/2))
rz :: Double -> Wire -> Circ ()
rz theta w = emitOp (Rz theta w)

-- ── Two-qubit gates ───────────────────────────────────────────────────────────

-- | CNOT (Controlled-X): flips target when control is |1⟩.
-- Convention: first argument = control, second = target.
cnot :: Wire -> Wire -> Circ ()
cnot ctrl tgt = emitOp (CNOT { control = ctrl, target = tgt })

-- | Controlled-Z: applies Z to both qubits when both are |1⟩.
-- Symmetric: CZ ctrl tgt == CZ tgt ctrl.
cz :: Wire -> Wire -> Circ ()
cz w1 w2 = emitOp (CZ w1 w2)

-- | SWAP: exchanges the quantum states of two wires.
swapGate :: Wire -> Wire -> Circ ()
swapGate w1 w2 = emitOp (SWAP w1 w2)

-- ── Three-qubit gates ─────────────────────────────────────────────────────────

-- | Toffoli (CCX): flips target when both controls are |1⟩.
-- Arguments: control1, control2, target.
toffoli :: Wire -> Wire -> Wire -> Circ ()
toffoli c1 c2 tgt = emitOp (Toffoli c1 c2 tgt)

-- | Fredkin (CSWAP): swaps target1 and target2 when control is |1⟩.
fredkin :: Wire -> Wire -> Wire -> Circ ()
fredkin ctrl t1 t2 = emitOp (Fredkin ctrl t1 t2)

-- ── Measurement and lifecycle ─────────────────────────────────────────────────

-- | Measure a wire, writing the result to a classical bit index.
-- The wire is consumed (destroyed by measurement in the Z basis).
-- Returns the classical bit index used.
measure :: Wire -> Int -> Circ ()
measure w cbitIdx = emitOp (QMeasure w cbitIdx)

-- | Initialize a fresh qubit to |b⟩ (False = |0⟩, True = |1⟩).
-- Equivalent to qinit0/qinit1 but takes an explicit boolean.
qinit :: Bool -> Circ Wire
qinit False = qinit0
qinit True  = qinit1

-- | Discard a qubit (end of lifetime, no measurement).
-- In a physical system this corresponds to tracing out the qubit.
qdiscard :: Wire -> Circ ()
qdiscard w = emitOp (QDiscard w)

-- ── Convenience ───────────────────────────────────────────────────────────────

-- | Allocate a fresh |0⟩ qubit and return its wire.
-- Alias for qinit0, provided for readability at call sites.
freshQubit :: Circ Wire
freshQubit = qinit0
