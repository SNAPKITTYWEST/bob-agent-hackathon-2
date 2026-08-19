"""
qir_to_vox.py — QIR JSON → MagicaVoxel .vox binary emitter.

BURT-IMMA: Matrix-Memory Equilibrium Propagation Agent
Phase 10-12 voxel frontend — consumes QuantumIR from all three language agents.

.vox binary format (RIFF-style, version 150, little-endian):
    magic      : b"VOX " (4 bytes)
    version    : uint32 = 150
    MAIN chunk : 4 bytes id + 4 bytes child_content_size + 4 bytes child_chunk_size
      SIZE chunk : x y z (uint32 each) — bounding box
      XYZI chunk : count (uint32) + per-voxel [x,y,z,color_index] (uint8 each)
      RGBA chunk : 256 × 4 bytes (r,g,b,a) — color palette

Quantum State Color Mapping (canonical — indices 1-8):
    1 = red    (#e63946) → qubit |1⟩
    2 = blue   (#457b9d) → qubit |0⟩
    3 = white  (#f1faee) → superposition (H gate output)
    4 = gold   (#ffb703) → gate operation (active gate voxel)
    5 = green  (#2dc653) → measured / collapsed
    6 = purple (#8338ec) → entangled pair (CNOT target)
    7 = orange (#fb5607) → WORM sealed state
    8 = cyan   (#00b4d8) → sovereign agent marker

QIR → voxel coordinate system:
    X axis = time step (gate sequence index, 0-based)
    Y axis = qubit index (q0 = 0)
    Z axis = 0 (flat circuit layout)

Gate → color mapping:
    "H"                          → 3 (white, superposition)
    "X","Y","Z"                  → 1 (red, |1⟩ flip)
    "CX","CNOT" control qubit    → 4 (gold, gate)
    "CX","CNOT" target qubit     → 6 (purple, entangled)
    "T","S","Rz","Rx","Ry","U1"  → 4 (gold, gate)
    measure                      → 5 (green, collapsed)
    reset                        → 2 (blue)
    barrier                      → skip (no voxel)
    WORM sealed (metadata flag)  → 7 (orange, overrides all above)
"""

from __future__ import annotations

import json
import struct
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Color palette (MagicaVoxel index 1-based; index 0 is empty/transparent)
# ---------------------------------------------------------------------------

# 256-entry RGBA palette.  Indices 1-8 are quantum state colors.
# Remaining entries are filled with neutral grey for tooling compatibility.
_NEUTRAL = (180, 180, 180, 255)

QUANTUM_PALETTE: List[Tuple[int, int, int, int]] = [
    (0,   0,   0,   0  ),  # index 0  — empty / transparent (never used)
    (230, 57,  70,  255),  # index 1  — |1⟩  red      #e63946
    (69,  123, 157, 255),  # index 2  — |0⟩  blue     #457b9d
    (241, 250, 238, 255),  # index 3  — superposition white  #f1faee
    (255, 183, 3,   255),  # index 4  — gate gold      #ffb703
    (45,  198, 83,  255),  # index 5  — measured green #2dc653
    (131, 56,  236, 255),  # index 6  — entangled purple #8338ec
    (251, 86,  7,   255),  # index 7  — WORM orange    #fb5607
    (0,   180, 216, 255),  # index 8  — sovereign cyan #00b4d8
] + [_NEUTRAL] * (256 - 9)  # indices 9-255 = neutral grey


# ---------------------------------------------------------------------------
# Gate → color index mapping
# ---------------------------------------------------------------------------

def _gate_color(name: str, qubit_role: str) -> int:
    """Return quantum color index for a gate on a given qubit role.

    qubit_role is one of: "solo", "control", "target"
    """
    if name in ("CX", "CNOT", "CZ"):
        if qubit_role == "control":
            return 4  # gold
        else:
            return 6  # purple (entangled)
    if name == "H":
        return 3  # white, superposition
    if name in ("X", "Y", "Z"):
        return 1  # red, |1⟩ flip
    if name in ("T", "Tdg", "S", "Sdg", "Rx", "Ry", "Rz", "U1", "U2", "U3", "CCX"):
        return 4  # gold, gate
    # Default: treat unknown gates as gate operations
    return 4


# ---------------------------------------------------------------------------
# Main entry point: QIR dict → list of (x, y, z, color_index)
# ---------------------------------------------------------------------------

def qir_to_voxels(
    qir: Dict[str, Any],
) -> List[Tuple[int, int, int, int]]:
    """Convert a QuantumIR dict to a list of (x, y, z, color_index) voxels.

    X = time step (0-based gate sequence index, advances per non-barrier op)
    Y = qubit index
    Z = 0 (flat)

    Barriers produce no voxels.
    WORM sealed flag (metadata.worm_sealed == True) overrides all colors → 7.
    """
    # Detect WORM sealed flag
    meta = qir.get("metadata") or qir.get("meta") or {}
    worm_sealed: bool = bool(meta.get("worm_sealed", False))

    voxels: List[Tuple[int, int, int, int]] = []
    time_step = 0

    ops = qir.get("ops", [])
    for op in ops:
        # Support both "type" key (language agents) and "op" key (schema spec)
        op_type = op.get("type") or op.get("op", "")

        if op_type == "barrier":
            # Barriers: no voxel, no time advance
            continue

        if op_type == "gate":
            name = op.get("name", "")
            qubits = op.get("qubits", [])
            if not qubits:
                time_step += 1
                continue

            if len(qubits) == 1:
                color = _gate_color(name, "solo")
                if worm_sealed:
                    color = 7
                voxels.append((time_step, qubits[0], 0, color))
            else:
                # Multi-qubit gate: control = qubits[0], targets = qubits[1:]
                ctrl_color = _gate_color(name, "control")
                tgt_color  = _gate_color(name, "target")
                if worm_sealed:
                    ctrl_color = 7
                    tgt_color  = 7
                voxels.append((time_step, qubits[0], 0, ctrl_color))
                for tgt in qubits[1:]:
                    voxels.append((time_step, tgt, 0, tgt_color))

        elif op_type == "measure":
            qubit = op.get("qubit", 0)
            color = 7 if worm_sealed else 5  # green or WORM orange
            voxels.append((time_step, qubit, 0, color))

        elif op_type == "reset":
            qubit = op.get("qubit", 0)
            color = 7 if worm_sealed else 2  # blue or WORM orange
            voxels.append((time_step, qubit, 0, color))

        time_step += 1

    return voxels


# ---------------------------------------------------------------------------
# .vox binary writer
# ---------------------------------------------------------------------------

def _pack_chunk(chunk_id: bytes, content: bytes, children: bytes = b"") -> bytes:
    """Pack a single .vox chunk:  id(4) + content_size(4) + children_size(4) + content + children."""
    return (
        chunk_id
        + struct.pack("<I", len(content))
        + struct.pack("<I", len(children))
        + content
        + children
    )


def _build_vox(
    voxels: List[Tuple[int, int, int, int]],
    palette: List[Tuple[int, int, int, int]],
) -> bytes:
    """Assemble a complete .vox binary from voxels + palette.

    Dimensions are derived from voxel coordinate bounds.
    """
    if voxels:
        max_x = max(v[0] for v in voxels) + 1
        max_y = max(v[1] for v in voxels) + 1
        max_z = max(v[2] for v in voxels) + 1
    else:
        max_x = max_y = max_z = 1  # MagicaVoxel requires at least 1×1×1

    # SIZE chunk content: x y z (uint32 each)
    size_content = struct.pack("<III", max_x, max_y, max_z)

    # XYZI chunk content: count (uint32) + voxels (4 bytes each: x y z ci)
    xyzi_content = struct.pack("<I", len(voxels))
    for (x, y, z, ci) in voxels:
        xyzi_content += struct.pack("BBBB", x, y, z, ci)

    # RGBA chunk content: 256 × 4 bytes
    rgba_content = b""
    for (r, g, b, a) in palette:
        rgba_content += struct.pack("BBBB", r, g, b, a)

    # Assemble child chunks
    children = (
        _pack_chunk(b"SIZE", size_content)
        + _pack_chunk(b"XYZI", xyzi_content)
        + _pack_chunk(b"RGBA", rgba_content)
    )

    # MAIN chunk: no content of its own, only children
    main_chunk = _pack_chunk(b"MAIN", b"", children)

    # File header: magic + version
    header = b"VOX " + struct.pack("<I", 150)

    return header + main_chunk


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def qir_to_vox(
    qir: Dict[str, Any],
    palette: Optional[List[Tuple[int, int, int, int]]] = None,
) -> bytes:
    """Convert a QuantumIR dict to a .vox binary blob.

    Parameters
    ----------
    qir     : parsed QuantumIR JSON (dict)
    palette : 256-entry RGBA palette.  Defaults to QUANTUM_PALETTE.

    Returns
    -------
    bytes : complete .vox file contents (ready to write to disk)
    """
    if palette is None:
        palette = QUANTUM_PALETTE
    voxels = qir_to_voxels(qir)
    return _build_vox(voxels, palette)


def qir_file_to_vox_file(
    qir_path: str | Path,
    vox_path: str | Path,
    palette: Optional[List[Tuple[int, int, int, int]]] = None,
) -> List[Tuple[int, int, int, int]]:
    """Load a QIR JSON file and write a .vox binary file.

    Returns the list of voxels emitted (useful for verification).
    """
    qir_path = Path(qir_path)
    vox_path = Path(vox_path)

    with qir_path.open("r", encoding="utf-8") as f:
        qir = json.load(f)

    data = qir_to_vox(qir, palette)

    with vox_path.open("wb") as f:
        f.write(data)

    return qir_to_voxels(qir)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python qir_to_vox.py <input.json> <output.vox>")
        sys.exit(1)

    voxels = qir_file_to_vox_file(sys.argv[1], sys.argv[2])
    print(f"Emitted {len(voxels)} voxels → {sys.argv[2]}")
    for v in voxels:
        print(f"  (x={v[0]}, y={v[1]}, z={v[2]}, color={v[3]})")
