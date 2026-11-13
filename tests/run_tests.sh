#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=0

# Detect compiler
if [ -z "$CXX" ]; then
    if command -v icpx &> /dev/null; then
        CXX=icpx
    elif command -v acpp &> /dev/null; then
        CXX=acpp
    else
        echo "ERROR: No SYCL compiler found"
        exit 1
    fi
fi

echo "=== Using compiler: $CXX ==="
echo ""

echo "=== Compiling SYCL test ==="
# AdaptiveCpp (acpp) doesn't use -fsycl flag
if [ "$CXX" = "acpp" ]; then
    $CXX -O2 "$SCRIPT_DIR/vector_add.cpp" -o /tmp/vector_add
else
    $CXX -fsycl -O2 "$SCRIPT_DIR/vector_add.cpp" -o /tmp/vector_add
fi

echo ""
echo "=== Test 1: Default backend ==="
OUTPUT=$(/tmp/vector_add 2>&1)
echo "$OUTPUT"
if echo "$OUTPUT" | grep -q "PASS"; then
    # For Intel containers, verify it's NOT using PoCL by default
    if [ -f /opt/pocl/lib/libpocl.so.2 ]; then
        if echo "$OUTPUT" | grep -q "Device: cpu-"; then
            echo "Test 1: FAILED - Expected Intel OpenCL but got PoCL"
            FAILED=1
        else
            echo "Test 1: PASSED (Intel OpenCL)"
        fi
    else
        echo "Test 1: PASSED"
    fi
else
    echo "Test 1: FAILED"
    FAILED=1
fi

# Test PoCL backend if available (intel-sycl containers only)
if [ -f /opt/pocl/lib/libpocl.so.2 ]; then
    echo ""
    echo "=== Test 2: PoCL backend ==="
    export OCL_ICD_FILENAMES=/opt/pocl/lib/libpocl.so.2
    export SYCL_DEVICE_ALLOWLIST=''
    OUTPUT=$(/tmp/vector_add 2>&1)
    echo "$OUTPUT"
    if echo "$OUTPUT" | grep -q "PASS"; then
        if echo "$OUTPUT" | grep -q "Device: cpu-"; then
            echo "Test 2: PASSED (PoCL)"
        else
            echo "Test 2: FAILED - Expected PoCL but got different backend"
            FAILED=1
        fi
    else
        echo "Test 2: FAILED"
        FAILED=1
    fi
    unset OCL_ICD_FILENAMES SYCL_DEVICE_ALLOWLIST
fi

# Open MPI 5 built into /opt/openmpi (AdaptiveCpp images only). [AI-Claude]
if [ "$CXX" = "acpp" ] && [ ! -x /opt/openmpi/bin/mpicxx ]; then
    echo ""
    echo "Test 3: FAILED - AdaptiveCpp image without /opt/openmpi"
    FAILED=1
elif [ -x /opt/openmpi/bin/mpicxx ]; then
    echo ""
    echo "=== Test 3: Open MPI ==="
    mpi_check() {  # description, command...
        local description=$1
        shift
        if "$@"; then
            echo "  ok: $description"
        else
            echo "  FAILED: $description"
            FAILED=1
        fi
    }
    OMPI_INFO=$(ompi_info)
    UCX_BUILD=$(ucx_info -b)
    mpi_check "Open MPI 5" grep -q "Open MPI: 5\." <<< "$OMPI_INFO"
    mpi_check "MPI_THREAD_MULTIPLE support" grep -q "MPI_THREAD_MULTIPLE: yes" <<< "$OMPI_INFO"
    mpi_check "UCX transport (pml ucx)" grep -q "MCA pml: ucx" <<< "$OMPI_INFO"
    mpi_check "UCX built with thread support" grep -qE "ENABLE_MT +1" <<< "$UCX_BUILD"
    mpi_check "no Ubuntu Open MPI packages" bash -c "! dpkg -l | grep -qE '^ii +(openmpi-bin|libopenmpi)'"
    mpicxx -O2 -pthread "$SCRIPT_DIR/mpi_threads.cpp" -o /tmp/mpi_threads
    mpi_check "test links /opt/openmpi" bash -c "ldd /tmp/mpi_threads | grep -q '/opt/openmpi/lib/libmpi.so'"
    ROOT_FLAG=()
    if [ "$(id -u)" = 0 ]; then ROOT_FLAG=(--allow-run-as-root); fi
    # set -e would end the script on a failing run before its output is shown.
    OUTPUT=$(mpirun "${ROOT_FLAG[@]}" --oversubscribe -np 2 /tmp/mpi_threads 2>&1) || true
    echo "$OUTPUT"
    mpi_check "two ranks with two threads each" grep -q "^PASS" <<< "$OUTPUT"
fi

# Host OpenMP and SYCL must share libomp and honor the CPU allocation. [AI-Codex]
if [ "$(basename "$CXX")" = "acpp" ]; then
    echo ""
    echo "=== Test 4: OpenMP runtime and kernel affinity ==="
    python3 "$SCRIPT_DIR/run_openmp_affinity.py"
fi

# Check the slim ROCm slice even on CPU-only CI runners. [AI-Codex]
if [ -f /opt/hipsycl/lib/hipSYCL/librt-backend-hip.so ]; then
    echo ""
    echo "=== Test 5: HIP backend dependencies ==="
    python3 - <<'PY'
import ctypes
import os
ctypes.CDLL("/opt/hipsycl/lib/hipSYCL/librt-backend-hip.so", mode=os.RTLD_NOW)
print("PASS: HIP backend and its shared-library dependencies load")
PY
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed!"
    exit 1
fi
