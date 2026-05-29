# AdaptiveCpp HPC container with BOTH NVIDIA CUDA and AMD ROCm support
#
# Dev/CI-only image: it carries both vendor runtime slices and an AdaptiveCpp
# built with both the CUDA and ROCm backends. CUDA comes from the (~5 GB)
# nvidia/cuda devel image; ROCm is installed from AMD's apt repo (only the
# components needed, like adaptivecpp-hpc-rocm) rather than the ~30 GB
# rocm/dev *-complete image.
#
# Pick the backend at exec time, e.g.:
#   apptainer run --nv   --env ACPP_VISIBILITY_MASK=cuda  thor-multigpu.sif ...
#   apptainer run --rocm --env ACPP_VISIBILITY_MASK=hip   thor-multigpu.sif ...
#
# Produces: ghcr.io/thor-rt/adaptivecpp-hpc-multigpu:main

ARG TOOLCHAIN_IMAGE=ghcr.io/thor-rt/adaptivecpp-toolchain:main
ARG RUNTIME_IMAGE=ghcr.io/thor-rt/adaptivecpp-runtime:main
ARG CUDA_IMAGE=nvidia/cuda:12.8.1-devel-ubuntu24.04

# ============================================================
# Stage 1: CUDA toolkit source (devel image, used only to copy from)
# ============================================================
FROM ${CUDA_IMAGE} AS cuda-toolkit

# ============================================================
# Stage 2: Build AdaptiveCpp with BOTH CUDA and ROCm backends
# ============================================================
FROM ${TOOLCHAIN_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive
ARG CLANG_VERSION=18
ARG ACPP_VERSION=v25.02.0
ARG ROCM_VERSION=6.4.1

# Bring in the CUDA toolkit for the build only (discarded with this stage)
COPY --from=cuda-toolkit /usr/local/cuda /usr/local/cuda

# Add AMD's ROCm apt repo and install only the build-time components
# (see adaptivecpp-hpc-rocm for the rationale, package list, and apt pin)
RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg ca-certificates \
    && wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key | gpg --dearmor -o /usr/share/keyrings/rocm.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/${ROCM_VERSION} noble main" > /etc/apt/sources.list.d/rocm.list \
    && printf 'Package: *\nPin: origin repo.radeon.com\nPin-Priority: 600\n' > /etc/apt/preferences.d/rocm-pin-600 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       rocm-llvm \
       rocm-device-libs \
       hip-dev \
       hsa-rocr-dev \
       comgr \
       hipcc \
    && rm -rf /var/lib/apt/lists/*

ENV ROCM_PATH=/opt/rocm
ENV PATH="/usr/local/cuda/bin:/opt/rocm/bin:${PATH}"
RUN echo "/opt/rocm/lib" > /etc/ld.so.conf.d/rocm.conf && ldconfig

RUN git clone --depth 1 --branch ${ACPP_VERSION} https://github.com/illuhad/hipSYCL.git /hipsycl

RUN cmake -S /hipsycl -B /hipsycl/build \
    -DCMAKE_INSTALL_PREFIX=/opt/hipsycl \
    -DCMAKE_BUILD_TYPE=Release \
    -DWITH_CPU_BACKEND=ON \
    -DWITH_CUDA_BACKEND=ON \
    -DWITH_ROCM_BACKEND=ON \
    -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda \
    -DROCM_PATH=/opt/rocm \
    -DLLVM_DIR=/usr/lib/llvm-${CLANG_VERSION} \
    -DCLANG_EXECUTABLE_PATH=/usr/bin/clang++-${CLANG_VERSION}

RUN cmake --build /hipsycl/build --target install

# ============================================================
# Stage 3: Runtime image + both vendor slices + AdaptiveCpp
# ============================================================
FROM ${RUNTIME_IMAGE}

# --- Slim CUDA runtime slice (see adaptivecpp-hpc-cuda for rationale) ---
COPY --from=cuda-toolkit /usr/local/cuda/lib64/libcudart*.so* /usr/local/cuda/lib64/
COPY --from=cuda-toolkit /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/
COPY --from=cuda-toolkit /usr/local/cuda/include /usr/local/cuda/include
COPY --from=cuda-toolkit /usr/local/cuda/nvvm /usr/local/cuda/nvvm
COPY --from=cuda-toolkit /usr/local/cuda/bin/ptxas /usr/local/cuda/bin/ptxas
COPY --from=cuda-toolkit /usr/local/cuda/bin/fatbinary /usr/local/cuda/bin/fatbinary
COPY --from=cuda-toolkit /usr/local/cuda/bin/bin2c /usr/local/cuda/bin/bin2c
COPY --from=cuda-toolkit /usr/local/cuda/bin/crt /usr/local/cuda/bin/crt

# --- Slim ROCm runtime slice from the builder (see adaptivecpp-hpc-rocm) ---
COPY --from=builder /opt/rocm/lib/libamdhip64.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/libhsa-runtime64.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/libhiprtc*.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/libamd_comgr.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/librocprofiler-register.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/amdgcn /opt/rocm/amdgcn
COPY --from=builder /opt/rocm/llvm/bin/lld /opt/rocm/llvm/bin/lld
COPY --from=builder /opt/rocm/include /opt/rocm/include

RUN echo "/usr/local/cuda/lib64" > /etc/ld.so.conf.d/cuda.conf \
    && echo "/usr/local/cuda/nvvm/lib64" >> /etc/ld.so.conf.d/cuda.conf \
    && echo "/opt/rocm/lib" > /etc/ld.so.conf.d/rocm.conf \
    && ldconfig

# Copy AdaptiveCpp installation
COPY --from=builder /opt/hipsycl /opt/hipsycl

# Environment (no fixed ACPP_VISIBILITY_MASK — pick the backend at exec time)
ENV ROCM_PATH=/opt/rocm
ENV HIPSYCL_INSTALL_DIR=/opt/hipsycl
ENV PATH="${HIPSYCL_INSTALL_DIR}/bin:/usr/local/cuda/bin:/opt/rocm/bin:${PATH}"
ENV CPATH="${HIPSYCL_INSTALL_DIR}/include:${CPATH}"
ENV LD_LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/usr/local/cuda/lib64:/opt/rocm/lib:${LD_LIBRARY_PATH}"
ENV LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/usr/local/cuda/lib64:/opt/rocm/lib:${LIBRARY_PATH}"
ENV CC=cc
ENV CXX=acpp
ENV LLVM_COV=/usr/local/bin/llvm-cov

CMD ["bash"]
