Docker containers for SYCL implementations.

## AdaptiveCpp Containers

The AdaptiveCpp images use Clang 19 and pin AdaptiveCpp to
`1170ba6a1500fb02c8afe4823e5b3785b5842f74`, the minimum commit required
by THOR for the PR #1995 math fixes. [AI-Codex]

AdaptiveCpp itself is built with that same Clang compiler, so its OpenMP
CPU backend and Clang-built applications share LLVM `libomp`. Setting only
`CLANG_EXECUTABLE_PATH` selects the application compiler but does not select
the compiler that builds AdaptiveCpp. Mixing a GCC-built backend (`libgomp`)
with a Clang/OpenMP application (`libomp`) can collapse CPU parallelism when
thread binding is enabled; see the upstream
[performance guide](https://adaptivecpp.github.io/AdaptiveCpp/performance/#with-omp-compilation-flow).
The four AdaptiveCpp build recipes therefore set `CMAKE_C_COMPILER` and
`CMAKE_CXX_COMPILER` explicitly. [AI-Codex]

The supported application toolchain is `CXX=acpp` (Clang 19) and `CC=clang`
(the toolchain's Clang 19 alternative), with LLVM `libomp` as the OpenMP
runtime. OpenMP-enabled application code and dependencies must use this
runtime. GCC-built libraries without OpenMP can be used when their ABI is
compatible. Applications requiring GNU `libgomp` need a custom image with a
matching AdaptiveCpp backend; GCC/OpenMP variants and mixed OpenMP runtimes
are outside the supported configurations. The regression tests validate the
provided LLVM stack. [AI-Codex]

The AdaptiveCpp images are layered so the LLVM/Clang/CMake and HPC setup is
defined once and reused:

* **adaptivecpp-toolchain**: shared build environment — Ubuntu 24.04 + LLVM 19
  (clang/llvm), Kitware CMake, Boost, Ninja. No AdaptiveCpp, no HPC libs. Used
  as the `builder` stage of every image below.
* **adaptivecpp-runtime**: `adaptivecpp-toolchain` + HPC libs (HDF5, Open MPI 5,
  GMP, TBB). Used as the final-stage base of every image below. See
  [Open MPI](#open-mpi).
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

### Publishing

Each publishing run stages every image under `build-<run-id>-<attempt>`.
Downstream builds use that same tag for their toolchain, runtime, and base
images. Smoke tests run against the published digest. Once the entire chain
passes, a final job promotes those images without rebuilding them. [AI-Codex]

Successful `main` builds update `main` for all images and `clang19` for
AdaptiveCpp images. Release-tag builds publish version aliases instead;
they do not move `main` or `clang19`. Clang 18 is no longer rebuilt, and
existing `clang18-frozen` tags are never touched by this workflow. The
AdaptiveCpp images with Ubuntu's Open MPI 4.1.6 are kept the same way, as
`openmpi4-frozen`.

Release tags use the year and month, `vYYYY.M.N`, where `N` counts the
releases in that month (for example `v2026.11.0`). They publish `YYYY.M.N`,
`YYYY.M` and `YYYY`. A release tag can be pushed on a branch commit to build
and test the full image chain before the branch is merged into `main`.
[AI-Claude]

Publishing runs are serialized. Promotion across multiple packages is not
atomic: a registry failure can leave some aliases updated. The unique build
tags remain available to identify a complete image set. For a retry, choose
**Re-run all jobs**, since a new attempt gets a new build tag. PR runs perform
workflow checks and the existing standalone toolchain/Intel-base tests;
they do not publish images or build the dependent image chain.

### Build retention

After a main-branch publishing attempt, cleanup keeps the three newest build
sets whose entire promotion job matrix passed. Failed or incompletely promoted
attempts are kept for at least seven days. Active attempts are never removed.
Cleanup only deletes package versions with exclusively `build-<run>-<attempt>`
tags: any other tag, including `main`, `clang19`, `clang18-frozen`, release
versions, or custom tags, protects the whole version. [AI-Codex]

Untagged platform manifests and signature artifacts are deliberately retained;
removing them indiscriminately can break images that are still tagged. Thus this
policy limits build-tagged versions, but is not a complete registry garbage
collector. Missing workflow history or an API error stops cleanup. The workflow
must have admin access to each package for its `GITHUB_TOKEN` to delete versions;
`packages: write` alone cannot grant that package-level access.

Preview the plan without changing the registry:

```bash
python3 scripts/retain_container_builds.py --repository thor-rt/syclcontainers
```

Deletion is enabled only by the main-branch workflow using `--apply`. Publishing
and cleanup share the workflow concurrency group. Avoid manually retagging images
during cleanup: each candidate is rechecked before deletion, but the registry
provides no atomic check-and-delete operation.

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

Both ROCm-capable images install the system `libdrm2` and `libdrm-amdgpu1`
dependencies of the copied HSA runtime. The test suite loads the HIP backend
with immediate symbol resolution even when no AMD GPU is available. [AI-Codex]

### Open MPI

`adaptivecpp-runtime` builds Open MPI 5.0.11 and UCX 1.16.0 from source into
`/opt/openmpi`. Ubuntu 24.04 packages Open MPI 4.1.6. With UCX and
`MPI_THREAD_MULTIPLE`, its PMIx client can segfault when two threads of a rank
first contact a peer at the same time. The source build has these properties:

- UCX has thread support, so Open MPI accepts UCX under `MPI_THREAD_MULTIPLE`.
- Open MPI uses its bundled PMIx and PRRTE. It supports InfiniBand and RoCE
  (through UCX), libfabric (OFI) and Omni-Path (PSM2).
- No Ubuntu Open MPI package is installed. The toolchain image therefore
  installs Boost without its MPI components.

On a Slurm cluster, launch MPI inside the container with `srun --mpi=pmix`.
Open MPI 5 has no PMI-1 or PMI-2 support, and its PMIx client works with the
PMIx v3 server of Slurm's `pmix_v3` plugin. On one node, `mpirun` inside the
container also works. A host `mpirun` that starts container processes needs
Open MPI 5 on the host. [AI-Claude]

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

The AdaptiveCpp tests require at least two physical CPU cores. They compile
both `generic` and `omp` test programs and exercise `OMP_PROC_BIND=close` and
`spread`. After initializing host OpenMP, a background thread submits a real
SYCL CPU kernel. The test checks numerical output, records the kernel's CPU
and native thread IDs, verifies its restricted CPU allocation, and rejects
multiple loaded OpenMP runtimes. The allocation excludes CPU 0 when possible.
Run just this regression with `python3 /tests/run_openmp_affinity.py` inside
the container. [AI-Codex]
