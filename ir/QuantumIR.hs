{-# LANGUAGE DeriveGeneric #-}
-- ir/QuantumIR.hs
-- Shared Quantum Intermediate Representation — Haskell types.
-- This module is the single source of truth for the IR contract.
-- AGENT_01 (BOB/Quipper) produces these values.
-- AGENT_02 (NETON/Guppy) and AGENT_03 (PAX-CODER/Yao.jl) must implement
-- against ir/quantum_ir_schema.json, which mirrors these types exactly.
--
-- DESIGN INVARIANTS:
--   1. Every lowering must populate irMeta.unsupported explicitly.
--      An empty list means full representability — NOT "field omitted".
--   2. irResources.width == irQubits (enforced by smart constructors).
--   3. QIROp qubit indices are 0-based and < irQubits.
--   4. QIRMeasure cbit indices are 0-based and < irCbits.
--   5. No runtime exceptions — all failures are explicit in unsupported.

module QuantumIR where

import GHC.Generics (Generic)

-- ── Operation types ───────────────────────────────────────────────────────────

-- | A single quantum operation in program order.
--
-- Encoding rules:
--   QIRGate  — any named unitary gate; params in radians; qubits in gate-convention
--              order (control before target for 2-qubit gates).
--   QIRMeasure — destructive Z-basis measurement; result written to classical bit.
--   QIRBarrier — prevents gate commutation across this boundary (compiler hint).
--   QIRReset   — prepares qubit in |0⟩ (may be followed by X for |1⟩ init).
data QIROp
  = QIRGate
      { opName   :: String    -- ^ Gate name: "H", "CX", "T", "Rz", "CCX", …
      , opParams :: [Double]  -- ^ Angle parameters in radians. [] for non-parametric.
      , opQubits :: [Int]     -- ^ Qubit indices, 0-based, in gate-convention order.
      }
  | QIRMeasure
      { mQubit :: Int  -- ^ Qubit to measure (0-based).
      , mCbit  :: Int  -- ^ Classical bit to receive result (0-based).
      }
  | QIRBarrier
      { bQubits :: [Int]  -- ^ Qubits spanned by the barrier.
      }
  | QIRReset
      { rQubit :: Int  -- ^ Qubit to reset to |0⟩.
      }
  deriving (Show, Eq, Generic)

-- ── Resource counts ───────────────────────────────────────────────────────────

-- | Static resource estimates for a circuit.
--
-- gate_count: total QIRGate ops (measure/barrier/reset excluded).
-- depth:      critical-path length — longest sequential gate chain.
-- t_count:    number of T and Tdg gates (primary fault-tolerant resource).
-- width:      == irQubits (redundant but useful for self-contained records).
data QIRResources = QIRResources
  { gateCount :: Int  -- ^ Total gate operations.
  , depth     :: Int  -- ^ Critical-path depth.
  , tCount    :: Int  -- ^ T + Tdg gate count.
  , width     :: Int  -- ^ Circuit width (= qubit count).
  } deriving (Show, Eq, Generic)

emptyResources :: Int -> QIRResources
emptyResources w = QIRResources
  { gateCount = 0
  , depth     = 0
  , tCount    = 0
  , width     = w
  }

-- ── Provenance metadata ───────────────────────────────────────────────────────

-- | Metadata attached to every circuit: provenance, version, and explicit
-- declaration of unsupported semantics.
--
-- INVARIANT: `unsupported` is NEVER implicitly empty.
-- If the source language is fully representable, set unsupported = [].
-- If anything was dropped or approximated, list it here with a description.
-- Silent information loss is forbidden.
data QIRMeta = QIRMeta
  { sourceLang  :: String    -- ^ "quipper" | "guppy" | "yao"
  , irVersion   :: String    -- ^ "0.1.0" (must match schema $id version)
  , unsupported :: [String]  -- ^ Semantics NOT representable in this IR instance.
  } deriving (Show, Eq, Generic)

-- | Construct metadata for the Quipper frontend.
-- Pre-populated with the two Quipper-specific limitations.
quipperMeta :: [String] -> QIRMeta
quipperMeta extraUnsupported = QIRMeta
  { sourceLang  = "quipper"
  , irVersion   = "0.1.0"
  , unsupported =
      [ "higher-order circuit parameters (Quipper BoxedCircuit) — represented as flattened gate sequence"
      , "dynamic lifting (classical feedback) — measurement only"
      ] ++ extraUnsupported
  }

-- | Construct metadata for the Guppy frontend (AGENT_02 / NETON).
guppyMeta :: [String] -> QIRMeta
guppyMeta extraUnsupported = QIRMeta
  { sourceLang  = "guppy"
  , irVersion   = "0.1.0"
  , unsupported = extraUnsupported
  }

-- | Construct metadata for the Yao.jl frontend (AGENT_03 / PAX-CODER).
yaoMeta :: [String] -> QIRMeta
yaoMeta extraUnsupported = QIRMeta
  { sourceLang  = "yao"
  , irVersion   = "0.1.0"
  , unsupported = extraUnsupported
  }

-- ── Circuit ───────────────────────────────────────────────────────────────────

-- | A complete quantum circuit in the shared IR.
--
-- Construction: use `mkCircuit` to enforce invariants at build time.
data QIRCircuit = QIRCircuit
  { irQubits    :: Int            -- ^ Total qubit count (>= 1).
  , irCbits     :: Int            -- ^ Total classical bit count (>= 0).
  , irOps       :: [QIROp]        -- ^ Operations in program order.
  , irMeta      :: QIRMeta        -- ^ Provenance + unsupported semantics.
  , irResources :: QIRResources   -- ^ Static resource estimates.
  } deriving (Show, Eq, Generic)

-- | Smart constructor: validates width consistency and computes resources.
-- Returns Left with an error message if invariants are violated.
mkCircuit
  :: Int          -- ^ qubit count
  -> Int          -- ^ cbit count
  -> [QIROp]      -- ^ ops
  -> QIRMeta      -- ^ meta
  -> Either String QIRCircuit
mkCircuit q c ops meta
  | q < 1            = Left "mkCircuit: qubit count must be >= 1"
  | c < 0            = Left "mkCircuit: cbit count must be >= 0"
  | not qubitsBound  = Left "mkCircuit: gate references qubit index >= qubit count"
  | not cbitsBound   = Left "mkCircuit: measure references cbit index >= cbit count"
  | otherwise        = Right $ QIRCircuit
      { irQubits    = q
      , irCbits     = c
      , irOps       = ops
      , irMeta      = meta
      , irResources = computeResources q ops
      }
  where
    qubitsBound = all (opQubitsInBound q) ops
    cbitsBound  = all (opCbitsInBound c) ops

opQubitsInBound :: Int -> QIROp -> Bool
opQubitsInBound q (QIRGate _ _ qs)  = all (< q) qs
opQubitsInBound q (QIRMeasure mq _) = mq < q
opQubitsInBound q (QIRBarrier qs)   = all (< q) qs
opQubitsInBound q (QIRReset rq)     = rq < q

opCbitsInBound :: Int -> QIROp -> Bool
opCbitsInBound c (QIRMeasure _ mc) = mc < c
opCbitsInBound _ _                 = True

-- ── Resource computation ──────────────────────────────────────────────────────

-- | Compute static resource estimates from an op list.
-- Depth is a conservative estimate: counts layers of gates on distinct qubits.
computeResources :: Int -> [QIROp] -> QIRResources
computeResources q ops = QIRResources
  { gateCount = gc
  , depth     = computeDepth q ops
  , tCount    = tc
  , width     = q
  }
  where
    gates = [ op | op@(QIRGate {}) <- ops ]
    gc    = length gates
    tc    = length [ g | g@(QIRGate n _ _) <- gates, n `elem` ["T", "Tdg"] ]

-- | Compute circuit depth via qubit-last-use tracking.
-- depth(c) = max over all qubits of the layer index of the last gate on that qubit.
computeDepth :: Int -> [QIROp] -> Int
computeDepth q ops = maximum (0 : map snd (zip [0..] layers))
  where
    -- Assign each gate a layer: the layer is 1 + max(layer of last gate on each qubit used).
    -- We use a simple sequential pass — conservative but correct.
    layers = snd $ foldl assignLayer (replicate q 0, []) onlyGates
    onlyGates = [ op | op@(QIRGate {}) <- ops ]
    assignLayer (lastLayer, depths) g =
      let qs      = opQubits g
          myDepth = 1 + maximum (0 : map (lastLayer !!) qs)
          newLL   = foldr (\qi acc -> take qi acc ++ [myDepth] ++ drop (qi+1) acc) lastLayer qs
      in (newLL, depths ++ [myDepth])
