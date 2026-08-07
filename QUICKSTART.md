# BOB 2.0 Quantum + Granite Compiler - Quick Start

## Prerequisites

- Python 3.10 or later
- NASM (Netwide Assembler) 2.15+
- GCC (C compiler for assembly linking)
- git

### Install Dependencies

**macOS:**
```bash
brew install nasm gcc
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install nasm gcc python3-dev
```

**Windows (MSYS2/MinGW):**
```bash
pacman -S nasm gcc mingw-w64-x86_64-toolchain
```

## 5-Minute Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/SNAPKITTYWEST/ibm-bob-2.0-hackathon.git
cd ibm-bob-2.0-hackathon
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Build Assembly Layer
```bash
cd assembly
./build.sh
cd ..
```

### Step 5: Configure Environment
```bash
cp .env.example .env
# Edit .env with your IBM_QUANTUM_TOKEN and API keys
python main.py
```

## Optional Runs

### Quantum Engine Only
```bash
python main.py --quantum-only --backend aer_simulator
```

### Granite Compiler Only
```bash
python main.py --compiler-only --granite-trace
```

### NASM Assembly Standalone
```bash
nasm -f elf64 assembly/quantum_kernel.asm -o assembly/quantum_kernel.o
gcc -shared -o assembly/libquantum_nasm.so assembly/quantum_kernel.o
```

### Full Simulation with Voxel Grid
```bash
python main.py --voxel-grid-size 64 --simulation-steps 500 --num-agents 15
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `nasm: command not found` | Install NASM (see Prerequisites) |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in activated venv |
| `IBM_QUANTUM_TOKEN` not set | Copy `.env.example` to `.env` and add your token |
| NASM build fails | Ensure gcc/clang is installed; check `assembly/build.sh` permissions |
| Quantum backend error | Set `QUANTUM_BACKEND=aer_simulator` in `.env` for local simulation |

## Quick Verify

```bash
python -c "import qiskit; print(qiskit.__version__)"
python main.py --version
```

Both should succeed. You're ready to build.

---

See `README.md` for full architecture and `docs/` for detailed guides.