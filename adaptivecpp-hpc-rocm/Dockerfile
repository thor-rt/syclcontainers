# AdaptiveCpp HPC container with AMD ROCm/HIP support
#
# Like intel-sycl-base (which installs only the oneAPI compiler packages from
# Intel's apt repo instead of pulling the ~10-15 GB oneapi-hpckit image), this
# image adds AMD's ROCm apt repo to the shared toolchain and installs only the
# components needed to build the AdaptiveCpp HIP backend. This keeps the build
# small enough for CI runners, unlike the ~30 GB rocm/dev *-complete image.
#
# The final stage copies only the minimal ROCm runtime slice the AdaptiveCpp
# SSCP/HIP JIT path needs into adaptivecpp-runtime.
#
# Produces: ghcr.io/thor-rt/adaptivecpp-hpc-rocm:main

ARG TOOLCHAIN_IMAGE=ghcr.io/thor-rt/adaptivecpp-toolchain:main
ARG RUNTIME_IMAGE=ghcr.io/thor-rt/adaptivecpp-runtime:main

# ============================================================
# Stage 1: Build AdaptiveCpp with the ROCm backend
# ============================================================
FROM ${TOOLCHAIN_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive
ARG CLANG_VERSION=18
ARG ACPP_VERSION=v25.02.0
ARG ROCM_VERSION=6.4.1

# Add AMD's ROCm apt repo and install only the build-time components:
#   rocm-llvm        device clang/lld/llvm
#   rocm-device-libs amdgcn device bitcode
#   hip-dev          HIP headers + libamdhip64 + hipRTC
#   hsa-rocr-dev     libhsa-runtime64
#   comgr            libamd_comgr (device code object manager)
#   hipcc            /opt/rocm/bin/hipcc (required by hip-config.cmake)
# (installs to /opt/rocm; ~0.6 GB download vs ~30 GB for the *-complete image)
#
# The apt pin is required: Ubuntu 24.04 ships an older ROCm 5.7.1 in its
# universe repo, and without preferring repo.radeon.com apt mixes 5.7.1 deps
# into the 6.4.1 install (which breaks hip-config.cmake).
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
ENV PATH="/opt/rocm/bin:${PATH}"
RUN echo "/opt/rocm/lib" > /etc/ld.so.conf.d/rocm.conf && ldconfig

RUN git clone --depth 1 --branch ${ACPP_VERSION} https://github.com/illuhad/hipSYCL.git /hipsycl

RUN cmake -S /hipsycl -B /hipsycl/build \
    -DCMAKE_INSTALL_PREFIX=/opt/hipsycl \
    -DCMAKE_BUILD_TYPE=Release \
    -DWITH_CPU_BACKEND=ON \
    -DWITH_CUDA_BACKEND=OFF \
    -DWITH_ROCM_BACKEND=ON \
    -DROCM_PATH=/opt/rocm \
    -DLLVM_DIR=/usr/lib/llvm-${CLANG_VERSION} \
    -DCLANG_EXECUTABLE_PATH=/usr/bin/clang++-${CLANG_VERSION}

RUN cmake --build /hipsycl/build --target install

# ============================================================
# Stage 2: Runtime image + slim ROCm slice + AdaptiveCpp
# ============================================================
FROM ${RUNTIME_IMAGE}

# Copy only what the AdaptiveCpp SSCP/HIP JIT path needs at runtime:
# - libamdhip64 / libhsa-runtime64 : HIP + HSA runtime
# - libhiprtc(+builtins)           : HIP runtime compilation (hipRTC)
# - libamd_comgr                   : JIT compile/link of device code
# - librocprofiler-register        : pulled in by libamdhip64
# - amdgcn/bitcode                 : device bitcode linked at JIT time
# - llvm/bin/lld                   : links the GPU code object
# - include                        : HIP headers needed by acpp at compile time
# (libhsakmt is folded into the HSA runtime in ROCm 6.4 — not a separate lib)
COPY --from=builder /opt/rocm/lib/libamdhip64.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/libhsa-runtime64.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/libhiprtc*.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/libamd_comgr.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/lib/librocprofiler-register.so* /opt/rocm/lib/
COPY --from=builder /opt/rocm/amdgcn /opt/rocm/amdgcn
COPY --from=builder /opt/rocm/llvm/bin/lld /opt/rocm/llvm/bin/lld
COPY --from=builder /opt/rocm/include /opt/rocm/include
RUN echo "/opt/rocm/lib" > /etc/ld.so.conf.d/rocm.conf \
    && ldconfig

# Copy AdaptiveCpp installation
COPY --from=builder /opt/hipsycl /opt/hipsycl

# Environment
ENV ROCM_PATH=/opt/rocm
ENV HIPSYCL_INSTALL_DIR=/opt/hipsycl
ENV PATH="${HIPSYCL_INSTALL_DIR}/bin:/opt/rocm/bin:${PATH}"
ENV CPATH="${HIPSYCL_INSTALL_DIR}/include:${CPATH}"
ENV LD_LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/opt/rocm/lib:${LD_LIBRARY_PATH}"
ENV LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/opt/rocm/lib:${LIBRARY_PATH}"
ENV CC=cc
ENV CXX=acpp
ENV LLVM_COV=/usr/local/bin/llvm-cov

CMD ["bash"]
