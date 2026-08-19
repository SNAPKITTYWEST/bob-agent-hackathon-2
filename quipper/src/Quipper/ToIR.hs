-- quipper/src/Quipper/ToIR.hs
-- Translates a Quipper Circ computation to a QIRCircuit.
--
-- TRANSLATION STRATEGY:
--   1. Run the Circ monad to obtain (result, CircState).
--   2. Walk csOps in program order, mapping each QOp to one or more QIROp.
--   3. QInit False → QIRReset (|0⟩ is the reset state)
--      QInit True  → QIRReset + QIRGate "X" (|1⟩ = X|0⟩)
--      QDiscard    → barrier on that qubit (fences its lifetime)
--   4. Resources are computed by mkCircuit.
--   5. Unsupported semantics are declared explicitly in the metadata.
--
-- INFORMATION LOSS (declared in irMeta.unsupported):
--   A. Higher-order circuit parameters (Quipper BoxedCircuit):
--      Real Quipper allows circuits to be passed as first-class values and
--      applied multiple times (looping, subroutine calls). The Circ monad
--      here flattens all such structure into a linear gate sequence. Any
--      circuit-valued argument must be fully unrolled before calling toIR.
--
--   B. Dynamic lifting (classical feedback):
--      Quipper supports `dynamic_lift :: Bit -> Circ Bool`, which reads a
--      measurement result back into the classical host and uses it to choose
--      future gates. This creates a classically-controlled quantum circuit.
--      The IR represents circuits as static gate sequences. Conditional gates
--      based on mid-circuit measurement results are NOT representable. Any
--      such structure must be resolved to a static approximation before calling
--      toIR, and the approximation must be noted by the caller.

module Quipper.ToIR
  ( toIR
  , toIRWith
  ) where

import Quipper.Syntax
import QuantumIR

-- ── Main translation entry points ─────────────────────────────────────────────

-- | Translate a Quipper circuit to QIRCircuit using the standard Quipper
-- unsupported-semantics declaration.
-- Fails with Left if qubit/cbit bound checks fail.
toIR :: Circ a -> Either String QIRCircuit
toIR = toIRWith []

-- | Translate with additional unsupported-semantics annotations.
-- Use this when the caller has pre-resolved dynamic lifting or
-- BoxedCircuit parameters and wants to document the approximation.
toIRWith :: [String] -> Circ a -> Either String QIRCircuit
toIRWith extraUnsupported circ =
  let (_, st)    = buildCircuit circ
      ops        = concatMap qopToQIROp (csOps st)
      nQubits    = csCounter st
      nCbits     = csCbits st
      meta       = quipperMeta extraUnsupported
  in if nQubits == 0
       then Left "toIR: circuit has no qubits (empty Circ computation)"
       else mkCircuit nQubits (max 1 nCbits) ops meta

-- ── QOp → QIROp translation ────────────────────────────────────────────────────

-- | Map a single Quipper QOp to one or more QIROp values.
-- Returns a list to handle cases like QInit True (reset + X).
qopToQIROp :: QOp -> [QIROp]

-- Single-qubit gates — direct mapping
qopToQIROp (Hadamard (Wire q)) =
  [QIRGate { opName = "H",  opParams = [], opQubits = [q] }]

qopToQIROp (PauliX (Wire q)) =
  [QIRGate { opName = "X",  opParams = [], opQubits = [q] }]

qopToQIROp (PauliY (Wire q)) =
  [QIRGate { opName = "Y",  opParams = [], opQubits = [q] }]

qopToQIROp (PauliZ (Wire q)) =
  [QIRGate { opName = "Z",  opParams = [], opQubits = [q] }]

qopToQIROp (T (Wire q)) =
  [QIRGate { opName = "T",  opParams = [], opQubits = [q] }]

qopToQIROp (TDag (Wire q)) =
  [QIRGate { opName = "Tdg", opParams = [], opQubits = [q] }]

qopToQIROp (S (Wire q)) =
  [QIRGate { opName = "S",  opParams = [], opQubits = [q] }]

qopToQIROp (SDag (Wire q)) =
  [QIRGate { opName = "Sdg", opParams = [], opQubits = [q] }]

qopToQIROp (Rx theta (Wire q)) =
  [QIRGate { opName = "Rx", opParams = [theta], opQubits = [q] }]

qopToQIROp (Ry theta (Wire q)) =
  [QIRGate { opName = "Ry", opParams = [theta], opQubits = [q] }]

qopToQIROp (Rz theta (Wire q)) =
  [QIRGate { opName = "Rz", opParams = [theta], opQubits = [q] }]

-- Two-qubit gates
qopToQIROp (CNOT { control = Wire c, target = Wire t }) =
  [QIRGate { opName = "CX", opParams = [], opQubits = [c, t] }]

qopToQIROp (CZ (Wire w1) (Wire w2)) =
  [QIRGate { opName = "CZ", opParams = [], opQubits = [w1, w2] }]

qopToQIROp (SWAP (Wire w1) (Wire w2)) =
  [QIRGate { opName = "SWAP", opParams = [], opQubits = [w1, w2] }]

-- Three-qubit gates
qopToQIROp (Toffoli (Wire c1) (Wire c2) (Wire t)) =
  [QIRGate { opName = "CCX", opParams = [], opQubits = [c1, c2, t] }]

qopToQIROp (Fredkin (Wire c) (Wire t1) (Wire t2)) =
  [QIRGate { opName = "CSWAP", opParams = [], opQubits = [c, t1, t2] }]

-- Measurement: QMeasure wire cbitIndex → QIRMeasure
qopToQIROp (QMeasure (Wire q) c) =
  [QIRMeasure { mQubit = q, mCbit = c }]

-- Initialization:
--   QInit False → reset to |0⟩
--   QInit True  → reset to |0⟩, then X to reach |1⟩
qopToQIROp (QInit False (Wire q)) =
  [QIRReset { rQubit = q }]

qopToQIROp (QInit True (Wire q)) =
  [ QIRReset { rQubit = q }
  , QIRGate  { opName = "X", opParams = [], opQubits = [q] }
  ]

-- Discard: barrier on the qubit as a lifetime fence.
-- The qubit is not freed in the IR (static circuit model has no dynamic alloc).
qopToQIROp (QDiscard (Wire q)) =
  [QIRBarrier { bQubits = [q] }]
