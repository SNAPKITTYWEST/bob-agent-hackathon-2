# qft3.jl
#
# 3-qubit Quantum Fourier Transform (QFT) example.
#
# QFT_3 circuit (big-endian qubit ordering):
#   q1: H, then controlled-Rz(π/2) with q2, then controlled-Rz(π/4) with q3
#   q2: H, then controlled-Rz(π/2) with q3
#   q3: H
#   (Plus SWAP gates at the end, which we include as controlled ops)
#
# T-gate count analysis: QFT on n qubits uses O(n²) rotation gates.
# For 3 qubits:
#   Rz(π/2)  = S gate  (0 T gates)
#   Rz(π/4)  = T gate  (1 T gate each)
#   H gates  = 0 T gates
#
# T gates present: only the Rz(π/4) = T on qubit 1 from qubit 3 control
# Expected t_count = 1

include("../src/yao_types.jl")
include("../src/yao_circuit.jl")
include("../src/yao_to_ir.jl")

using Printf

println("=" ^ 60)
println("3-Qubit QFT Example — Yao.jl model")
println("=" ^ 60)

# ------------------------------------------------------------------
# QFT helper: phase gate Rz(2π / 2^k)
# ------------------------------------------------------------------
#
# In the standard QFT circuit, R_k = Rz(2π/2^k):
#   R_1 = Z  (phase π)
#   R_2 = S  (phase π/2)
#   R_3 = T  (phase π/4) ← counts toward t_count
#

Rk(k::Int) = Rz(2π / (2.0^k))

# ------------------------------------------------------------------
# Build QFT_3 circuit
#
# Standard decomposition (no final SWAP):
#   q1: H → ctrl-R2(q1,q2) → ctrl-R3(q1,q3)
#   q2: H → ctrl-R2(q2,q3)
#   q3: H
#
# Using Yao.jl model: control(nq, [ctrl], target_loc => Rz(angle))
# ------------------------------------------------------------------

println("\nBuilding QFT_3 circuit...")

# Layer 1: qubit 1
h1     = put(3, [1], H())
cr2_12 = control(3, [2], 1 => Rk(2))   # ctrl q2, target q1, phase π/2
cr3_13 = control(3, [3], 1 => Rk(3))   # ctrl q3, target q1, phase π/4 (T gate!)

# Layer 2: qubit 2
h2     = put(3, [2], H())
cr2_23 = control(3, [3], 2 => Rk(2))   # ctrl q3, target q2, phase π/2

# Layer 3: qubit 3
h3     = put(3, [3], H())

# Measurements
m_all  = measure(3, [1, 2, 3])

qft3 = chain(3,
    h1, cr2_12, cr3_13,   # qubit 1 section
    h2, cr2_23,            # qubit 2 section
    h3,                    # qubit 3 section
    m_all,
)

println("Circuit: chain(3,")
println("  put(3,[1],H()),")
println("  control(3,[2], 1=>Rz(π/2)),  # ctrl-R2")
println("  control(3,[3], 1=>Rz(π/4)),  # ctrl-R3 = T gate")
println("  put(3,[2],H()),")
println("  control(3,[3], 2=>Rz(π/2)),  # ctrl-R2")
println("  put(3,[3],H()),")
println("  measure(3,[1,2,3]),")
println(")")
println("\nnqubits(qft3) = $(nqubits(qft3))")

# ------------------------------------------------------------------
# Lower to QIR
# ------------------------------------------------------------------
ir = yao_to_ir(qft3)

println("\n" * "=" ^ 60)
println("Resource Analysis")
println("=" ^ 60)
resources = ir["resources"]
println("  gate_count : $(resources["gate_count"])")
println("  depth      : $(resources["depth"])")
println("  t_count    : $(resources["t_count"])  (T/Rz(π/4) gates)")
println("  width      : $(resources["width"]) qubits")

println("\nT-gate analysis:")
println("  H gates contribute 0 T gates each")
println("  S/Rz(π/2) gates contribute 0 T gates each")
println("  Rz(π/4) gates count as T gates for fault-tolerance cost")

t_gates_found = filter(op -> op["type"] == "gate" &&
    (op["name"] == "T" || (op["name"] == "Rz" && !isempty(op["params"]) &&
     abs(op["params"][1] - π/4) < 1e-9)), ir["ops"])
println("  Ops matching T criteria: $(length(t_gates_found))")

println("\n" * "=" ^ 60)
println("QuantumIR JSON")
println("=" ^ 60)

json_str = to_json(ir)
println(json_str)

println("\n" * "=" ^ 60)
println("Unsupported semantics (always non-empty):")
println("=" ^ 60)
for s in ir["metadata"]["unsupported"]
    println("  • $s")
end

@assert ir["source_lang"] == "yao"
@assert ir["qubits"] == 3
@assert !isempty(ir["metadata"]["unsupported"])
println("\nAssertions passed ✓")
