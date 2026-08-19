# MagicaVoxel Viewer

Renderer for the sovereign voxel civilization output.

## What it is

MagicaVoxel is a free voxel editor and path-traced renderer by ephtracy.
Extract MagicaVoxel-Viewer.zip and run the executable to view .vox files.

## File format (.vox)

RIFF-style binary format. BURT generates this directly.

Chunk layout:
  VOX  - magic + version
  MAIN - root chunk
    SIZE - dimensions: x y z (uint32 each)
    XYZI - voxel data: count (uint32) + [x,y,z,color_index] per voxel (uint8 each)
    RGBA - 256-color palette (4 bytes per color: r,g,b,a)

## Quantum civilization color mapping

Color index -> quantum meaning:
  1  (red)     - qubit |1>
  2  (blue)    - qubit |0>
  3  (white)   - superposition
  4  (gold)    - gate operation
  5  (green)   - measured / collapsed
  6  (purple)  - entangled pair
  7  (orange)  - WORM sealed state
  8  (cyan)    - sovereign agent

## How to generate .vox from QuantumIR

See src/ for the voxel emitter. Feed it a QuantumIR JSON from Phase 8
and it outputs a .vox file ready for MagicaVoxel rendering.

## Path

tools/magicavoxel/MagicaVoxel-Viewer.zip
Extract here. Run MagicaVoxel.exe (Windows) or MagicaVoxel.app (Mac).
