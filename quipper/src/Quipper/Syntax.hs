{-# LANGUAGE GeneralizedNewtypeDeriving #-}
-- quipper/src/Quipper/Syntax.hs
-- Quipper-style circuit syntax.
--
-- The real Quipper library requires GHC 8 and a specialized toolchain.
-- This module provides a FAITHFUL SEMANTIC REPRESENTATION of Quipper's
-- circuit model, buildable with any modern GHC (9.x), using:
--   - Newtype `Wire` for linear qubit resources (no cloning implied by use)
--   - State monad `Circ` for in-order gate accumulation
--   - `QOp` covering Quipper's standard gate vocabulary
--
-- WHAT THIS CAPTURES from Quipper:
--   - First-class circuits as values (Circ a computations)
--   - Wire linearity: wires are named resources threaded through the monad
--   - Standard gate set: H, CNOT, T, T†, S, Rx, Rz, CZ, Toffoli
--   - Measurement (destructive, classical output)
--   - Initialization (QInit) and discard (QDiscard)
--
-- WHAT IS NOT CAPTURED (declared explicitly in ToIR.hs):
--   - BoxedCircuit / higher-order circuit parameters
--   - Dynamic lifting (classical → quantum feedback)
--   - Ancilla management with automatic uncomputation
--   - Type-level qubit/cbit distinction (ClassicalWire vs QuantumWire)

module Quipper.Syntax where

import Control.Monad.State.Strict (State, get, put, modify, runState)

-- ── Wire ─────────────────────────────────────────────────────────────────────

-- | A named quantum wire (qubit resource).
-- In real Quipper, wires are linear — they cannot be duplicated or discarded
-- without explicit QDiscard. We model this as a named index; the type system
-- does not enforce linearity here (that would require linear types), but the
-- semantics are correct: each Wire maps to exactly one qubit in the circuit.
newtype Wire = Wire { wireIndex :: Int }
  deriving (Show, Eq, Ord)

-- ── Circuit state ─────────────────────────────────────────────────────────────

-- | The mutable state threaded through a Circ computation.
data CircState = CircState
  { csOps      :: [QOp]   -- ^ Operations accumulated in program order (reversed during build, corrected on extraction).
  , csWires    :: [Wire]   -- ^ All wires allocated so far.
  , csCounter  :: Int      -- ^ Next wire index to allocate.
  , csCbits    :: Int      -- ^ Number of measurement (classical) bits used so far.
  } deriving (Show)

initialCircState :: CircState
initialCircState = CircState
  { csOps     = []
  , csWires   = []
  , csCounter = 0
  , csCbits   = 0
  }

-- ── Circ monad ────────────────────────────────────────────────────────────────

-- | The circuit construction monad.
-- A `Circ a` computation, when run over an initial CircState, produces a value
-- of type `a` (often a tuple of output Wires) and an updated CircState
-- containing all accumulated operations.
--
-- This mirrors Quipper's `Circ` type, which is also a state-threading function.
-- In real Quipper the state includes the heap of live wires; here we make it
-- explicit as CircState.
newtype Circ a = Circ { runCirc :: State CircState a }
  deriving (Functor, Applicative, Monad)

-- ── Gate vocabulary ───────────────────────────────────────────────────────────

-- | A single quantum operation.
-- Maps 1-to-1 with Quipper's circuit primitives where possible.
data QOp
  -- Single-qubit gates
  = Hadamard  Wire              -- ^ H: Hadamard
  | PauliX    Wire              -- ^ X: bit flip
  | PauliY    Wire              -- ^ Y: Pauli-Y
  | PauliZ    Wire              -- ^ Z: phase flip
  | T         Wire              -- ^ T = diag(1, exp(iπ/4))
  | TDag      Wire              -- ^ T† = diag(1, exp(-iπ/4))
  | S         Wire              -- ^ S = T²
  | SDag      Wire              -- ^ S† = T†²
  | Rx        Double Wire       -- ^ Rx(θ): rotation about X by θ radians
  | Ry        Double Wire       -- ^ Ry(θ): rotation about Y by θ radians
  | Rz        Double Wire       -- ^ Rz(θ): rotation about Z by θ radians
  -- Two-qubit gates
  | CNOT      { control :: Wire, target :: Wire }  -- ^ Controlled-X
  | CZ        Wire Wire                            -- ^ Controlled-Z
  | SWAP      Wire Wire                            -- ^ Swap two qubits
  -- Three-qubit gates
  | Toffoli   Wire Wire Wire    -- ^ Toffoli / CCX: control1, control2, target
  | Fredkin   Wire Wire Wire    -- ^ Fredkin / CSWAP: control, target1, target2
  -- Measurement and lifecycle
  | QMeasure  Wire Int          -- ^ Measure qubit → classical bit index
  | QInit     Bool Wire         -- ^ Initialize wire to |0⟩ (False) or |1⟩ (True)
  | QDiscard  Wire              -- ^ Discard a wire (end of its lifetime)
  deriving (Show, Eq)

-- ── Wire allocation ───────────────────────────────────────────────────────────

-- | Allocate a fresh qubit wire, initialized to |0⟩.
qinit0 :: Circ Wire
qinit0 = Circ $ do
  s <- get
  let w = Wire (csCounter s)
  put s { csCounter = csCounter s + 1
        , csWires   = csWires s ++ [w]
        , csOps     = csOps s ++ [QInit False w]
        }
  return w

-- | Allocate a fresh qubit wire, initialized to |1⟩.
qinit1 :: Circ Wire
qinit1 = Circ $ do
  s <- get
  let w = Wire (csCounter s)
  put s { csCounter = csCounter s + 1
        , csWires   = csWires s ++ [w]
        , csOps     = csOps s ++ [QInit True w]
        }
  return w

-- ── Gate emission ─────────────────────────────────────────────────────────────

-- | Emit a QOp into the circuit being built.
emitOp :: QOp -> Circ ()
emitOp op = Circ $ modify (\s -> s { csOps = csOps s ++ [op] })

-- ── Circuit extraction ────────────────────────────────────────────────────────

-- | Run a Circ computation starting from an empty state.
-- Returns the result value and the final CircState (containing all ops).
buildCircuit :: Circ a -> (a, CircState)
buildCircuit (Circ m) = runState m initialCircState

-- | Run a Circ computation and extract just the op list and wire count.
extractOps :: Circ a -> ([QOp], Int)
extractOps circ =
  let (_, s) = buildCircuit circ
  in (csOps s, csCounter s)
