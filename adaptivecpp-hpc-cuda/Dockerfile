# AdaptiveCpp HPC container with NVIDIA CUDA support
#
# Multi-stage build: compile AdaptiveCpp with the CUDA backend on the shared
# toolchain image (with the CUDA toolkit copied in), then assemble a slim
# runtime image from adaptivecpp-runtime plus only the CUDA runtime slice.
#
# Produces: ghcr.io/thor-rt/adaptivecpp-hpc-cuda:main

ARG TOOLCHAIN_IMAGE=ghcr.io/thor-rt/adaptivecpp-toolchain:main
ARG RUNTIME_IMAGE=ghcr.io/thor-rt/adaptivecpp-runtime:main
ARG CUDA_IMAGE=nvidia/cuda:12.8.1-devel-ubuntu24.04

# ============================================================
# Stage 1: CUDA toolkit source (devel image, used only to copy from)
# ============================================================
FROM ${CUDA_IMAGE} AS cuda-toolkit

# ============================================================
# Stage 2: Build AdaptiveCpp with the CUDA backend
# ============================================================
FROM ${TOOLCHAIN_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive
ARG CLANG_VERSION=18
ARG ACPP_VERSION=v25.02.0

# Bring in the full CUDA toolkit for the build only (discarded with this stage)
COPY --from=cuda-toolkit /usr/local/cuda /usr/local/cuda
ENV PATH="/usr/local/cuda/bin:${PATH}"

RUN git clone --depth 1 --branch ${ACPP_VERSION} https://github.com/illuhad/hipSYCL.git /hipsycl

RUN cmake -S /hipsycl -B /hipsycl/build \
    -DCMAKE_INSTALL_PREFIX=/opt/hipsycl \
    -DCMAKE_BUILD_TYPE=Release \
    -DWITH_CPU_BACKEND=ON \
    -DWITH_CUDA_BACKEND=ON \
    -DWITH_ROCM_BACKEND=OFF \
    -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda \
    -DLLVM_DIR=/usr/lib/llvm-${CLANG_VERSION} \
    -DCLANG_EXECUTABLE_PATH=/usr/bin/clang++-${CLANG_VERSION}

RUN cmake --build /hipsycl/build --target install

# ============================================================
# Stage 3: Runtime image + slim CUDA slice + AdaptiveCpp
# ============================================================
FROM ${RUNTIME_IMAGE}

# Copy only what's needed from the CUDA toolkit:
# - Runtime libs (libcudart) for execution
# - Headers for acpp compilation
# - nvvm (libdevice bitcode + cicc + libnvvm) for GPU code generation
# - ptxas for PTX assembly
# (skips nvcc, nvprof, nsight, cuBLAS, NCCL, NPP, etc. — saves ~9 GB)
COPY --from=cuda-toolkit /usr/local/cuda/lib64/libcudart*.so* /usr/local/cuda/lib64/
COPY --from=cuda-toolkit /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/
COPY --from=cuda-toolkit /usr/local/cuda/include /usr/local/cuda/include
COPY --from=cuda-toolkit /usr/local/cuda/nvvm /usr/local/cuda/nvvm
COPY --from=cuda-toolkit /usr/local/cuda/bin/ptxas /usr/local/cuda/bin/ptxas
COPY --from=cuda-toolkit /usr/local/cuda/bin/fatbinary /usr/local/cuda/bin/fatbinary
COPY --from=cuda-toolkit /usr/local/cuda/bin/bin2c /usr/local/cuda/bin/bin2c
COPY --from=cuda-toolkit /usr/local/cuda/bin/crt /usr/local/cuda/bin/crt
RUN echo "/usr/local/cuda/lib64" > /etc/ld.so.conf.d/cuda.conf \
    && echo "/usr/local/cuda/nvvm/lib64" >> /etc/ld.so.conf.d/cuda.conf \
    && ldconfig

# Copy AdaptiveCpp installation
COPY --from=builder /opt/hipsycl /opt/hipsycl

# Environment
ENV HIPSYCL_INSTALL_DIR=/opt/hipsycl
ENV PATH="${HIPSYCL_INSTALL_DIR}/bin:/usr/local/cuda/bin:${PATH}"
ENV CPATH="${HIPSYCL_INSTALL_DIR}/include:${CPATH}"
ENV LD_LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"
ENV LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/usr/local/cuda/lib64:${LIBRARY_PATH}"
ENV CC=cc
ENV CXX=acpp
ENV LLVM_COV=/usr/local/bin/llvm-cov

CMD ["bash"]
