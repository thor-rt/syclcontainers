# AdaptiveCpp base image (CPU backend)
#
# Multi-stage build: compile AdaptiveCpp on the shared toolchain image, then
# copy the install into the slim runtime image. All LLVM/CMake/HPC setup lives
# in adaptivecpp-toolchain / adaptivecpp-runtime — this file only builds acpp.
#
# Produces: ghcr.io/thor-rt/adaptivecpp-base:main

ARG TOOLCHAIN_IMAGE=ghcr.io/thor-rt/adaptivecpp-toolchain:main
ARG RUNTIME_IMAGE=ghcr.io/thor-rt/adaptivecpp-runtime:main

# ============================================================
# Stage 1: Build AdaptiveCpp with the CPU backend
# ============================================================
FROM ${TOOLCHAIN_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive
ARG CLANG_VERSION=18
ARG ACPP_VERSION=v25.02.0

# Clone and build AdaptiveCpp (hipSYCL)
RUN git clone --depth 1 --branch ${ACPP_VERSION} https://github.com/illuhad/hipSYCL.git /hipsycl

RUN cmake -S /hipsycl -B /hipsycl/build \
    -DCMAKE_INSTALL_PREFIX=/opt/hipsycl \
    -DCMAKE_BUILD_TYPE=Release \
    -DWITH_CPU_BACKEND=ON \
    -DWITH_CUDA_BACKEND=OFF \
    -DWITH_ROCM_BACKEND=OFF \
    -DLLVM_DIR=/usr/lib/llvm-${CLANG_VERSION} \
    -DCLANG_EXECUTABLE_PATH=/usr/bin/clang++-${CLANG_VERSION}

RUN cmake --build /hipsycl/build --target install

# ============================================================
# Stage 2: Runtime image + AdaptiveCpp install
# ============================================================
FROM ${RUNTIME_IMAGE}

# Copy AdaptiveCpp installation
COPY --from=builder /opt/hipsycl /opt/hipsycl

# Setting environment variables for AdaptiveCpp
ENV HIPSYCL_INSTALL_DIR=/opt/hipsycl
ENV PATH="${HIPSYCL_INSTALL_DIR}/bin:${PATH}"
ENV CPATH="${HIPSYCL_INSTALL_DIR}/include:${CPATH}"
ENV LD_LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:${LD_LIBRARY_PATH}"
ENV LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:${LIBRARY_PATH}"
ENV CC=cc
ENV CXX=acpp
ENV LLVM_COV=/usr/local/bin/llvm-cov

# Set the default command to bash
CMD ["bash"]
