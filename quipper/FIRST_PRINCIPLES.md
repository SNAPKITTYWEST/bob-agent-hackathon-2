# Quipper Frontend — First Principles

Mathematical validation questions answered for each major component.

---

## 1. QIROp (Quantum Operation)

**WHAT IS THE MATHEMATICAL OBJECT?**
A quantum operation is a member of one of four semantic classes:
- Gate: a unitary map U : (C^2)^(tensor n) → (C^2)^(tensor n) acting on n qubits.
- Measure: a projective measurement in the Z-basis, selecting outcome 0 or 1 and collapsing the qubit.
- Barrier: a compiler ordering constraint — no mathematical content beyond sequencing.
- Reset: the completely positive trace-and-prepare map that discards a qubit and prepares |0⟩.

**WHAT IS ITS REPRESENTATION?**
An algebraic data type with four constructors: QIRGate (name, real parameters, qubit indices), QIRMeasure (qubit index, cbit index), QIRBarrier (qubit list), QIRReset (qubit index). Gate parameters are real angles in radians (Double). All qubit/cbit indices are non-negative integers, 0-based.

**WHAT OPERATIONS ARE VALID?**
- QIRGate: opQubits must be non-empty, distinct (a gate cannot act twice on the same qubit in one op), and all < irQubits.
- QIRMeasure: mQubit < irQubits, mCbit < irCbits.
- QIRBarrier: bQubits non-empty, all < irQubits.
- QIRReset: rQubit < irQubits.

**WHAT INVARIANTS MUST HOLD?**
1. Qubit indices in all ops are within [0, irQubits).
2. Cbit indices in all QIRMeasure ops are within [0, irCbits).
3. The op sequence is in program order (no reordering by the IR).
4. Gate name is from the standard set OR is a declared custom gate.

**HOW IS IT LOWERED?**
QOp (Quipper) → QIROp (IR): see `Quipper/ToIR.hs`.
- Single-qubit gates: direct name mapping (Hadamard → "H", T → "T", etc.).
- Two-qubit gates: CX for CNOT, CZ for CZ, SWAP for SWAP.
- Three-qubit: CCX for Toffoli, CSWAP for Fredkin.
- QInit False → QIRReset; QInit True → [QIRReset, QIRGate "X"].
- QDiscard → QIRBarrier (lifetime fence, no physical operation).
- QMeasure → QIRMeasure.

**HOW IS IT TESTED?**
QuipperSpec.hs checks: Bell state contains H + CX + 2 measures; Toffoli produces CCX; SWAP present in QFT.

**WHAT INFORMATION IS LOST?**
None per gate. Individual gates translate bijectively. The loss is at the circuit level: higher-order structure (BoxedCircuit looping, dynamic lifting) cannot be expressed in a flat op list.

**WHAT BACKEND ASSUMPTIONS EXIST?**
- Gate names are strings. Backend must maintain its own name→unitary mapping.
- "CCX" is treated as a single gate by the IR; fault-tolerant backends must decompose it into T gates (T-count = 7 for the optimal Selinger decomposition).
- "Rz" params are double-precision floats — exact arithmetic backends must round to their algebraic representation.

---

## 2. QIRCircuit (Circuit)

**WHAT IS THE MATHEMATICAL OBJECT?**
A quantum circuit is a directed acyclic graph (DAG) of unitary and non-unitary operations acting on a fixed register of n qubits and m classical bits. The circuit defines a completely positive trace-preserving (CPTP) map from (C^2)^(tensor n) × Bits^m to (C^2)^(tensor n) × Bits^m.

**WHAT IS ITS REPRESENTATION?**
A record: qubit count (Int), cbit count (Int), operation list (program-order [QIROp]), metadata (QIRMeta), and resource estimates (QIRResources). Represented in JSON per ir/quantum_ir_schema.json.

**WHAT OPERATIONS ARE VALID?**
- `mkCircuit q c ops meta` is the smart constructor: validates qubit/cbit bounds, then computes resources.
- The IR does not validate unitary commutativity or physical connectivity — those are backend concerns.
- Adding ops to an existing circuit requires rebuilding via mkCircuit.

**WHAT INVARIANTS MUST HOLD?**
1. irQubits >= 1.
2. irCbits >= 0.
3. irResources.width == irQubits.
4. All qubit/cbit indices in ops are in bounds (enforced by mkCircuit).
5. irMeta.unsupported is explicitly set (never absent or undefined).
6. irMeta.version == "0.1.0" for this schema generation.

**HOW IS IT LOWERED?**
`toIR :: Circ a -> Either String QIRCircuit` runs the Circ monad, extracts ops and wire count, constructs metadata with unsupported declarations, and calls mkCircuit.

**HOW IS IT TESTED?**
QuipperSpec.hs: qubit count, op count, gate count, depth, T-count, JSON roundtrip.

**WHAT INFORMATION IS LOST?**
- The Quipper circuit structure (subroutine hierarchy, BoxedCircuit reuse) is flattened to a linear sequence.
- Dynamic lifting (classical feedback between measurements and future gates) is dropped — the IR is a static circuit. This is declared in unsupported.
- Wire linearity enforcement at the type level is lost (Haskell Wire is just Int).

**WHAT BACKEND ASSUMPTIONS EXIST?**
- Backends receive a flat, ordered list of operations. They may build a DAG from it.
- Gate set support varies by backend. "CCX" and "CSWAP" may require decomposition.
- The circuit model is gate-based (not pulse-level, not continuous-time).

---

## 3. QIRMeta (Metadata)

**WHAT IS THE MATHEMATICAL OBJECT?**
Provenance annotation: a structured record of where the circuit came from, which schema version it conforms to, and which source-language semantics were dropped during lowering.

**WHAT IS ITS REPRESENTATION?**
Three fields: sourceLang (String, one of "quipper"|"guppy"|"yao"), irVersion (String, currently "0.1.0"), unsupported ([String]).

**WHAT OPERATIONS ARE VALID?**
- Read-only after construction. The smart constructors `quipperMeta`, `guppyMeta`, `yaoMeta` pre-populate the standard unsupported items for each language.
- Extra unsupported items are appended by the caller.

**WHAT INVARIANTS MUST HOLD?**
CRITICAL: `unsupported` is NEVER silently empty unless the source language is fully representable in the IR. Every approximation, dropped feature, or flattened abstraction MUST appear as a human-readable string in this list. This is the transparency invariant of the shared IR.

**HOW IS IT LOWERED?**
Not lowered — it is constructed by the frontend and carried through intact.

**HOW IS IT TESTED?**
QuipperSpec.hs: checks that unsupported contains "higher-order circuit parameters" and "dynamic lifting" for all Quipper circuits.

**WHAT INFORMATION IS LOST?**
Nothing — this field exists specifically to prevent information loss from being silent.

**WHAT BACKEND ASSUMPTIONS EXIST?**
None. Backends must surface `unsupported` to users or logs when non-empty.

---

## 4. QIRResources (Resource Estimates)

**WHAT IS THE MATHEMATICAL OBJECT?**
A static analysis of circuit resource requirements: gate count (total unitary ops), circuit depth (critical-path length), T-count (fault-tolerant magic state cost), and width (qubit count).

**WHAT IS ITS REPRESENTATION?**
Four non-negative integers: gateCount, depth, tCount, width.

**WHAT OPERATIONS ARE VALID?**
`computeResources :: Int -> [QIROp] -> QIRResources` computes all four values from a qubit count and op list. The depth algorithm assigns each gate a layer equal to 1 + max(layers of its qubit's previous gates).

**WHAT INVARIANTS MUST HOLD?**
1. gateCount >= 0; depth >= 0; tCount >= 0; width >= 1.
2. tCount <= gateCount (T gates are a subset of all gates).
3. depth <= gateCount (sequential circuit is worst case).
4. width == irQubits (always consistent with the circuit it describes).

**HOW IS IT LOWERED?**
Computed by `computeResources` inside `mkCircuit`. The depth computation is a conservative single-pass estimate: correct for acyclic gate ordering, conservative when commutation could reduce layers.

**HOW IS IT TESTED?**
QuipperSpec.hs: depth > 2 for QFT(3); T-count = 0 for Bell; width == qubit count for all; depth >= 1 for all circuits with gates.

**WHAT INFORMATION IS LOST?**
The depth estimate is conservative: commutable gates are not reordered. A true depth requires DAG compilation, which is a backend concern. The `depth` field here is an upper bound, not a tight bound.

**WHAT BACKEND ASSUMPTIONS EXIST?**
Backends may improve depth by DAG-based gate commutation. The IR's depth is a hint, not a contract.

---

## 5. Wire and Circ Monad (Quipper Syntax)

**WHAT IS THE MATHEMATICAL OBJECT?**
A quantum wire is a linear type resource: a named qubit whose state evolves through time. The Circ monad is a state threading construction: `Circ a = CircState -> (a, CircState)`, accumulating operations and wire allocations.

**WHAT IS ITS REPRESENTATION?**
`Wire = Wire Int` (a named qubit index). `Circ a = Circ (State CircState a)` where CircState holds accumulated ops, live wires, counter, and cbit count.

**WHAT OPERATIONS ARE VALID?**
- Wire allocation: `qinit0`, `qinit1` (fresh qubit, |0⟩ or |1⟩).
- Gate application: any function `Wire -> Circ ()` or `Wire -> Wire -> Circ ()` etc.
- Measurement: `measure :: Wire -> Int -> Circ ()`.
- Discard: `qdiscard :: Wire -> Circ ()`.
The monad ensures sequential composition (bind respects program order).

**WHAT INVARIANTS MUST HOLD?**
1. Each Wire allocated by qinit0/qinit1 gets a unique index.
2. Gates are accumulated in `csOps` in the order they are called (left-to-right in do-notation).
3. csCounter strictly increases — wire indices are never reused.

**HOW IS IT LOWERED?**
`buildCircuit :: Circ a -> (a, CircState)` runs the monad. `toIR` then calls `buildCircuit` and maps `csOps` to `[QIROp]` via `qopToQIROp`.

**HOW IS IT TESTED?**
QuipperSpec.hs tests the lowered output. The monad itself is implicitly tested because wrong ordering would produce wrong op counts and gate sequences.

**WHAT INFORMATION IS LOST?**
Linear type enforcement: in the real Quipper library, GHC's type system (with linear types extension) prevents a wire from being used after measurement or discard. Here, `Wire` is just `Int` — misuse is a runtime error, not a compile-time error. This is noted in Syntax.hs.

**WHAT BACKEND ASSUMPTIONS EXIST?**
None. The monad is a pure computation model; backends receive only the QIRCircuit after lowering.
