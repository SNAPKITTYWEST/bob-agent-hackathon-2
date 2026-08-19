// QuantumVoxelServer.cs
// BURT-IMMA — Phase 10-12 Quantum Voxel Frontend
//
// Cherry-pick from ChunkGatewayServer:
//   - TcpListener / BinaryWriter / ChunkPacket pattern (preserved exactly)
//   - StructureToBytes<T> generic helper (preserved exactly)
//   - ChunkPacket / VoxelData struct (preserved exactly)
//
// Quantum extension:
//   - StreamQuantumCircuit(TcpClient, string qirJsonPath)
//   - Reads QIR JSON → converts to 32×32×32 voxel chunks → streams to client
//   - Quantum color index encoded in R channel of VoxelData
//
// Quantum State → RGB mapping (canonical 8 colors):
//   1 = (230, 57,  70 )  |1⟩  red
//   2 = (69,  123, 157)  |0⟩  blue
//   3 = (241, 250, 238)  superposition white
//   4 = (255, 183, 3  )  gate gold
//   5 = (45,  198, 83 )  measured green
//   6 = (131, 56,  236)  entangled purple
//   7 = (251, 86,  7  )  WORM orange
//   8 = (0,   180, 216)  sovereign agent cyan

using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using System.Collections.Generic;

namespace SnapKitty.QuantumVoxel
{
    // -----------------------------------------------------------------------
    // VoxelData — matches ChunkGatewayServer exactly
    // -----------------------------------------------------------------------
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct VoxelData
    {
        public byte R;
        public byte G;
        public byte B;
        public byte Density;  // 0 = empty, 255 = solid
    }

    // -----------------------------------------------------------------------
    // ChunkPacket — 32×32×32 block, matches ChunkGatewayServer exactly
    // -----------------------------------------------------------------------
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct ChunkPacket
    {
        public int ChunkX;
        public int ChunkY;
        public int ChunkZ;
        public int VoxelCount;

        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 32768)]  // 32*32*32
        public VoxelData[] Voxels;

        public static ChunkPacket Empty(int cx, int cy, int cz)
        {
            var pkt = new ChunkPacket
            {
                ChunkX = cx,
                ChunkY = cy,
                ChunkZ = cz,
                VoxelCount = 0,
                Voxels = new VoxelData[32768],
            };
            return pkt;
        }
    }

    // -----------------------------------------------------------------------
    // Quantum color index → RGB mapping
    // -----------------------------------------------------------------------
    public static class QuantumColorMap
    {
        public static readonly (byte R, byte G, byte B)[] Colors = new[]
        {
            (0,   0,   0  ),  // index 0 — empty / transparent
            (230, 57,  70 ),  // index 1 — |1⟩  red
            (69,  123, 157),  // index 2 — |0⟩  blue
            (241, 250, 238),  // index 3 — superposition white
            (255, 183, 3  ),  // index 4 — gate gold
            (45,  198, 83 ),  // index 5 — measured green
            (131, 56,  236),  // index 6 — entangled purple
            (251, 86,  7  ),  // index 7 — WORM orange
            (0,   180, 216),  // index 8 — sovereign agent cyan
        };

        public static (byte R, byte G, byte B) Get(int index)
        {
            if (index < 0 || index >= Colors.Length) return (180, 180, 180);
            return Colors[index];
        }
    }

    // -----------------------------------------------------------------------
    // QIR voxel: coordinate + color index (mirrors Python emitter logic)
    // -----------------------------------------------------------------------
    public readonly record struct QirVoxel(int X, int Y, int Z, int ColorIndex);

    // -----------------------------------------------------------------------
    // QIR JSON parser — reads QuantumIR ops → list of QirVoxel
    // Supports both "type" key (language agents) and "op" key (schema spec)
    // -----------------------------------------------------------------------
    public static class QirParser
    {
        private static int GateColor(string name, string role)
        {
            return name switch
            {
                "H" => 3,
                "X" or "Y" or "Z" => 1,
                "CX" or "CNOT" or "CZ" => role == "control" ? 4 : 6,
                "T" or "Tdg" or "S" or "Sdg"
                    or "Rx" or "Ry" or "Rz"
                    or "U1" or "U2" or "U3"
                    or "CCX" => 4,
                _ => 4,
            };
        }

        public static List<QirVoxel> Parse(string qirJson)
        {
            var voxels = new List<QirVoxel>();
            using var doc = JsonDocument.Parse(qirJson);
            var root = doc.RootElement;

            // WORM sealed flag
            bool wormSealed = false;
            if (root.TryGetProperty("metadata", out var metaElem) ||
                root.TryGetProperty("meta", out metaElem))
            {
                if (metaElem.TryGetProperty("worm_sealed", out var ws))
                    wormSealed = ws.GetBoolean();
            }

            if (!root.TryGetProperty("ops", out var opsElem)) return voxels;

            int t = 0;
            foreach (var op in opsElem.EnumerateArray())
            {
                // Support "type" or "op" key
                string opType = "";
                if (op.TryGetProperty("type", out var typeProp))
                    opType = typeProp.GetString() ?? "";
                else if (op.TryGetProperty("op", out var opProp))
                    opType = opProp.GetString() ?? "";

                if (opType == "barrier") continue;

                if (opType == "gate")
                {
                    string name = op.TryGetProperty("name", out var np) ? (np.GetString() ?? "") : "";
                    if (!op.TryGetProperty("qubits", out var qubitsElem)) { t++; continue; }

                    var qubits = new List<int>();
                    foreach (var q in qubitsElem.EnumerateArray())
                        qubits.Add(q.GetInt32());

                    if (qubits.Count == 0) { t++; continue; }

                    if (qubits.Count == 1)
                    {
                        int ci = wormSealed ? 7 : GateColor(name, "solo");
                        voxels.Add(new QirVoxel(t, qubits[0], 0, ci));
                    }
                    else
                    {
                        int ctrlCi = wormSealed ? 7 : GateColor(name, "control");
                        int tgtCi  = wormSealed ? 7 : GateColor(name, "target");
                        voxels.Add(new QirVoxel(t, qubits[0], 0, ctrlCi));
                        for (int i = 1; i < qubits.Count; i++)
                            voxels.Add(new QirVoxel(t, qubits[i], 0, tgtCi));
                    }
                }
                else if (opType == "measure")
                {
                    int qubit = op.TryGetProperty("qubit", out var qp) ? qp.GetInt32() : 0;
                    int ci = wormSealed ? 7 : 5;
                    voxels.Add(new QirVoxel(t, qubit, 0, ci));
                }
                else if (opType == "reset")
                {
                    int qubit = op.TryGetProperty("qubit", out var qp) ? qp.GetInt32() : 0;
                    int ci = wormSealed ? 7 : 2;
                    voxels.Add(new QirVoxel(t, qubit, 0, ci));
                }

                t++;
            }

            return voxels;
        }
    }

    // -----------------------------------------------------------------------
    // QuantumVoxelServer
    //
    // Cherry-pick from ChunkGatewayServer:
    //   - TcpListener pattern (same port default 8080)
    //   - BinaryWriter streaming
    //   - StructureToBytes<T> helper (preserved exactly)
    //   - ChunkPacket / VoxelData struct (preserved exactly)
    // -----------------------------------------------------------------------
    public class QuantumVoxelServer
    {
        private const int DefaultPort = 8080;
        private const int ChunkDim   = 32;

        private readonly int _port;
        private TcpListener? _listener;

        public QuantumVoxelServer(int port = DefaultPort)
        {
            _port = port;
        }

        // -----------------------------------------------------------------------
        // StructureToBytes<T> — cherry-picked from ChunkGatewayServer, unchanged
        // -----------------------------------------------------------------------
        private static byte[] StructureToBytes<T>(T structure) where T : struct
        {
            int size = Marshal.SizeOf(structure);
            byte[] arr = new byte[size];
            IntPtr ptr = Marshal.AllocHGlobal(size);
            try
            {
                Marshal.StructureToPtr(structure, ptr, false);
                Marshal.Copy(ptr, arr, 0, size);
            }
            finally
            {
                Marshal.FreeHGlobal(ptr);
            }
            return arr;
        }

        // -----------------------------------------------------------------------
        // Start — begin accepting connections
        // -----------------------------------------------------------------------
        public async Task StartAsync(string defaultQirPath)
        {
            _listener = new TcpListener(IPAddress.Any, _port);
            _listener.Start();
            Console.WriteLine($"[QuantumVoxelServer] Listening on port {_port}");

            while (true)
            {
                var client = await _listener.AcceptTcpClientAsync();
                Console.WriteLine($"[QuantumVoxelServer] Client connected: {client.Client.RemoteEndPoint}");
                _ = Task.Run(() => HandleClientAsync(client, defaultQirPath));
            }
        }

        private async Task HandleClientAsync(TcpClient client, string qirPath)
        {
            try
            {
                await StreamQuantumCircuit(client, qirPath);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[QuantumVoxelServer] Client error: {ex.Message}");
            }
            finally
            {
                client.Close();
                Console.WriteLine("[QuantumVoxelServer] Client disconnected");
            }
        }

        // -----------------------------------------------------------------------
        // StreamQuantumCircuit — reads QIR JSON → voxel chunks → streams to client
        // Cherry-pick: ChunkGatewayServer streaming pattern (TcpClient + BinaryWriter)
        // -----------------------------------------------------------------------
        public async Task StreamQuantumCircuit(TcpClient client, string qirJsonPath)
        {
            string qirJson = await File.ReadAllTextAsync(qirJsonPath);
            var qirVoxels = QirParser.Parse(qirJson);

            Console.WriteLine($"[QuantumVoxelServer] Streaming {qirVoxels.Count} voxels from {qirJsonPath}");

            // Compute chunk bounding box
            if (qirVoxels.Count == 0)
            {
                Console.WriteLine("[QuantumVoxelServer] No voxels to stream.");
                return;
            }

            int maxChunkX = 0, maxChunkY = 0, maxChunkZ = 0;
            foreach (var v in qirVoxels)
            {
                maxChunkX = Math.Max(maxChunkX, v.X / ChunkDim);
                maxChunkY = Math.Max(maxChunkY, v.Y / ChunkDim);
                maxChunkZ = Math.Max(maxChunkZ, v.Z / ChunkDim);
            }

            // Build chunk dictionary
            var chunks = new Dictionary<(int, int, int), ChunkPacket>();
            foreach (var v in qirVoxels)
            {
                int cx = v.X / ChunkDim;
                int cy = v.Y / ChunkDim;
                int cz = v.Z / ChunkDim;
                var key = (cx, cy, cz);

                if (!chunks.ContainsKey(key))
                    chunks[key] = ChunkPacket.Empty(cx, cy, cz);

                int lx = v.X % ChunkDim;
                int ly = v.Y % ChunkDim;
                int lz = v.Z % ChunkDim;
                int idx = lx + ly * ChunkDim + lz * ChunkDim * ChunkDim;

                var (r, g, b) = QuantumColorMap.Get(v.ColorIndex);

                // Store color index in R channel for Metal shader lookup
                // Full RGB also stored for direct use
                var vd = chunks[key].Voxels[idx];
                vd.R       = (byte)v.ColorIndex;  // color index for Metal shader
                vd.G       = g;
                vd.B       = b;
                vd.Density = 255;

                var pkt = chunks[key];
                pkt.Voxels[idx] = vd;
                pkt.VoxelCount++;
                chunks[key] = pkt;
            }

            // Stream all chunks to the client (BinaryWriter pattern)
            using var stream = client.GetStream();
            using var writer = new BinaryWriter(stream);

            // Write chunk count header
            writer.Write(chunks.Count);

            foreach (var kvp in chunks)
            {
                var packet = kvp.Value;
                byte[] bytes = StructureToBytes(packet);
                writer.Write(bytes.Length);
                writer.Write(bytes);
                Console.WriteLine(
                    $"[QuantumVoxelServer] Streamed chunk ({kvp.Key.Item1},{kvp.Key.Item2},{kvp.Key.Item3})" +
                    $" — {packet.VoxelCount} voxels"
                );
            }

            writer.Flush();
        }

        // -----------------------------------------------------------------------
        // CLI entry point
        // -----------------------------------------------------------------------
        public static async Task Main(string[] args)
        {
            string qirPath = args.Length > 0 ? args[0] : "../../voxel/demo/bell_state_quipper.json";
            int port = args.Length > 1 ? int.Parse(args[1]) : DefaultPort;

            var server = new QuantumVoxelServer(port);
            await server.StartAsync(qirPath);
        }
    }
}
