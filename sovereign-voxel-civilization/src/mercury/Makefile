MERCURY_COMPILER = mmc
MERCURY_FLAGS = --grade hlc.gc --make --verbose
TARGETS = voxel_runtime voxel_tests
all: $(TARGETS)
voxel_runtime: voxel_world.m voxel_gateway.m voxel_runtime.m
	$(MERCURY_COMPILER) $(MERCURY_FLAGS) voxel_runtime
voxel_tests: voxel_world.m voxel_gateway.m voxel_tests.m
	$(MERCURY_COMPILER) $(MERCURY_FLAGS) voxel_tests
test: voxel_tests
	./voxel_tests
run: voxel_runtime
	./voxel_runtime
clean:
	rm -f *.mh *.c *.o *.err *.d *.int *.int2 *.int3
	rm -f voxel_runtime voxel_tests
	rm -rf Mercury
.PHONY: all test run clean

# Made with Bob
