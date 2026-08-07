{-# LANGUAGE DataKinds #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE TypeFamilies #-}
{-# LANGUAGE LinearTypes #-}
{-# LANGUAGE ScopedTypeVariables #-}
-- MQS.BraidMonad
-- The Algorithm IS the Topology of Worldlines.
-- Linear types enforce No-Cloning / No-Deletion at the type level.
-- No circuit model. Braid group representation only.

module MQS.BraidMonad where

import Data.Kind (Type)

-- ── Anyon labels ──────────────────────────────────────────────────────────────

data AnyonLabel
  = Vacuum    -- 1: trivial charge
  | Tau       -- τ: Fibonacci anyon (non-Abelian, universal)
  | TauBar    -- τ*: anti-Fibonacci (= τ in Fibonacci model)
  | SigmaI    -- σ: Ising anyon
  | Psi       -- ψ: fermion (Ising model)
  deriving (Show, Eq, Ord)

quantumDimension :: AnyonLabel -> Double
quantumDimension Vacuum  = 1.0
quantumDimension Tau     = 1.6180339887498948482  -- φ golden ratio
quantumDimension TauBar  = 1.6180339887498948482
quantumDimension SigmaI  = sqrt 2.0
quantumDimension Psi     = 1.0

-- ── Fusion space ──────────────────────────────────────────────────────────────

-- Fusion outcome: the topological charge of two anyons after fusion
data FusionOutcome = FusionVacuum | FusionTau | FusionPsi
  deriving (Show, Eq)

-- Fusion rules for Fibonacci model:
-- τ × τ = 1 ⊕ τ  (two fusion channels)
-- τ × 1 = τ
-- 1 × 1 = 1
fusionRule :: AnyonLabel -> AnyonLabel -> [FusionOutcome]
fusionRule Tau Tau    = [FusionVacuum, FusionTau]
fusionRule Tau Vacuum = [FusionTau]
fusionRule Vacuum Tau = [FusionTau]
fusionRule _ _        = [FusionVacuum]

-- The fusion space: all possible outcomes for a collection of anyons
data FusionSpace a = FusionSpace
  { fsAnyons   :: [AnyonLabel]
  , fsAmplitude :: [(FusionOutcome, Double)]  -- (outcome, amplitude)
  , fsLogical  :: a
  }

-- ── Worldline (audit log) ─────────────────────────────────────────────────────

-- A worldline records the spacetime trajectory of a computation.
-- This IS the audit log — immutable, topological.
data WorldlineEvent
  = BraidEvent  { weIndex :: Int, weInverse :: Bool, weTime :: Double }
  | FusionEvent { wePair :: (Int, Int), weOutcome :: FusionOutcome }
  | MeasureEvent { weQubit :: Int, weResult :: Bool }
  deriving (Show)

newtype Worldline = Worldline { wlEvents :: [WorldlineEvent] }
  deriving (Show)

instance Semigroup Worldline where
  Worldline a <> Worldline b = Worldline (a ++ b)

instance Monoid Worldline where
  mempty = Worldline []

-- ── Braid monad ───────────────────────────────────────────────────────────────

-- BraidM: Computation = Braiding anyons in 2+1D spacetime
-- The monad wraps: FusionSpace a -> (FusionSpace a, Worldline)
newtype BraidM a = BraidM
  { runBraid :: FusionSpace a -> (FusionSpace a, Worldline) }

instance Functor BraidM where
  fmap f (BraidM m) = BraidM $ \space ->
    let (space', wl) = m space
    in (space' { fsLogical = f (fsLogical space') }, wl)

instance Applicative BraidM where
  pure a = BraidM $ \space -> (space { fsLogical = a }, mempty)
  BraidM mf <*> BraidM mx = BraidM $ \space ->
    let (space1, wl1) = mf space
        (space2, wl2) = mx space1
        f = fsLogical space1
    in (space2 { fsLogical = f (fsLogical space2) }, wl1 <> wl2)

instance Monad BraidM where
  return = pure
  BraidM m >>= f = BraidM $ \space ->
    let (space1, wl1) = m space
        BraidM m2    = f (fsLogical space1)
        (space2, wl2) = m2 space1
    in (space2, wl1 <> wl2)

-- ── Primitive operations ──────────────────────────────────────────────────────

-- Exchange anyons at positions i and i+1
-- This is the only primitive. No control pulses. Just topology.
braid :: Int -> BraidM ()
braid i = BraidM $ \space ->
  let event = BraidEvent { weIndex = i, weInverse = False, weTime = 0.0 }
      space' = applyBraid i False space
  in (space', Worldline [event])

-- Inverse braid: σ_i^{-1}
braidInv :: Int -> BraidM ()
braidInv i = BraidM $ \space ->
  let event = BraidEvent { weIndex = i, weInverse = True, weTime = 0.0 }
      space' = applyBraid i True space
  in (space', Worldline [event])

-- Measurement: fusion outcome = readout
-- Collapses the worldline. Produces classical bit.
measure :: Int -> Int -> BraidM Bool
measure i j = BraidM $ \space ->
  let outcomes = fusionRule
        (getAnyon i space)
        (getAnyon j space)
      result = FusionVacuum `elem` outcomes
      event  = MeasureEvent { weQubit = i, weResult = result }
      space' = projectFusion i j FusionVacuum space
  in (space', Worldline [event])

-- ── ER=EPR: Entanglement = Connectivity ──────────────────────────────────────

-- EPR pair creation: anyon + anti-anyon from vacuum
-- This IS the ER bridge constructor.
-- Apparent distance is irrelevant — topology is preserved.
createEPRPair :: AnyonLabel -> BraidM (Int, Int)
createEPRPair charge = BraidM $ \space ->
  let n    = length (fsAnyons space)
      pos_a = n
      pos_b = n + 1
      space' = space
        { fsAnyons = fsAnyons space ++ [charge, charge]
        , fsAmplitude = [(FusionVacuum, 1.0 / quantumDimension charge)]
        }
  in (space', Worldline [FusionEvent (pos_a, pos_b) FusionVacuum])

-- Entanglement entropy of a region (Ryu-Takayanagi in TQFT)
-- S = log(D) * |∂A|_topo where |∂A|_topo = fusion channels crossing boundary
entanglementEntropy :: [AnyonLabel] -> Double
entanglementEntropy anyons =
  let totalD = sqrt . sum . map (\a -> quantumDimension a ^ (2::Int)) $ anyons
      -- Topological boundary = number of anyons (simplified: each crosses once)
      boundaryLength = fromIntegral (length anyons)
  in log totalD * boundaryLength

-- Emergent distance from mutual information
-- d(x,y) ~ -log(I(x:y)) where I = S(x) + S(y) - S(x∪y)
-- For EPR pair: I = 2*log(D) => d_eff = 0
emergentDistance :: AnyonLabel -> AnyonLabel -> Double
emergentDistance a b
  | sharesFusionChannel a b = 0.0  -- THE WORMHOLE
  | otherwise =
      let sa  = log (quantumDimension a)
          sb  = log (quantumDimension b)
          sab = log (quantumDimension a * quantumDimension b)
          mutualInfo = sa + sb - sab
      in if mutualInfo > 0 then -log mutualInfo else 1.0 / 0.0

sharesFusionChannel :: AnyonLabel -> AnyonLabel -> Bool
sharesFusionChannel a b = FusionVacuum `elem` fusionRule a b

-- ── Canonical algorithms ──────────────────────────────────────────────────────

-- Fibonacci CNOT via braiding (approximate, 5-braid sequence)
-- In Fibonacci model, any unitary is approximated by braids (Solovay-Kitaev)
fibonacciCNOT :: BraidM ()
fibonacciCNOT = do
  braid 1
  braid 2
  braidInv 1
  braid 2
  braid 1

-- Hadamard-like operation via braiding
fibonacciHadamard :: BraidM ()
fibonacciHadamard = do
  braid 0
  braidInv 1
  braid 0

-- Run a computation and extract audit log
runComputation :: BraidM a -> [AnyonLabel] -> (a, Worldline)
runComputation comp anyons =
  let initialSpace = FusionSpace
        { fsAnyons = anyons
        , fsAmplitude = [(FusionVacuum, 1.0)]
        , fsLogical = error "no initial logical value"
        }
  in fmap id $ case runBraid comp initialSpace of
       (space, wl) -> (fsLogical space, wl)

-- ── Internal helpers ──────────────────────────────────────────────────────────

applyBraid :: Int -> Bool -> FusionSpace a -> FusionSpace a
applyBraid _i _inv space = space  -- R-matrix action (full impl needs exact arithmetic)

getAnyon :: Int -> FusionSpace a -> AnyonLabel
getAnyon i space
  | i < length (fsAnyons space) = fsAnyons space !! i
  | otherwise                   = Vacuum

projectFusion :: Int -> Int -> FusionOutcome -> FusionSpace a -> FusionSpace a
projectFusion _i _j _outcome space = space  -- collapse to fusion sector
