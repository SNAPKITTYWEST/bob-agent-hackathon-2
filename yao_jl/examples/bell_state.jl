# bell_state.jl
#
# Bell State example: (|00⟩ + |11⟩) / √2
#
# Demonstrates:
#   1. Circuit construction with chain/put/control
#   2. Statevector simulation
#   3. Lowering to QuantumIR JSON
#
# This is CLASSICAL STATEVECTOR SIMULATION. No quantum hardware.

# Load the Yao.jl model and simulation/IR modules
include("../src/yao_types.jl")
include("../src/yao_circuit.jl")
include("../src/yao_simulation.jl")
include("../src/yao_to_ir.jl")

using Printf

println("=" ^ 60)
println("Bell State Example — Yao.jl model")
println("Circuit: H on qubit 1, CNOT (ctrl=1, tgt=2), Measure both")
println("=" ^ 60)

# ------------------------------------------------------------------
# 1. Build the circuit
# ------------------------------------------------------------------
#
# Bell state preparation:
#   Step 1: H|0⟩ on qubit 1  →  (|0⟩ + |1⟩)/√2
#   Step 2: CNOT(ctrl=1, tgt=2)  →  (|00⟩ + |11⟩)/√2

circuit = chain(2,
    put(2, [1], H()),
    control(2, [1], 2 => X()),
    measure(2, [1, 2]),
)

println("\nCircuit structure:")
println("  chain(2,")
println("    put(2, [1], H()),      # H on qubit 1")
println("    control(2, [1], 2=>X()), # CNOT: ctrl=q1, tgt=q2")
println("    measure(2, [1,2]),     # measure both")
println("  )")
println("\nnqubits(circuit) = $(nqubits(circuit))")

# ------------------------------------------------------------------
# 2. Simulate
# ------------------------------------------------------------------
println("\n" * "=" ^ 60)
println("Statevector Simulation")
println("=" ^ 60)
println("\nInitial state: |00⟩ = [1+0i, 0, 0, 0]")

# Simulate without measure (MeasureBlock is no-op in statevector sim)
sim_circuit = chain(2,
    put(2, [1], H()),
    control(2, [1], 2 => X()),
)
sv = simulate(sim_circuit)

println("\nAfter H⊗I applied to |00⟩:")
# Intermediate step
sv_after_h = simulate(chain(2, put(2, [1], H())))
for (k, amp) in enumerate(sv_after_h)
    if abs(amp) > 1e-10
        lbl = basis_label(k-1, 2)
        @printf("  %s  α = %+.6f %+.6fim  |α|² = %.6f\n",
                lbl, real(amp), imag(amp), abs2(amp))
    end
end

println("\nAfter CNOT (Bell state):")
for (k, amp) in enumerate(sv)
    if abs(amp) > 1e-10
        lbl = basis_label(k-1, 2)
        @printf("  %s  α = %+.6f %+.6fim  |α|² = %.6f\n",
                lbl, real(amp), imag(amp), abs2(amp))
    end
end

println("\nExpected: |00⟩ coefficient = 1/√2 ≈ $(1/sqrt(2))")
println("          |11⟩ coefficient = 1/√2 ≈ $(1/sqrt(2))")

# Verify
@assert abs(abs(sv[1]) - 1/sqrt(2)) < 1e-10  "|00⟩ amplitude mismatch"
@assert abs(abs(sv[4]) - 1/sqrt(2)) < 1e-10  "|11⟩ amplitude mismatch"
@assert abs(sv[2]) < 1e-10                    "|01⟩ should be zero"
@assert abs(sv[3]) < 1e-10                    "|10⟩ should be zero"
println("\nSimulation verified: |00⟩ and |11⟩ amplitudes are 1/√2 ✓")

# ------------------------------------------------------------------
# 3. Lower to QuantumIR
# ------------------------------------------------------------------
println("\n" * "=" ^ 60)
println("QuantumIR JSON")
println("=" ^ 60)

ir = yao_to_ir(circuit)

println("\nVerification:")
println("  source_lang = \"$(ir["source_lang"])\"  (expected: yao)")
println("  qubits      = $(ir["qubits"])              (expected: 2)")
println("  cbits       = $(ir["cbits"])              (expected: 2)")
println("  ops count   = $(length(ir["ops"]))           (expected: 4: H, CX, measure×2)")
println("  unsupported = $(length(ir["metadata"]["unsupported"])) items (never empty)")

@assert ir["source_lang"] == "yao"
@assert ir["qubits"] == 2
@assert !isempty(ir["metadata"]["unsupported"])

json_str = to_json(ir)
println("\nJSON output:")
println(json_str)
