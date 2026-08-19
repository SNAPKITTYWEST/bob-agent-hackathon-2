// QuantumVoxelView.swift
// BURT-IMMA — Phase 10-12 Quantum Voxel Frontend
//
// Cherry-pick sources:
//   - MetalVoxelEngine: connectToCSGateway() + receiveChunk() + processChunkData()
//   - SpaceVoxelScene: setupEnvironment() lighting (directional + ambient)
//   - SwiftUI UIViewRepresentable wrapper pattern
//
// Renamed: QuantumVoxelEngine, QuantumVoxelView
// Connects to C# QuantumVoxelServer on port 8080.
// In processChunkData: R channel → quantum color index → SIMD4<Float> color.
// Metal pipeline and shader API unchanged from cherry-pick source.

import Foundation
import Metal
import MetalKit
import SwiftUI
import Network
import simd

// ---------------------------------------------------------------------------
// MARK: — Quantum Color Constants (canonical 8 colors as SIMD4<Float>)
// ---------------------------------------------------------------------------

enum QuantumColor: Int {
    case empty        = 0
    case one          = 1  // |1⟩  red
    case zero         = 2  // |0⟩  blue
    case superpos     = 3  // superposition white
    case gate         = 4  // gate gold
    case measured     = 5  // measured green
    case entangled    = 6  // entangled purple
    case worm         = 7  // WORM orange
    case sovereign    = 8  // sovereign agent cyan

    var simdColor: SIMD4<Float> {
        switch self {
        case .empty:     return SIMD4<Float>(0.000, 0.000, 0.000, 0.000)
        case .one:       return SIMD4<Float>(0.902, 0.224, 0.275, 1.000) // #e63946
        case .zero:      return SIMD4<Float>(0.271, 0.482, 0.616, 1.000) // #457b9d
        case .superpos:  return SIMD4<Float>(0.945, 0.980, 0.933, 1.000) // #f1faee
        case .gate:      return SIMD4<Float>(1.000, 0.718, 0.012, 1.000) // #ffb703
        case .measured:  return SIMD4<Float>(0.176, 0.776, 0.325, 1.000) // #2dc653
        case .entangled: return SIMD4<Float>(0.514, 0.220, 0.925, 1.000) // #8338ec
        case .worm:      return SIMD4<Float>(0.984, 0.337, 0.027, 1.000) // #fb5607
        case .sovereign: return SIMD4<Float>(0.000, 0.706, 0.847, 1.000) // #00b4d8
        }
    }

    static func from(colorIndex: UInt8) -> QuantumColor {
        return QuantumColor(rawValue: Int(colorIndex)) ?? .gate
    }
}

// ---------------------------------------------------------------------------
// MARK: — VoxelInstance (GPU instance data)
// ---------------------------------------------------------------------------

struct VoxelInstance {
    var position: SIMD3<Float>
    var color: SIMD4<Float>
}

// ---------------------------------------------------------------------------
// MARK: — ChunkPacket (matches C# struct layout exactly)
// ---------------------------------------------------------------------------

struct ReceivedVoxel {
    let x: Int
    let y: Int
    let z: Int
    let colorIndex: UInt8
}

// ---------------------------------------------------------------------------
// MARK: — QuantumVoxelEngine
// Cherry-pick: MetalVoxelEngine pattern (connectToCSGateway / receiveChunk /
//              processChunkData), SpaceVoxelScene setupEnvironment() lighting
// ---------------------------------------------------------------------------

@MainActor
class QuantumVoxelEngine: NSObject, MTKViewDelegate {

    // Metal state
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    private var renderPipeline: MTLRenderPipelineState?
    private var depthState: MTLDepthStencilState?
    private var instanceBuffer: MTLBuffer?
    private var vertexBuffer: MTLBuffer?

    // Scene state
    private var instances: [VoxelInstance] = []
    private var uniformsBuffer: MTLBuffer?

    // Network (cherry-pick: MetalVoxelEngine.connectToCSGateway pattern)
    private var connection: NWConnection?
    private let serverHost: String
    private let serverPort: UInt16

    // Lighting params (cherry-pick: SpaceVoxelScene.setupEnvironment)
    private var lightDirection: SIMD3<Float>  = normalize(SIMD3<Float>(0.5, 1.0, 0.7))
    private var lightColor: SIMD3<Float>      = SIMD3<Float>(1.0, 0.94, 0.88)
    private var ambientColor: SIMD3<Float>    = SIMD3<Float>(0.25, 0.28, 0.35)

    // Camera / animation
    private var orbitAngle: Float = 0.0
    private var cameraDistance: Float = 12.0

    // Uniforms struct (matches shader expectation)
    struct Uniforms {
        var modelViewProjection: float4x4
        var lightDirection: SIMD3<Float>
        var _pad0: Float = 0
        var lightColor: SIMD3<Float>
        var _pad1: Float = 0
        var ambientColor: SIMD3<Float>
        var _pad2: Float = 0
    }

    init?(device: MTLDevice, serverHost: String = "127.0.0.1", serverPort: UInt16 = 8080) {
        self.device = device
        self.serverHost = serverHost
        self.serverPort = serverPort
        guard let queue = device.makeCommandQueue() else { return nil }
        self.commandQueue = queue
        super.init()
    }

    // -----------------------------------------------------------------------
    // MARK: — Setup pipeline
    // -----------------------------------------------------------------------

    func setup(view: MTKView) {
        view.device = device
        view.colorPixelFormat = .bgra8Unorm
        view.depthStencilPixelFormat = .depth32Float
        view.clearColor = MTLClearColor(red: 0.118, green: 0.118, blue: 0.141, alpha: 1.0)
        view.delegate = self

        setupPipeline(view: view)
        setupDepthState()
        setupVertexBuffer()
        setupUniforms()

        // Connect to C# QuantumVoxelServer
        connectToCSGateway()
    }

    // -----------------------------------------------------------------------
    // MARK: — connectToCSGateway (cherry-pick: MetalVoxelEngine pattern)
    // Connects to the C# QuantumVoxelServer on port 8080.
    // -----------------------------------------------------------------------

    private func connectToCSGateway() {
        let endpoint = NWEndpoint.hostPort(
            host: NWEndpoint.Host(serverHost),
            port: NWEndpoint.Port(rawValue: serverPort)!
        )
        connection = NWConnection(to: endpoint, using: .tcp)
        connection?.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                print("[QuantumVoxelEngine] Connected to C# gateway at \(self?.serverHost ?? ""):\(self?.serverPort ?? 0)")
                self?.receiveChunkCount()
            case .failed(let error):
                print("[QuantumVoxelEngine] Connection failed: \(error)")
            case .cancelled:
                print("[QuantumVoxelEngine] Connection cancelled")
            default:
                break
            }
        }
        connection?.start(queue: .global(qos: .userInitiated))
    }

    // -----------------------------------------------------------------------
    // MARK: — receiveChunk (cherry-pick: MetalVoxelEngine pattern)
    // -----------------------------------------------------------------------

    private func receiveChunkCount() {
        connection?.receive(minimumIncompleteLength: 4, maximumLength: 4) { [weak self] data, _, _, error in
            guard let self, let data, error == nil, data.count == 4 else { return }
            let chunkCount = data.withUnsafeBytes { $0.load(as: Int32.self) }
            print("[QuantumVoxelEngine] Expecting \(chunkCount) chunks")
            self.receiveChunks(remaining: Int(chunkCount))
        }
    }

    private func receiveChunks(remaining: Int) {
        guard remaining > 0 else {
            print("[QuantumVoxelEngine] All chunks received — \(self.instances.count) voxels")
            Task { @MainActor in self.rebuildInstanceBuffer() }
            return
        }
        // Read chunk byte length header
        connection?.receive(minimumIncompleteLength: 4, maximumLength: 4) { [weak self] data, _, _, error in
            guard let self, let data, error == nil, data.count == 4 else { return }
            let byteLen = data.withUnsafeBytes { $0.load(as: Int32.self) }
            self.receiveChunk(byteLength: Int(byteLen), remaining: remaining)
        }
    }

    private func receiveChunk(byteLength: Int, remaining: Int) {
        connection?.receive(minimumIncompleteLength: byteLength, maximumLength: byteLength) { [weak self] data, _, _, error in
            guard let self, let data, error == nil else { return }
            self.processChunkData(data)
            self.receiveChunks(remaining: remaining - 1)
        }
    }

    // -----------------------------------------------------------------------
    // MARK: — processChunkData (cherry-pick: MetalVoxelEngine pattern)
    // R channel → quantum color index → SIMD4<Float> color values
    // -----------------------------------------------------------------------

    private func processChunkData(_ data: Data) {
        // ChunkPacket layout (matches C# struct):
        //   ChunkX   : Int32 (4 bytes)
        //   ChunkY   : Int32 (4 bytes)
        //   ChunkZ   : Int32 (4 bytes)
        //   VoxelCount: Int32 (4 bytes)
        //   Voxels   : 32768 × 4 bytes (R,G,B,Density)
        let headerSize = 16  // 4 × Int32
        let voxelSize  = 4   // R,G,B,Density
        let chunkDim   = 32

        guard data.count >= headerSize else { return }

        let chunkX = data.withUnsafeBytes { $0.load(fromByteOffset: 0,  as: Int32.self) }
        let chunkY = data.withUnsafeBytes { $0.load(fromByteOffset: 4,  as: Int32.self) }
        let chunkZ = data.withUnsafeBytes { $0.load(fromByteOffset: 8,  as: Int32.self) }
        // VoxelCount not strictly needed; we scan the full 32^3 block

        var newInstances: [VoxelInstance] = []

        for lz in 0..<chunkDim {
            for ly in 0..<chunkDim {
                for lx in 0..<chunkDim {
                    let voxelIndex = lx + ly * chunkDim + lz * chunkDim * chunkDim
                    let byteOffset = headerSize + voxelIndex * voxelSize

                    guard byteOffset + 3 < data.count else { continue }

                    let rByte   = data[byteOffset + 0]  // quantum color index
                    let density = data[byteOffset + 3]

                    guard density == 255 else { continue }

                    // R channel encodes the quantum color index (1-8)
                    let colorIndex = rByte
                    let quantumColor = QuantumColor.from(colorIndex: colorIndex)
                    let simdColor = quantumColor.simdColor

                    let worldX = Float(Int(chunkX) * chunkDim + lx)
                    let worldY = Float(Int(chunkY) * chunkDim + ly)
                    let worldZ = Float(Int(chunkZ) * chunkDim + lz)

                    newInstances.append(VoxelInstance(
                        position: SIMD3<Float>(worldX, worldY, worldZ),
                        color: simdColor
                    ))
                }
            }
        }

        Task { @MainActor in
            self.instances.append(contentsOf: newInstances)
        }
    }

    // -----------------------------------------------------------------------
    // MARK: — Metal pipeline setup
    // -----------------------------------------------------------------------

    private func setupPipeline(view: MTKView) {
        let library = device.makeDefaultLibrary()
        let vertexFn   = library?.makeFunction(name: "quantum_vertex")
        let fragmentFn = library?.makeFunction(name: "quantum_fragment")

        let desc = MTLRenderPipelineDescriptor()
        desc.vertexFunction   = vertexFn
        desc.fragmentFunction = fragmentFn
        desc.colorAttachments[0].pixelFormat = view.colorPixelFormat
        desc.depthAttachmentPixelFormat      = view.depthStencilPixelFormat

        do {
            renderPipeline = try device.makeRenderPipelineState(descriptor: desc)
        } catch {
            print("[QuantumVoxelEngine] Pipeline error: \(error)")
        }
    }

    private func setupDepthState() {
        let desc = MTLDepthStencilDescriptor()
        desc.depthCompareFunction = .less
        desc.isDepthWriteEnabled  = true
        depthState = device.makeDepthStencilState(descriptor: desc)
    }

    private func setupUniforms() {
        uniformsBuffer = device.makeBuffer(
            length: MemoryLayout<Uniforms>.stride,
            options: .cpuCacheModeWriteCombined
        )
    }

    private func setupVertexBuffer() {
        // Cube vertices are defined in the Metal shader (cubeVertices[36])
        // No CPU-side vertex data needed for the instanced draw call
    }

    // -----------------------------------------------------------------------
    // MARK: — Instance buffer rebuild
    // -----------------------------------------------------------------------

    private func rebuildInstanceBuffer() {
        guard !instances.isEmpty else { return }
        let byteCount = instances.count * MemoryLayout<VoxelInstance>.stride
        instanceBuffer = device.makeBuffer(
            bytes: instances,
            length: byteCount,
            options: .cpuCacheModeWriteCombined
        )
    }

    // -----------------------------------------------------------------------
    // MARK: — Environment lighting (cherry-pick: SpaceVoxelScene.setupEnvironment)
    // Directional light + ambient light
    // -----------------------------------------------------------------------

    private func setupEnvironment() {
        // Directional light (warm sun-like)
        lightDirection = normalize(SIMD3<Float>(0.5, 1.0, 0.7))
        lightColor     = SIMD3<Float>(1.0, 0.94, 0.88)

        // Ambient (cool fill from sky)
        ambientColor   = SIMD3<Float>(0.25, 0.28, 0.35)
    }

    // -----------------------------------------------------------------------
    // MARK: — MTKViewDelegate: draw
    // -----------------------------------------------------------------------

    nonisolated func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) { }

    nonisolated func draw(in view: MTKView) {
        Task { @MainActor in drawFrame(view: view) }
    }

    private func drawFrame(view: MTKView) {
        guard
            let pipeline = renderPipeline,
            let depth    = depthState,
            let uniforms = uniformsBuffer,
            let drawable = view.currentDrawable,
            let rpd       = view.currentRenderPassDescriptor,
            let cmdBuffer = commandQueue.makeCommandBuffer(),
            let encoder   = cmdBuffer.makeRenderCommandEncoder(descriptor: rpd)
        else { return }

        // Update camera orbit
        orbitAngle += 0.012
        let eye = SIMD3<Float>(
            sin(orbitAngle) * cameraDistance + 2,
            6.0 + sin(orbitAngle * 0.5) * 2.0,
            cos(orbitAngle) * cameraDistance
        )
        let target = SIMD3<Float>(2, 1, 0)
        let up     = SIMD3<Float>(0, 1, 0)

        let aspect = Float(view.drawableSize.width / view.drawableSize.height)
        let proj   = perspectiveMatrix(fovY: .pi / 3, aspect: aspect, near: 0.1, far: 200)
        let view4  = lookAtMatrix(eye: eye, target: target, up: up)
        let mvp    = proj * view4

        var u = Uniforms(
            modelViewProjection: mvp,
            lightDirection: lightDirection,
            lightColor: lightColor,
            ambientColor: ambientColor
        )
        memcpy(uniforms.contents(), &u, MemoryLayout<Uniforms>.stride)

        encoder.setRenderPipelineState(pipeline)
        encoder.setDepthStencilState(depth)
        encoder.setVertexBuffer(uniforms, offset: 0, index: 1)

        if let inst = instanceBuffer, !instances.isEmpty {
            encoder.setVertexBuffer(inst, offset: 0, index: 2)
            encoder.drawPrimitives(
                type: .triangle,
                vertexStart: 0,
                vertexCount: 36,       // cubeVertices[36] in shader
                instanceCount: instances.count
            )
        }

        encoder.endEncoding()
        cmdBuffer.present(drawable)
        cmdBuffer.commit()
    }

    // -----------------------------------------------------------------------
    // MARK: — Math helpers
    // -----------------------------------------------------------------------

    private func perspectiveMatrix(fovY: Float, aspect: Float, near: Float, far: Float) -> float4x4 {
        let y = 1 / tan(fovY * 0.5)
        let x = y / aspect
        let z = far / (near - far)
        return float4x4(columns: (
            SIMD4<Float>( x,  0,  0,  0),
            SIMD4<Float>( 0,  y,  0,  0),
            SIMD4<Float>( 0,  0,  z, -1),
            SIMD4<Float>( 0,  0,  z * near, 0)
        ))
    }

    private func lookAtMatrix(eye: SIMD3<Float>, target: SIMD3<Float>, up: SIMD3<Float>) -> float4x4 {
        let f = normalize(target - eye)
        let r = normalize(cross(f, up))
        let u = cross(r, f)
        return float4x4(columns: (
            SIMD4<Float>( r.x,  u.x, -f.x, 0),
            SIMD4<Float>( r.y,  u.y, -f.y, 0),
            SIMD4<Float>( r.z,  u.z, -f.z, 0),
            SIMD4<Float>(-dot(r, eye), -dot(u, eye), dot(f, eye), 1)
        ))
    }
}

// ---------------------------------------------------------------------------
// MARK: — QuantumVoxelView (UIViewRepresentable, cherry-pick pattern)
// ---------------------------------------------------------------------------

struct QuantumVoxelView: UIViewRepresentable {

    let serverHost: String
    let serverPort: UInt16

    init(serverHost: String = "127.0.0.1", serverPort: UInt16 = 8080) {
        self.serverHost = serverHost
        self.serverPort = serverPort
    }

    func makeUIView(context: Context) -> MTKView {
        guard let device = MTLCreateSystemDefaultDevice() else {
            fatalError("[QuantumVoxelView] Metal not available on this device")
        }
        let mtkView = MTKView(frame: .zero, device: device)
        mtkView.preferredFramesPerSecond = 60
        mtkView.isPaused = false
        mtkView.enableSetNeedsDisplay = false

        guard let engine = QuantumVoxelEngine(
            device: device,
            serverHost: serverHost,
            serverPort: serverPort
        ) else {
            fatalError("[QuantumVoxelView] Failed to create QuantumVoxelEngine")
        }
        context.coordinator.engine = engine
        engine.setup(view: mtkView)
        return mtkView
    }

    func updateUIView(_ uiView: MTKView, context: Context) { }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    // Coordinator holds the engine to prevent deallocation
    class Coordinator {
        var engine: QuantumVoxelEngine?
    }
}

// ---------------------------------------------------------------------------
// MARK: — SwiftUI Preview (macOS / iOS)
// ---------------------------------------------------------------------------

struct QuantumVoxelView_Previews: PreviewProvider {
    static var previews: some View {
        QuantumVoxelView()
            .frame(width: 800, height: 600)
    }
}
