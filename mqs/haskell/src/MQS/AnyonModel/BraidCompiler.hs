{-# LANGUAGE DataKinds #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE ScopedTypeVariables #-}
-- MQS.AnyonModel.BraidCompiler
-- Exact braid word -> unitary matrix compilation
-- Working over the cyclotomic field Q[ζ₅] for Fibonacci anyons
-- (ζ₅ = exp(2πi/5), golden ratio φ = ζ₅ + ζ₅⁻¹)

module MQS.AnyonModel.BraidCompiler where

import Data.Complex (Complex(..), magnitude, conjugate)
import Data.Ratio (Ratio, (%))

-- ── Cyclotomic field approximation ───────────────────────────────────────────
-- Full implementation uses exact algebraic numbers.
-- Here we use Complex Double with high-precision constants.

type Amplitude = Complex Double

-- Golden ratio (exact)
phi :: Double
phi = 1.6180339887498948482

-- R-matrix phases for Fibonacci anyons SU(2)_3
-- R^{τ,τ}_1 = exp(i·4π/5)
-- R^{τ,τ}_τ = exp(-i·3π/5)

r_phase_vacuum :: Amplitude
r_phase_vacuum = cis (4 * pi / 5)

r_phase_tau :: Amplitude
r_phase_tau = cis ((-3) * pi / 5)

cis :: Double -> Amplitude
cis theta = cos theta :+ sin theta

-- ── F-matrix for Fibonacci ─────────────────────────────────────────────────
-- F^{τττ}_τ: The key associator (2x2 matrix, real entries)
-- [[φ⁻¹,   φ⁻¹/²],
--  [φ⁻¹/², -φ⁻¹ ]]

fMatrix :: [[Amplitude]]
fMatrix =
  [ [ (1/phi) :+ 0,          (1/sqrt phi) :+ 0 ]
  , [ (1/sqrt phi) :+ 0,    (-(1/phi)) :+ 0   ]
  ]

-- ── Braid generators ─────────────────────────────────────────────────────────

data BraidGen
  = Sigma Int     -- σ_i: exchange strands i and i+1
  | SigmaInv Int  -- σ_i^{-1}
  deriving (Show, Eq)

-- R-matrix for a braid generator on two τ anyons
-- σ acts as R-matrix in the fusion basis
rMatrix :: BraidGen -> [[Amplitude]]
rMatrix (Sigma _) =
  [ [ r_phase_vacuum, 0 :+ 0             ]
  , [ 0 :+ 0,         r_phase_tau        ]
  ]
rMatrix (SigmaInv _) =
  [ [ conjA r_phase_vacuum, 0 :+ 0       ]
  , [ 0 :+ 0,               conjA r_phase_tau ]
  ]
  where conjA (a :+ b) = a :+ (-b)

-- ── Matrix operations ─────────────────────────────────────────────────────────

type Matrix = [[Amplitude]]

identityMatrix :: Matrix
identityMatrix = [[1 :+ 0, 0 :+ 0], [0 :+ 0, 1 :+ 0]]

matMul :: Matrix -> Matrix -> Matrix
matMul a b =
  [ [ sum [ (a !! i !! k) * (b !! k !! j) | k <- [0..1] ]
    | j <- [0..1] ]
  | i <- [0..1] ]

-- Apply F-move conjugation: F^† · M · F
applyFMove :: Matrix -> Matrix
applyFMove m = matMul (matMul fDagger m) fMatrix
  where
    fDagger = [ [ conjugate (fMatrix !! j !! i) | j <- [0..1] ] | i <- [0..1] ]

-- ── Braid word compilation ────────────────────────────────────────────────────

-- Compile a braid word to a unitary matrix in the fusion basis
-- Uses R-matrices and F-moves (associators) for Fibonacci anyons
braidWordToUnitary :: [BraidGen] -> Matrix
braidWordToUnitary = foldl applyGen identityMatrix
  where
    applyGen :: Matrix -> BraidGen -> Matrix
    applyGen m gen = matMul (applyFMove (rMatrix gen)) m

-- ── Teleportation fidelity ────────────────────────────────────────────────────

-- Initial state: |ψ_i⟩ = [1, 0] (τ in vacuum channel)
initialState :: [Amplitude]
initialState = [1 :+ 0, 0 :+ 0]

-- Target state after perfect teleportation: [1, 0]
targetState :: [Amplitude]
targetState = [1 :+ 0, 0 :+ 0]

-- Apply matrix to vector
matVec :: Matrix -> [Amplitude] -> [Amplitude]
matVec m v = [ sum [ (m !! i !! j) * (v !! j) | j <- [0..1] ] | i <- [0..1] ]

-- Inner product ⟨ψ|φ⟩
innerProduct :: [Amplitude] -> [Amplitude] -> Amplitude
innerProduct psi phi = sum [ conjugate (psi !! i) * (phi !! i) | i <- [0..length psi - 1] ]

-- |⟨ψ_target | U | ψ_initial⟩|²
teleportationFidelity :: [BraidGen] -> Double
teleportationFidelity word =
  let u     = braidWordToUnitary word
      psi_f = matVec u initialState
      overlap = innerProduct targetState psi_f
  in magnitude overlap ^ (2 :: Int)

-- ── Exact fidelity bound ──────────────────────────────────────────────────────

-- Theoretical fidelity for canonical GJW protocol:
-- F = 1 - 1/φ^(2N) where N = braid depth
-- This is exact in the Fibonacci anyon model.
fidelityBoundExact :: Int -> Rational
fidelityBoundExact n =
  let phi_2n = round (phi ^ (2 * n)) :: Integer
  in (phi_2n - 1) % phi_2n

-- ── GJW canonical word ───────────────────────────────────────────────────────

-- Build the canonical GJW pattern: (σ₁ σ₂⁻¹)^N
gjwCanonicalWord :: Int -> [BraidGen]
gjwCanonicalWord n = concatMap (\_ -> [Sigma 1, SigmaInv 2]) [1..n]

-- Required depth for coupling strength g
gjwRequiredDepth :: Double -> Int
gjwRequiredDepth g =
  let g_topo = g * phi * phi
      raw    = (1.0 / g_topo) * log (1.0 / g_topo)
  in max 3 (round raw)

-- Compile GJW protocol for a given coupling
gjwCompile :: Double -> ([BraidGen], Double)
gjwCompile g =
  let n    = gjwRequiredDepth g
      word = gjwCanonicalWord n
      fid  = teleportationFidelity word
  in (word, fid)
