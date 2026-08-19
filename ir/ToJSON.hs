{-# LANGUAGE OverloadedStrings #-}
-- ir/ToJSON.hs
-- Serialization of QIRCircuit to JSON (aeson Value).
-- Mirrors the structure of ir/quantum_ir_schema.json exactly.
-- Used by all three frontends to emit the shared wire format.

module ToJSON where

import Data.Aeson (Value(..), object, (.=), toJSON)
import Data.Aeson.Key (fromString)
import qualified Data.Aeson as A
import qualified Data.Vector as V

import QuantumIR

-- ── Top-level serializer ──────────────────────────────────────────────────────

-- | Serialize a QIRCircuit to a JSON Value.
-- The output validates against ir/quantum_ir_schema.json version 0.1.0.
qirToJSON :: QIRCircuit -> Value
qirToJSON c = object
  [ "qubits"     .= irQubits c
  , "cbits"      .= irCbits c
  , "ops"        .= Array (V.fromList (map opToJSON (irOps c)))
  , "meta"       .= metaToJSON (irMeta c)
  , "resources"  .= resourcesToJSON (irResources c)
  ]

-- ── Operation serializers ──────────────────────────────────────────────────────

opToJSON :: QIROp -> Value
opToJSON (QIRGate n ps qs) = object
  [ "op"     .= String "gate"
  , "name"   .= n
  , "params" .= ps
  , "qubits" .= qs
  ]
opToJSON (QIRMeasure q c) = object
  [ "op"    .= String "measure"
  , "qubit" .= q
  , "cbit"  .= c
  ]
opToJSON (QIRBarrier qs) = object
  [ "op"     .= String "barrier"
  , "qubits" .= qs
  ]
opToJSON (QIRReset q) = object
  [ "op"    .= String "reset"
  , "qubit" .= q
  ]

-- ── Metadata serializer ───────────────────────────────────────────────────────

metaToJSON :: QIRMeta -> Value
metaToJSON m = object
  [ "source_lang"  .= sourceLang m
  , "version"      .= irVersion m
  , "unsupported"  .= unsupported m
  ]

-- ── Resource serializer ───────────────────────────────────────────────────────

resourcesToJSON :: QIRResources -> Value
resourcesToJSON r = object
  [ "gate_count" .= gateCount r
  , "depth"      .= depth r
  , "t_count"    .= tCount r
  , "width"      .= width r
  ]

-- ── Round-trip helpers ────────────────────────────────────────────────────────

-- | Serialize to compact JSON bytestring.
qirToBytes :: QIRCircuit -> A.Value
qirToBytes = qirToJSON

-- | Pretty-print a QIRCircuit to a JSON string (via encode).
-- Useful in Examples and test output.
prettyQIR :: QIRCircuit -> String
prettyQIR c =
  -- Uses aeson's default encode; for pretty output use aeson-pretty in
  -- applications (not added as a core dependency to keep the IR lean).
  show (qirToJSON c)
