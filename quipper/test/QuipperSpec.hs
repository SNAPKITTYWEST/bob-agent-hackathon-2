-- quipper/test/QuipperSpec.hs
-- HSpec test suite for the Quipper frontend and shared IR.
--
-- Test strategy:
--   - Structural tests: check qubit/op counts on canonical circuits
--   - Resource tests: depth/T-count on QFT and Toffoli
--   - Metadata invariant: unsupported list is always explicit (never absent)
--   - JSON roundtrip: gate count survives encode → decode

module QuipperSpec (spec) where

import Test.Hspec
import Data.Aeson (encode, decode, Value(..))
import qualified Data.Aeson as A
import qualified Data.Aeson.KeyMap as KM
import qualified Data.Vector as V
import Data.Maybe (fromMaybe, isJust)

import Quipper.Syntax
import Quipper.Primitives
import Quipper.ToIR
import Quipper.Examples
import QuantumIR
import ToJSON

spec :: Spec
spec = do
  describe "Bell state" bellStateSpec
  describe "QFT(3)" qft3Spec
  describe "Toffoli gate" toffoliSpec
  describe "IR metadata invariants" metaSpec
  describe "JSON roundtrip" jsonRoundtripSpec
  describe "Resource computation" resourceSpec

-- ── Bell state ────────────────────────────────────────────────────────────────

bellStateSpec :: Spec
bellStateSpec = do
  let circuit = case bellState of
        Right c -> c
        Left e  -> error ("bellState failed: " ++ e)

  it "has exactly 2 qubits" $
    irQubits circuit `shouldBe` 2

  it "has exactly 2 classical bits" $
    irCbits circuit `shouldBe` 2

  it "has exactly 5 ops (reset0, reset1, H, CX, measure0, measure1)" $
    -- QInit False q0 → QIRReset q0
    -- QInit False q1 → QIRReset q1
    -- Hadamard q0    → QIRGate "H"
    -- CNOT q0 q1    → QIRGate "CX"
    -- QMeasure q0 0 → QIRMeasure
    -- QMeasure q1 1 → QIRMeasure
    length (irOps circuit) `shouldBe` 6

  it "contains an H gate" $
    any isHadamard (irOps circuit) `shouldBe` True

  it "contains a CX gate" $
    any isCX (irOps circuit) `shouldBe` True

  it "contains 2 measure ops" $
    length (filter isMeasure (irOps circuit)) `shouldBe` 2

  it "has gate count of 2 (H and CX, excluding resets and measures)" $
    gateCount (irResources circuit) `shouldBe` 2

  it "has T-count of 0 (no T gates in Bell circuit)" $
    tCount (irResources circuit) `shouldBe` 0

-- ── QFT(3) ────────────────────────────────────────────────────────────────────

qft3Spec :: Spec
qft3Spec = do
  let circuit = case qft3 of
        Right c -> c
        Left e  -> error ("qft3 failed: " ++ e)

  it "has exactly 3 qubits" $
    irQubits circuit `shouldBe` 3

  it "has depth > 2" $
    depth (irResources circuit) > 2 `shouldBe` True

  it "contains at least 3 H gates (one per qubit)" $ do
    let hGates = length (filter isHadamard (irOps circuit))
    hGates >= 3 `shouldBe` True

  it "contains at least 1 SWAP gate (bit-reversal)" $
    any isSWAP (irOps circuit) `shouldBe` True

  it "contains Rz gates (for controlled-phase rotations)" $
    any isRz (irOps circuit) `shouldBe` True

-- ── Toffoli gate ──────────────────────────────────────────────────────────────

toffoliSpec :: Spec
toffoliSpec = do
  let circuit = case toffoliGate of
        Right c -> c
        Left e  -> error ("toffoliGate failed: " ++ e)

  it "has exactly 3 qubits" $
    irQubits circuit `shouldBe` 3

  it "contains a CCX gate" $
    any isCCX (irOps circuit) `shouldBe` True

  it "has gate count >= 1" $
    gateCount (irResources circuit) >= 1 `shouldBe` True

-- ── Metadata invariants ───────────────────────────────────────────────────────

metaSpec :: Spec
metaSpec = do
  it "Bell state: unsupported list is never absent (explicit, non-null)" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    -- unsupported must be a concrete list (possibly empty, but present)
    let u = unsupported (irMeta c)
    isJust (Just u) `shouldBe` True

  it "Bell state: source_lang is 'quipper'" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    sourceLang (irMeta c) `shouldBe` "quipper"

  it "Bell state: version is '0.1.0'" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    irVersion (irMeta c) `shouldBe` "0.1.0"

  it "Bell state: unsupported contains BoxedCircuit declaration" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    let u = unsupported (irMeta c)
    any ("higher-order circuit parameters" `isInfixOf`) u `shouldBe` True

  it "Bell state: unsupported contains dynamic lifting declaration" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    let u = unsupported (irMeta c)
    any ("dynamic lifting" `isInfixOf`) u `shouldBe` True

  it "QFT(3): unsupported is explicit" $ do
    let c = case qft3 of { Right x -> x; Left e -> error e }
    isJust (Just (unsupported (irMeta c))) `shouldBe` True

  it "Toffoli: unsupported is explicit" $ do
    let c = case toffoliGate of { Right x -> x; Left e -> error e }
    isJust (Just (unsupported (irMeta c))) `shouldBe` True

-- ── JSON roundtrip ────────────────────────────────────────────────────────────

jsonRoundtripSpec :: Spec
jsonRoundtripSpec = do
  it "Bell state gate_count survives encode → decode" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    let json    = qirToJSON c
    let encoded = encode json
    let decoded = decode encoded :: Maybe Value
    case decoded of
      Nothing -> expectationFailure "JSON decode failed"
      Just v  -> do
        let resources = lookupKey "resources" v
        case resources of
          Just (Object rm) ->
            case KM.lookup "gate_count" rm of
              Just (Number n) ->
                round n `shouldBe` gateCount (irResources c)
              _ -> expectationFailure "gate_count not found in resources"
          _ -> expectationFailure "resources not found in JSON"

  it "Bell state: JSON has 'ops' array" $ do
    let c = case bellState of { Right x -> x; Left e -> error e }
    let v = qirToJSON c
    isJust (lookupKey "ops" v) `shouldBe` True

  it "QFT(3): JSON has meta.source_lang = 'quipper'" $ do
    let c = case qft3 of { Right x -> x; Left e -> error e }
    let v = qirToJSON c
    case lookupKey "meta" v of
      Just (Object m) ->
        case KM.lookup "source_lang" m of
          Just (String s) -> s `shouldBe` "quipper"
          _ -> expectationFailure "source_lang not a string"
      _ -> expectationFailure "meta not found"

-- ── Resource computation ──────────────────────────────────────────────────────

resourceSpec :: Spec
resourceSpec = do
  it "width == qubit count for all examples" $ do
    let check e = case e of
          Right c -> width (irResources c) `shouldBe` irQubits c
          Left e' -> expectationFailure e'
    check bellState
    check qft3
    check toffoliGate

  it "depth >= 1 for any non-empty gate circuit" $ do
    let check name e = case e of
          Right c
            | gateCount (irResources c) > 0 ->
                depth (irResources c) >= 1 `shouldBe` True
            | otherwise -> return ()
          Left e' -> expectationFailure (name ++ ": " ++ e')
    check "bellState" bellState
    check "qft3"      qft3
    check "toffoli"   toffoliGate

-- ── Predicates ───────────────────────────────────────────────────────────────

isHadamard :: QIROp -> Bool
isHadamard (QIRGate "H" _ _) = True
isHadamard _                 = False

isCX :: QIROp -> Bool
isCX (QIRGate "CX" _ _) = True
isCX _                   = False

isCCX :: QIROp -> Bool
isCCX (QIRGate "CCX" _ _) = True
isCCX _                    = False

isMeasure :: QIROp -> Bool
isMeasure (QIRMeasure {}) = True
isMeasure _               = False

isSWAP :: QIROp -> Bool
isSWAP (QIRGate "SWAP" _ _) = True
isSWAP _                    = False

isRz :: QIROp -> Bool
isRz (QIRGate "Rz" _ _) = True
isRz _                   = False

-- ── Helpers ───────────────────────────────────────────────────────────────────

lookupKey :: String -> Value -> Maybe Value
lookupKey k (Object o) = KM.lookup (A.fromString k) o
lookupKey _ _          = Nothing

isInfixOf :: String -> String -> Bool
isInfixOf needle haystack = go needle haystack
  where
    go [] _            = True
    go _  []           = False
    go n  h
      | take (length n) h == n = True
      | otherwise               = go n (tail h)
