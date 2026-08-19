// quantum_voxel.metal
// BURT-IMMA — Phase 10-12 Quantum Voxel Frontend
//
// Cherry-pick from sovereign-voxel-civilization Metal shader:
//   - cubeVertices[36] array (preserved exactly)
//   - Isometric projection matrix (preserved exactly)
//   - Vertex shader structure (preserved exactly)
//
// Quantum extension (fragment shader only):
//   - Fragment color decoded from color index in in.color.r channel
//   - 8 quantum state colors replace original voxel civilization palette
//   - Rim glow preserved for volumetric feel

#include <metal_stdlib>
using namespace metal;

// ---------------------------------------------------------------------------
// Vertex input / output
// ---------------------------------------------------------------------------

struct VertexIn {
    float3 position [[attribute(0)]];
    float3 normal   [[attribute(1)]];
};

struct VertexOut {
    float4 position [[position]];
    float3 worldPos;
    float3 normal;
    float4 color;    // color.r = quantum color index (1-8, normalized to 0-1 range)
};

// ---------------------------------------------------------------------------
// Instance data (matches Swift VoxelInstance struct)
// ---------------------------------------------------------------------------

struct VoxelInstance {
    float3 position;
    float4 color;
};

// ---------------------------------------------------------------------------
// Uniforms
// ---------------------------------------------------------------------------

struct Uniforms {
    float4x4 modelViewProjection;
    float3   lightDirection;
    float    _pad0;
    float3   lightColor;
    float    _pad1;
    float3   ambientColor;
    float    _pad2;
};

// ---------------------------------------------------------------------------
// Cube vertex data — cubeVertices[36] (cherry-pick: preserved exactly)
// Unit cube centred at origin, CCW winding, flat normals per face
// ---------------------------------------------------------------------------

constant float3 cubeVertices[36] = {
    // -Z face
    float3(-0.5, -0.5, -0.5), float3( 0.5, -0.5, -0.5), float3( 0.5,  0.5, -0.5),
    float3( 0.5,  0.5, -0.5), float3(-0.5,  0.5, -0.5), float3(-0.5, -0.5, -0.5),
    // +Z face
    float3(-0.5, -0.5,  0.5), float3( 0.5,  0.5,  0.5), float3( 0.5, -0.5,  0.5),
    float3( 0.5,  0.5,  0.5), float3(-0.5, -0.5,  0.5), float3(-0.5,  0.5,  0.5),
    // -X face
    float3(-0.5,  0.5,  0.5), float3(-0.5,  0.5, -0.5), float3(-0.5, -0.5, -0.5),
    float3(-0.5, -0.5, -0.5), float3(-0.5, -0.5,  0.5), float3(-0.5,  0.5,  0.5),
    // +X face
    float3( 0.5,  0.5,  0.5), float3( 0.5, -0.5, -0.5), float3( 0.5,  0.5, -0.5),
    float3( 0.5, -0.5, -0.5), float3( 0.5,  0.5,  0.5), float3( 0.5, -0.5,  0.5),
    // -Y face
    float3(-0.5, -0.5, -0.5), float3( 0.5, -0.5, -0.5), float3( 0.5, -0.5,  0.5),
    float3( 0.5, -0.5,  0.5), float3(-0.5, -0.5,  0.5), float3(-0.5, -0.5, -0.5),
    // +Y face
    float3(-0.5,  0.5, -0.5), float3( 0.5,  0.5,  0.5), float3( 0.5,  0.5, -0.5),
    float3( 0.5,  0.5,  0.5), float3(-0.5,  0.5, -0.5), float3(-0.5,  0.5,  0.5),
};

// Flat normals per face (6 faces × 6 vertices)
constant float3 cubeNormals[36] = {
    float3( 0, 0,-1), float3( 0, 0,-1), float3( 0, 0,-1),
    float3( 0, 0,-1), float3( 0, 0,-1), float3( 0, 0,-1),
    float3( 0, 0, 1), float3( 0, 0, 1), float3( 0, 0, 1),
    float3( 0, 0, 1), float3( 0, 0, 1), float3( 0, 0, 1),
    float3(-1, 0, 0), float3(-1, 0, 0), float3(-1, 0, 0),
    float3(-1, 0, 0), float3(-1, 0, 0), float3(-1, 0, 0),
    float3( 1, 0, 0), float3( 1, 0, 0), float3( 1, 0, 0),
    float3( 1, 0, 0), float3( 1, 0, 0), float3( 1, 0, 0),
    float3( 0,-1, 0), float3( 0,-1, 0), float3( 0,-1, 0),
    float3( 0,-1, 0), float3( 0,-1, 0), float3( 0,-1, 0),
    float3( 0, 1, 0), float3( 0, 1, 0), float3( 0, 1, 0),
    float3( 0, 1, 0), float3( 0, 1, 0), float3( 0, 1, 0),
};

// ---------------------------------------------------------------------------
// Isometric projection matrix (cherry-pick: preserved exactly)
// Classic 2:1 isometric: rotated 45° on Y, then ~35.26° on X
// ---------------------------------------------------------------------------

constant float4x4 isoMatrix = float4x4(
    float4( 0.7071,  0.4082, -0.5774, 0),
    float4( 0.0000,  0.8165,  0.5774, 0),
    float4( 0.7071, -0.4082,  0.5774, 0),
    float4( 0.0000,  0.0000,  0.0000, 1)
);

// ---------------------------------------------------------------------------
// MARK: — Vertex Shader
// ---------------------------------------------------------------------------

vertex VertexOut quantum_vertex(
    uint            vertexID   [[ vertex_id   ]],
    uint            instanceID [[ instance_id ]],
    constant Uniforms*       uniforms  [[ buffer(1) ]],
    constant VoxelInstance*  instances [[ buffer(2) ]]
) {
    VertexOut out;

    float3 localPos = cubeVertices[vertexID];
    float3 normal   = cubeNormals[vertexID];

    VoxelInstance inst = instances[instanceID];
    float3 worldPos = localPos + inst.position;

    out.position = uniforms->modelViewProjection * float4(worldPos, 1.0);
    out.worldPos = worldPos;
    out.normal   = normal;
    out.color    = inst.color;  // color.r = quantum color index / 255.0

    return out;
}

// ---------------------------------------------------------------------------
// MARK: — Fragment Shader
//
// Quantum state colors by index (R channel encodes color index 1-8).
// Cherry-pick base: sovereign-voxel-civilization fragment shader.
// Quantum state color mapping replaces original civilization palette.
// Rim glow preserved.
// ---------------------------------------------------------------------------

fragment float4 quantum_fragment(
    VertexOut in [[ stage_in ]],
    constant Uniforms* uniforms [[ buffer(1) ]]
) {
    // Decode quantum color index from R channel
    float idx = round(in.color.r * 255.0);

    float3 qColor;
    if      (idx <= 1.0) qColor = float3(0.902, 0.224, 0.275); // |1⟩ red
    else if (idx <= 2.0) qColor = float3(0.271, 0.482, 0.616); // |0⟩ blue
    else if (idx <= 3.0) qColor = float3(0.945, 0.980, 0.933); // superposition white
    else if (idx <= 4.0) qColor = float3(1.000, 0.718, 0.012); // gate gold
    else if (idx <= 5.0) qColor = float3(0.176, 0.776, 0.325); // measured green
    else if (idx <= 6.0) qColor = float3(0.514, 0.220, 0.925); // entangled purple
    else if (idx <= 7.0) qColor = float3(0.984, 0.337, 0.027); // WORM orange
    else                 qColor = float3(0.000, 0.706, 0.847); // sovereign cyan

    // Lambertian diffuse
    float3 N    = normalize(in.normal);
    float3 L    = normalize(uniforms->lightDirection);
    float  diff = max(dot(N, L), 0.0);
    float3 diffuse = uniforms->lightColor * qColor * diff;

    // Ambient
    float3 ambient = uniforms->ambientColor * qColor;

    // Rim glow (edge highlight — preserved from cherry-pick source)
    // Approximated without view vector: brighten faces perpendicular to light
    float rimFactor = pow(1.0 - abs(dot(N, L)), 3.0) * 0.25;
    float3 rimGlow  = qColor * rimFactor;

    float3 finalColor = ambient + diffuse + rimGlow;

    // Gamma correction (approximate)
    finalColor = pow(clamp(finalColor, 0.0, 1.0), float3(1.0 / 2.2));

    return float4(finalColor, 1.0);
}
