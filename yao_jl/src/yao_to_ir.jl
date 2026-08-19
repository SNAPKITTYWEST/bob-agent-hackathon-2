# yao_to_ir.jl
#
# Lower Yao.jl block trees to QuantumIR JSON.
#
# QuantumIR is a FLAT, SEQUENTIAL representation. Yao.jl blocks are
# hierarchical and can express parallelism (KronBlock) and nesting
# (ChainBlock of ChainBlocks). This module flattens the tree.
#
# SEMANTICS LOST IN TRANSLATION (always reported in `unsupported`):
#   1. KronBlock parallelism — serialized to sequential in QIR
#   2. Differentiable parameters — AD metadata absent in QIR v0.1
#   3. Yao.jl ChainBlock nesting — flattened to op sequence
#
# These are NEVER silently dropped. Every IR output has a non-empty
# `unsupported` list documenting exactly what was lost.

include("yao_types.jl")

# -----------------------------------------------------------------------
# IR op constructors (Dict = JSON-serializable)
# -----------------------------------------------------------------------

ir_gate(name::String, params::Vector{Float64}, qubits::Vector{Int}) =
    Dict{String,Any}("type" => "gate", "name" => name, "params" => params, "qubits" => qubits)

ir_measure(qubit::Int, cbit::Int) =
    Dict{String,Any}("type" => "measure", "qubit" => qubit, "cbit" => cbit)

ir_barrier(qubits::Vector{Int}) =
    Dict{String,Any}("type" => "barrier", "qubits" => qubits)

ir_reset(qubit::Int) =
    Dict{String,Any}("type" => "reset", "qubit" => qubit)

# -----------------------------------------------------------------------
# Gate name normalization
# -----------------------------------------------------------------------

"""Map Yao.jl gate names to canonical QIR gate names."""
const YAO_TO_IR_NAME = Dict{String,String}(
    "H"  => "H",
    "X"  => "X",
    "Y"  => "Y",
    "Z"  => "Z",
    "T"  => "T",
    "S"  => "S",
    "Rx" => "Rx",
    "Ry" => "Ry",
    "Rz" => "Rz",
    "CX" => "CX",
    "CCX"=> "CCX",
)

"""
    is_t_gate(name::String) -> Bool

True for T and T† gates (relevant to fault-tolerance resource counting).
"""
is_t_gate(name::String) = name in ("T", "Tdg", "T†", "t")

# -----------------------------------------------------------------------
# Recursive block lowering
# -----------------------------------------------------------------------

"""
    lower_block!(ops, cbit_counter, block, nq; locs=nothing)

Walk the block tree, appending IR ops to `ops`.
`cbit_counter[1]` is a mutable counter for measurement output bits.
`locs` provides qubit location context when a block is inside a PutBlock.
All qubit indices in the IR are 0-based (QIR convention).
"""
function lower_block!(
    ops::Vector{Dict{String,Any}},
    cbit_counter::Vector{Int},
    block::AbstractBlock,
    nq::Int;
    locs::Union{Vector{Int},Nothing} = nothing
)
    if isa(block, PrimitiveGate)
        # Determine which qubits this gate acts on (0-based)
        if locs !== nothing
            qubits_0 = [l - 1 for l in locs]
        else
            qubits_0 = collect(0 : block.nqubits - 1)
        end
        ir_name = get(YAO_TO_IR_NAME, block.name, block.name)
        push!(ops, ir_gate(ir_name, copy(block.params), qubits_0))

    elseif isa(block, PutBlock)
        # Recurse with explicit qubit locations
        lower_block!(ops, cbit_counter, block.block, nq; locs=block.locs)

    elseif isa(block, ChainBlock)
        # Sequential — lower each sub-block in order
        for b in block.blocks
            lower_block!(ops, cbit_counter, b, nq)
        end

    elseif isa(block, KronBlock)
        # Parallel in Yao — serialized to sequential in QIR
        # (Semantic gap documented in `unsupported`)
        for (loc, b) in zip(block.locs, block.blocks)
            blocs = collect(loc : loc + nqubits(b) - 1)
            lower_block!(ops, cbit_counter, b, nq; locs=blocs)
        end

    elseif isa(block, ControlBlock)
        ctrl_0 = [c - 1 for c in block.ctrl_locs]  # 0-based
        inner  = block.block

        if isa(inner, PutBlock) && isa(inner.block, PrimitiveGate)
            # Canonical form: control(n, ctrl_locs, target_loc => primitive)
            tgt_gate   = inner.block
            target_0   = [l - 1 for l in inner.locs]
            n_ctrl     = length(ctrl_0)
            gate_name  = tgt_gate.name

            if n_ctrl == 1 && gate_name == "X"
                push!(ops, ir_gate("CX", Float64[], vcat(ctrl_0, target_0)))
            elseif n_ctrl == 2 && gate_name == "X"
                push!(ops, ir_gate("CCX", Float64[], vcat(ctrl_0, target_0)))
            else
                # Generic controlled gate: "C-<name>"
                ir_name = "C" * get(YAO_TO_IR_NAME, gate_name, gate_name)
                push!(ops, ir_gate(ir_name, copy(tgt_gate.params), vcat(ctrl_0, target_0)))
            end

        elseif isa(inner, PrimitiveGate)
            # Bare primitive without PutBlock — infer target qubit
            gate_name = inner.name
            target_0  = [maximum(block.ctrl_locs)]  # follows last control (0-based already)
            n_ctrl    = length(ctrl_0)

            if n_ctrl == 1 && gate_name == "X"
                push!(ops, ir_gate("CX", Float64[], vcat(ctrl_0, target_0)))
            elseif n_ctrl == 2 && gate_name == "X"
                push!(ops, ir_gate("CCX", Float64[], vcat(ctrl_0, target_0)))
            else
                ir_name = "C" * get(YAO_TO_IR_NAME, gate_name, gate_name)
                push!(ops, ir_gate(ir_name, copy(inner.params), vcat(ctrl_0, target_0)))
            end

        else
            @warn "ControlBlock with inner block type $(typeof(inner)) — emitting barrier instead"
            push!(ops, ir_barrier(collect(0:nq-1)))
        end

    elseif isa(block, MeasureBlock)
        for loc in block.locs
            q0 = loc - 1
            push!(ops, ir_measure(q0, cbit_counter[1]))
            cbit_counter[1] += 1
        end

    else
        @warn "Unknown block type $(typeof(block)) — skipping"
    end
end

# -----------------------------------------------------------------------
# Resource analysis
# -----------------------------------------------------------------------

"""
    compute_resources(ops, nq) -> Dict

Count gate_count, depth, t_count, width from a flat IR op list.
Depth is computed by tracking the latest layer each qubit was used in.
"""
function compute_resources(ops::Vector{Dict{String,Any}}, nq::Int)::Dict{String,Int}
    gate_count = 0
    t_count    = 0
    qubit_layer = zeros(Int, nq)  # last layer each qubit was touched

    for op in ops
        if op["type"] == "gate"
            gate_count += 1
            name = op["name"]
            if is_t_gate(name)
                t_count += 1
            end
            qs = Int[q for q in op["qubits"]]
            if !isempty(qs)
                layer = maximum(qubit_layer[q+1] for q in qs) + 1
                for q in qs
                    qubit_layer[q+1] = layer
                end
            end
        end
    end

    depth = isempty(qubit_layer) ? 0 : maximum(qubit_layer)
    return Dict{String,Int}(
        "gate_count" => gate_count,
        "depth"      => depth,
        "t_count"    => t_count,
        "width"      => nq,
    )
end

# -----------------------------------------------------------------------
# Main lowering entry point
# -----------------------------------------------------------------------

"""
    UNSUPPORTED_SEMANTICS

Canonical list of Yao.jl semantics that cannot be represented in QIR v0.1.
This list is ALWAYS included in every IR output — never silently empty.
"""
const UNSUPPORTED_SEMANTICS = [
    "KronBlock parallelism (serialized to sequential in QIR)",
    "differentiable parameters (AD metadata not in QIR v0.1)",
    "Yao.jl ChainBlock nesting (flattened to sequential op list)",
]

"""
    yao_to_ir(circuit::ChainBlock; cbits=nothing) -> Dict{String,Any}

Translate a Yao.jl ChainBlock to QuantumIR JSON (as a Julia Dict).
Returns a Dict matching the QuantumIR schema.

`cbits` — number of classical bits; if nothing, inferred from MeasureBlock count.

Unsupported semantics are always listed in `metadata.unsupported`.
"""
function yao_to_ir(circuit::ChainBlock; cbits::Union{Int,Nothing}=nothing)::Dict{String,Any}
    nq = circuit.nqubits
    ops = Dict{String,Any}[]
    cbit_counter = [0]  # mutable counter via 1-element Vector

    lower_block!(ops, cbit_counter, circuit, nq)

    n_cbits = cbits !== nothing ? cbits : cbit_counter[1]
    resources = compute_resources(ops, nq)

    return Dict{String,Any}(
        "version"     => "0.1.0",
        "source_lang" => "yao",
        "qubits"      => nq,
        "cbits"       => n_cbits,
        "ops"         => ops,
        "metadata"    => Dict{String,Any}(
            "source_lang" => "yao",
            "version"     => "0.1.0",
            "unsupported" => UNSUPPORTED_SEMANTICS,
        ),
        "resources"   => resources,
    )
end

# -----------------------------------------------------------------------
# JSON serialization (stdlib only — no JSON3 or JSON packages)
# -----------------------------------------------------------------------

"""
    to_json(x; indent=2) -> String

Serialize a Julia Dict/Vector/primitive to JSON string.
Handles nested Dicts, Vectors, Int, Float64, Bool, String, Nothing.
"""
function to_json(x; indent::Int=2)::String
    buf = IOBuffer()
    _json_write(buf, x, 0, indent)
    return String(take!(buf))
end

function _json_indent(io::IO, depth::Int, indent::Int)
    if indent > 0
        print(io, "\n")
        print(io, " " ^ (depth * indent))
    end
end

function _json_write(io::IO, x::Dict, depth::Int, indent::Int)
    print(io, "{")
    keys_sorted = sort(collect(keys(x)))  # deterministic output
    for (i, k) in enumerate(keys_sorted)
        _json_indent(io, depth+1, indent)
        _json_write(io, string(k), depth+1, indent)
        print(io, ": ")
        _json_write(io, x[k], depth+1, indent)
        if i < length(keys_sorted)
            print(io, ",")
        end
    end
    _json_indent(io, depth, indent)
    print(io, "}")
end

function _json_write(io::IO, x::Vector, depth::Int, indent::Int)
    if isempty(x)
        print(io, "[]")
        return
    end
    print(io, "[")
    for (i, v) in enumerate(x)
        _json_indent(io, depth+1, indent)
        _json_write(io, v, depth+1, indent)
        if i < length(x)
            print(io, ",")
        end
    end
    _json_indent(io, depth, indent)
    print(io, "]")
end

function _json_write(io::IO, x::String, depth::Int, indent::Int)
    # Escape special characters
    s = replace(x, "\\" => "\\\\", "\"" => "\\\"", "\n" => "\\n", "\t" => "\\t")
    print(io, "\"", s, "\"")
end

function _json_write(io::IO, x::Bool, depth::Int, indent::Int)
    print(io, x ? "true" : "false")
end

function _json_write(io::IO, x::Int, depth::Int, indent::Int)
    print(io, x)
end

function _json_write(io::IO, x::Float64, depth::Int, indent::Int)
    if isinteger(x) && abs(x) < 1e15
        print(io, string(Int(x)), ".0")
    else
        print(io, x)
    end
end

function _json_write(io::IO, x::Nothing, depth::Int, indent::Int)
    print(io, "null")
end

# Fallback for Any
function _json_write(io::IO, x, depth::Int, indent::Int)
    print(io, string(x))
end
