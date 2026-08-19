{-# LANGUAGE OverloadedStrings #-}
-- quipper/src/Quipper/Examples.hs
-- Concrete Quipper circuits lowered to QIRCircuit and printed as JSON.
--
-- Each example:
--   (1) Builds a Quipper Circ computation
--   (2) Lowers it to QIRCircuit via ToIR.toIR
--   (3) Prints JSON via ToJSON.qirToJSON
--
-- Examples:
--   bellState  — 2 qubits, H + CNOT + measure both
--   qft3       — 3-qubit QFT (H, controlled-Rz gates, SWAP)
--   toffoliGate — standalone Toffoli gate demonstration

module Quipper.Examples
  ( bellState
  , qft3
  , toffoliGate
  , runExamples
  ) where

import Data.Aeson (encode)
import qualified Data.ByteString.Lazy.Char8 as BL

import Quipper.Syntax
import Quipper.Primitives
import Quipper.ToIR
import QuantumIR
import ToJSON

-- ── Bell State ────────────────────────────────────────────────────────────────

-- | Bell state |Φ+⟩ = (|00⟩ + |11⟩)/√2
--
-- Circuit:
--   q0: ─[H]─●─── M→c0
--   q1: ──────X─── M→c1
--
-- Quipper representation: allocate q0, q1; apply H q0; CNOT q0 q1; measure both.
bellStateCirc :: Circ (Wire, Wire)
bellStateCirc = do
  q0 <- freshQubit
  q1 <- freshQubit
  hadamard q0
  cnot q0 q1
  measure q0 0
  measure q1 1
  return (q0, q1)

-- | Bell state lowered to QIRCircuit.
bellState :: Either String QIRCircuit
bellState = toIR bellStateCirc

-- ── 3-Qubit Quantum Fourier Transform ────────────────────────────────────────

-- | QFT on 3 qubits.
--
-- Standard decomposition (acting on |q2 q1 q0⟩ big-endian):
--
--   q0: ─[H]─[R2]────[R3]──────────────────SWAP─
--   q1: ──────●────────────[H]─[R2]─────────────
--   q2: ────────────────────●────────[H]────SWAP─
--
-- R_k = diag(1, exp(2πi/2^k)) = Rz(2π/2^k) up to global phase
--
-- We use the controlled-Rz decomposition:
--   controlled-R_k(ctrl, tgt) ≈ Rz(π/2^(k-1)) on target, controlled by ctrl
--   (implemented here as CZ variant; exact implementation uses Rz parametric)
--
-- For the IR, each controlled-Rz is emitted as a named CRz gate with param.
-- This is within the standard QIR gate set (parametric 2-qubit gate).
qft3Circ :: Circ (Wire, Wire, Wire)
qft3Circ = do
  q0 <- freshQubit
  q1 <- freshQubit
  q2 <- freshQubit

  -- QFT on q0 (most significant qubit, big-endian convention)
  hadamard q0
  controlledRz (pi / 2)      q1 q0    -- R_2: controlled by q1
  controlledRz (pi / 4)      q2 q0    -- R_3: controlled by q2

  -- QFT on q1
  hadamard q1
  controlledRz (pi / 2)      q2 q1    -- R_2: controlled by q2

  -- QFT on q2
  hadamard q2

  -- Bit-reversal SWAP (q0 ↔ q2 for 3 qubits; q1 stays)
  swapGate q0 q2

  return (q0, q1, q2)

-- | Emit a controlled-Rz gate: applies Rz(theta) on target controlled by ctrl.
-- Decomposition: CRz(θ) = Rz(θ/2) on tgt, CX ctrl tgt, Rz(-θ/2) on tgt, CX ctrl tgt.
-- This is the standard textbook decomposition into the {CX, Rz} gate set.
controlledRz :: Double -> Wire -> Wire -> Circ ()
controlledRz theta ctrl tgt = do
  rz (theta / 2)  tgt
  cnot ctrl tgt
  rz (negate (theta / 2)) tgt
  cnot ctrl tgt

-- | QFT(3) lowered to QIRCircuit.
qft3 :: Either String QIRCircuit
qft3 = toIR qft3Circ

-- ── Toffoli Gate ─────────────────────────────────────────────────────────────

-- | Standalone Toffoli (CCX) gate on 3 qubits.
--
-- Circuit:
--   q0: ─────●─────
--   q1: ─────●─────
--   q2: ─────X─────
--
-- The Toffoli gate is universal for classical reversible computation.
-- It requires exactly 7 T gates in the optimal decomposition (T-count = 7).
-- The IR emits it as a single "CCX" gate; backend compilers handle
-- the T-gate decomposition during synthesis.
toffoliCirc :: Circ (Wire, Wire, Wire)
toffoliCirc = do
  q0 <- freshQubit
  q1 <- freshQubit
  q2 <- freshQubit
  toffoli q0 q1 q2
  return (q0, q1, q2)

-- | Toffoli gate lowered to QIRCircuit.
toffoliGate :: Either String QIRCircuit
toffoliGate = toIR toffoliCirc

-- ── Runner ────────────────────────────────────────────────────────────────────

-- | Print all three examples as JSON to stdout.
-- Each circuit is preceded by a header line for readability.
runExamples :: IO ()
runExamples = do
  printExample "Bell State (|Phi+>)" bellState
  printExample "QFT on 3 qubits"    qft3
  printExample "Toffoli gate (CCX)"  toffoliGate

printExample :: String -> Either String QIRCircuit -> IO ()
printExample name result = do
  putStrLn $ "=== " ++ name ++ " ==="
  case result of
    Left  err -> putStrLn $ "ERROR: " ++ err
    Right c   -> do
      BL.putStrLn (encode (qirToJSON c))
      putStrLn $ "  qubits=" ++ show (irQubits c)
             ++ " depth=" ++ show (depth (irResources c))
             ++ " gates=" ++ show (gateCount (irResources c))
             ++ " T-count=" ++ show (tCount (irResources c))
      putStrLn ""
