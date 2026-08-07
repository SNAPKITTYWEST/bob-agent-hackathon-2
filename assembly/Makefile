# Makefile for IBM Quantum NASM Bridge
# Compiles x86-64 assembly for quantum operations

ASM = nasm
CC = gcc
ASMFLAGS = -f elf64 -g -F dwarf
CFLAGS = -Wall -O3 -march=native
LDFLAGS = -lm

TARGET = quantum_nasm_bridge
ASM_SRC = quantum_nasm_bridge.asm
OBJ = quantum_nasm_bridge.o
SHARED_LIB = libquantum_nasm.so

.PHONY: all clean shared test

all: $(TARGET)

$(OBJ): $(ASM_SRC)
	$(ASM) $(ASMFLAGS) $(ASM_SRC) -o $(OBJ)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) -o $(TARGET) $(LDFLAGS)

shared: $(OBJ)
	$(CC) -shared -fPIC $(OBJ) -o $(SHARED_LIB) $(LDFLAGS)

test: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(OBJ) $(TARGET) $(SHARED_LIB)

install: shared
	cp $(SHARED_LIB) /usr/local/lib/
	ldconfig

.SILENT: clean

# Made with Bob
