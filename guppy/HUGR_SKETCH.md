# HUGR Sketch — Hierarchical Unified Graph Representation

## What is HUGR?

HUGR (Hierarchical Unified Graph Representation) is the intermediate
representation (IR) used by Quantinuum's Guppy quantum programming
language.  It was designed as a general-purpose IR for quantum programs
that captures both classical control flow and quantum data flow in a
single unified graph structure.

Key design goals of HUGR:

- **Hierarchical**: operations can be nested — a "function definition"
  node contains a graph of its body, a "conditional" node contains its
  branches, etc.
- **Data-flow**: edges in the graph represent data dependencies, not
  execution order.  Parallelism is implicit in the absence of edges.
- **Port-typed**: every node has named input and output ports with
  explicit types.  A qubit flowing through the graph is an edge with
  type `Qubit`.
- **Linear types enforced structurally**: a `Qubit`-typed edge can
  connect exactly one source port to exactly one target port.  The
  graph structure itself prevents copying or dropping qubits — there
  is no way to draw a fork in a linear edge.

HUGR is specified by the `hugr-core` Rust library (Quantinuum/hugr
on GitHub) and is the compilation target of `guppylang`.

---

## How Guppy compiles to HUGR

1. **Parse**: Guppy source is Python with decorator-based annotations.
   The `@guppy` decorator invokes Guppy's compiler on the decorated
   function.

2. **Type inference**: Guppy's type checker infers ownership for every
   variable.  `Qubit` variables are linear; classical values are
   unrestricted.  Every use-site is checked at compile time.

3. **HUGR construction**: Each Guppy expression/statement maps to a
   HUGR node.  Function arguments become input ports.  Gate applications
   become `ExtensionOp` nodes with Qubit-typed input and output ports.
   Measurement becomes a node with a Qubit input and a Bool output.

4. **Passes**: HUGR supports optimisation passes (gate fusion, constant
   folding, routing) that operate on the graph structure while
   preserving type invariants.

5. **Backend emission**: HUGR can be lowered to OpenQASM, QIR (LLVM),
   or hardware-specific representations.

---

## What our Python simulation captures

| Feature | Real Guppy/HUGR | Our simulation |
|---------|-----------------|----------------|
| Linear qubit ownership | Compile-time type error | Runtime LinearityViolation |
| Classical/quantum boundary | Structural port types | measure() returns ClassicalBit |
| Gate application semantics | HUGR ExtensionOp nodes | GuppyOp records in a list |
| No-cloning enforcement | Cannot draw a forked edge | .consume() raises on reuse |
| Operation ordering | Data-flow DAG (parallel if no edge) | Sequential list (no parallelism) |
| Nested control flow | Hierarchical graph nodes | Not modelled |
| Dependent types | Full type language | Not modelled |
| Inductive type recursion | Supported | Not modelled |
| Compile-time verification | Yes | Runtime only |
| HUGR passes/optimisations | Yes (separate pass pipeline) | Not modelled |

---

## What is lost in our simulation

**Graph structure**: HUGR is a DAG.  Our simulation records operations
in a flat list (a tape).  We lose the explicit data-flow edges between
nodes, which means we cannot recover parallelism from our IR.

**Port typing**: In HUGR every node port has a type.  Our `GuppyOp`
stores qubit indices as integers — the structural type information is
gone.

**Hierarchical nesting**: HUGR represents loops, conditionals, and
function definitions as nested subgraphs.  Our simulation has no
nesting concept.

**Optimisation pass results**: A real Guppy compiler would run HUGR
optimisation passes before emitting QIR.  Our simulation emits gates
in the order they were written, which may not be optimal.

**Compile-time vs runtime checking**: Real Guppy catches linearity
violations during Python import (at decorator evaluation time).  Our
simulation catches them when the gate function is actually called.

---

## How our QIR mapping differs from actual HUGR

| Aspect | HUGR | Our QIR (QuantumIR v0.1) |
|--------|------|--------------------------|
| Representation | Graph (nodes + edges) | Flat op list |
| Parallelism | Explicit (absence of edges) | Lost (sequential tape) |
| Types on wires | Qubit, Bool, Int, etc. | Implicit by op type |
| Control flow | Conditional nodes, loops | Not representable |
| Nesting | Yes | No |
| Metadata | HUGR extension system | Fixed `unsupported` list |
| Backend target | Backend-specific lowering | Any backend reading QIR JSON |

The `unsupported` field in every QIR output document explicitly records
the HUGR semantics that were lost during lowering.  Consumers of QIR
MUST NOT assume these semantics are preserved.

---

*This document is part of the AGENT_02 (NETON) Guppy frontend.*
*See FIRST_PRINCIPLES.md for the full mathematical specification.*
