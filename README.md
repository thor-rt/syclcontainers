Docker containers for SYCL implementations.

## AdaptiveCpp Containers

The AdaptiveCpp images are layered so the LLVM/Clang/CMake and HPC setup is
defined once and reused:

* **adaptivecpp-toolchain**: shared build environment — Ubuntu 24.04 + LLVM 18
  (clang/llvm), Kitware CMake, Boost, Ninja. No AdaptiveCpp, no HPC libs. Used
  as the `builder` stage of every image below.
* **adaptivecpp-runtime**: `adaptivecpp-toolchain` + HPC libs (HDF5, OpenMPI,
  GMP, TBB). Used as the final-stage base of every image below.
* **adaptivecpp-base**: AdaptiveCpp built on the toolchain (CPU backend),
  installed into the runtime image.
* **adaptivecpp-hpc**: thin alias of `adaptivecpp-base` (the HPC libs now live
  in `adaptivecpp-runtime`); kept for backward compatibility.
* **adaptivecpp-hpc-cuda**: `adaptivecpp-base` + NVIDIA CUDA backend (slim CUDA
  runtime slice copied from `nvidia/cuda:*-devel`).
* **adaptivecpp-hpc-rocm**: `adaptivecpp-base` + AMD ROCm/HIP backend. ROCm is
  installed from AMD's apt repo (only the components needed — like how
  `intel-sycl-base` installs only the oneAPI compiler), not pulled from the
  ~30 GB `rocm/dev *-complete` image, so the build stays CI-sized.
* **adaptivecpp-hpc-multigpu**: image with **both** the CUDA and ROCm backends
  and both vendor runtime slices. Pick the backend at exec time via
  `ACPP_VISIBILITY_MASK` (`cuda` or `hip`). It pulls both vendor toolkits at
  build time, so it is the largest/slowest CI job.

All images (`toolchain`, `runtime`, `base`, `hpc`, `hpc-cuda`, `hpc-rocm`,
`hpc-multigpu`, `intel-*`) are built and pushed automatically by
`.github/workflows/docker-publish.yml`.

### Build order / dependency graph

```
adaptivecpp-toolchain ──> adaptivecpp-runtime ──┬─> adaptivecpp-base ──> adaptivecpp-hpc
        (FROM ubuntu)        (+ HPC libs)        ├─> adaptivecpp-hpc-cuda      (+ nvidia/cuda:*-devel)
                                                 ├─> adaptivecpp-hpc-rocm      (+ rocm/dev-ubuntu:*-complete)
                                                 └─> adaptivecpp-hpc-multigpu  (+ both vendor toolkits)
```

The downstream images accept `TOOLCHAIN_IMAGE` and `RUNTIME_IMAGE` build args
so they can be pointed at locally built or alternative bases. The CUDA images
accept `CUDA_IMAGE` (the `nvidia/cuda:*-devel` source) and the ROCm images
accept `ROCM_VERSION` (the `repo.radeon.com/rocm/apt/<version>` to install).

### ROCm runtime slice

`adaptivecpp-hpc-rocm` copies only a minimal ROCm slice (HIP + HSA runtime,
`libamd_comgr`, `amdgcn` device bitcode, `lld`, HIP headers). This is
best-effort; verify on the target hardware with `acpp-info` / `ldd` and add
libraries to the `COPY --from=rocm-toolkit` block if something is missing. On
unsupported gfx targets you may need `HSA_OVERRIDE_GFX_VERSION` at runtime.

## Intel SYCL Containers

* **intel-sycl-base**: Base Intel DPC++ container with Intel oneAPI HPC Toolkit
* **intel-sycl-hpc**: Intel DPC++ with HDF5 and Intel MPI

### OpenCL Backend Selection (intel-sycl-base)

The container includes both Intel OpenCL and PoCL backends. Intel OpenCL is used by default and PoCL is hidden from SYCL.

```bash
# Use Intel OpenCL (default)
./my_sycl_app

# Show all available OpenCL platforms (including PoCL)
SYCL_DEVICE_ALLOWLIST='' sycl-ls

# Use PoCL instead of Intel OpenCL
ONEAPI_DEVICE_SELECTOR='opencl:1' ./my_sycl_app

# Or force PoCL only via OpenCL ICD
OCL_ICD_FILENAMES=/opt/pocl/lib/libpocl.so.2 ./my_sycl_app
```

**Note:** The Intel SYCL runtime filters non-Intel OpenCL platforms by default. Use `SYCL_DEVICE_ALLOWLIST=''` to see all platforms, or `ONEAPI_DEVICE_SELECTOR` to select a specific backend.

## Testing

Run the test suite inside a container:

```bash
# Intel containers
docker run --rm -v ./tests:/tests intel-sycl-base bash -c "source /opt/intel/oneapi/setvars.sh && /tests/run_tests.sh"

# AdaptiveCpp containers
docker run --rm -v ./tests:/tests adaptivecpp-base /tests/run_tests.sh
```
