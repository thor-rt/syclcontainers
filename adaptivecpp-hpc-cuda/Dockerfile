# AdaptiveCpp HPC container with NVIDIA CUDA support
#
# Multi-stage build: compile AdaptiveCpp with CUDA in devel image,
# then copy into a slim runtime image with only what's needed.
# Produces: ghcr.io/thor-rt/adaptivecpp-hpc-cuda:main

# ============================================================
# Stage 1: Build AdaptiveCpp with CUDA backend
# ============================================================
FROM nvidia/cuda:12.8.1-devel-ubuntu24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

ARG CLANG_VERSION=18
ARG ACPP_VERSION=v25.02.0

# Install LLVM/Clang, CMake, and build tools
RUN apt-get update && apt-get install -y wget gnupg software-properties-common lsb-release \
    # --- Add Kitware APT repo for latest CMake (need cmake>=3.29) ---
    && wget -qO - https://apt.kitware.com/keys/kitware-archive-latest.asc | gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/kitware.list \
    # --- LLVM installation ---
    && wget https://apt.llvm.org/llvm.sh \
    && chmod +x llvm.sh \
    && ./llvm.sh ${CLANG_VERSION} \
    && apt-get update \
    && apt-get install -y \
    build-essential \
    cmake=3.31.8-0kitware1ubuntu24.04.1 \
    cmake-data=3.31.8-0kitware1ubuntu24.04.1 \
    git \
    libstdc++6 \
    libboost-all-dev \
    clang-${CLANG_VERSION} \
    clang-tools-${CLANG_VERSION} \
    libclang-${CLANG_VERSION}-dev \
    llvm-${CLANG_VERSION} \
    llvm-${CLANG_VERSION}-tools \
    llvm-${CLANG_VERSION}-dev \
    libomp-${CLANG_VERSION}-dev \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-${CLANG_VERSION} 100 \
    && update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-${CLANG_VERSION} 100

# Build AdaptiveCpp with CUDA backend
RUN git clone --depth 1 --branch $ACPP_VERSION https://github.com/illuhad/hipSYCL.git /hipsycl

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
# Stage 2: Runtime image — Ubuntu + LLVM/Clang + CUDA runtime + AdaptiveCpp + HPC libs
# ============================================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

ARG CLANG_VERSION=18

# Install LLVM/Clang (needed at compile time by acpp) and CMake
RUN apt-get update && apt-get install -y wget gnupg software-properties-common lsb-release \
    && wget -qO - https://apt.kitware.com/keys/kitware-archive-latest.asc | gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/kitware.list \
    && wget https://apt.llvm.org/llvm.sh \
    && chmod +x llvm.sh \
    && ./llvm.sh ${CLANG_VERSION} \
    && apt-get update \
    && apt-get install -y \
    build-essential \
    cmake=3.31.8-0kitware1ubuntu24.04.1 \
    cmake-data=3.31.8-0kitware1ubuntu24.04.1 \
    git \
    gdb \
    libstdc++6 \
    libboost-all-dev \
    python3-pip \
    clang-${CLANG_VERSION} \
    clang-tools-${CLANG_VERSION} \
    libclang-${CLANG_VERSION}-dev \
    llvm-${CLANG_VERSION} \
    llvm-${CLANG_VERSION}-tools \
    llvm-${CLANG_VERSION}-dev \
    libomp-${CLANG_VERSION}-dev \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-${CLANG_VERSION} 100 \
    && update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-${CLANG_VERSION} 100 \
    && if [ -x /usr/bin/llvm-cov-${CLANG_VERSION} ]; then \
         ln -sf /usr/bin/llvm-cov-${CLANG_VERSION} /usr/local/bin/llvm-cov; \
       elif [ -x /usr/lib/llvm-${CLANG_VERSION}/bin/llvm-cov ]; then \
         ln -sf /usr/lib/llvm-${CLANG_VERSION}/bin/llvm-cov /usr/local/bin/llvm-cov; \
       fi

# Copy only what's needed from the CUDA toolkit:
# - Runtime libs (libcudart) for execution
# - Headers for acpp compilation
# - nvvm (libdevice bitcode + cicc + libnvvm) for GPU code generation
# - ptxas for PTX assembly
# (skips nvcc, nvprof, nsight, cuBLAS, NCCL, NPP, etc. — saves ~9 GB)
COPY --from=builder /usr/local/cuda/lib64/libcudart*.so* /usr/local/cuda/lib64/
COPY --from=builder /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/
COPY --from=builder /usr/local/cuda/include /usr/local/cuda/include
COPY --from=builder /usr/local/cuda/nvvm /usr/local/cuda/nvvm
COPY --from=builder /usr/local/cuda/bin/ptxas /usr/local/cuda/bin/ptxas
COPY --from=builder /usr/local/cuda/bin/fatbinary /usr/local/cuda/bin/fatbinary
COPY --from=builder /usr/local/cuda/bin/bin2c /usr/local/cuda/bin/bin2c
COPY --from=builder /usr/local/cuda/bin/crt /usr/local/cuda/bin/crt
RUN echo "/usr/local/cuda/lib64" > /etc/ld.so.conf.d/cuda.conf \
    && echo "/usr/local/cuda/nvvm/lib64" >> /etc/ld.so.conf.d/cuda.conf \
    && ldconfig

# Copy AdaptiveCpp installation
COPY --from=builder /opt/hipsycl /opt/hipsycl

# Install HPC libraries (HDF5, OpenMPI, GMP)
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-serial-dev \
    hdf5-tools \
    openmpi-bin \
    libopenmpi-dev \
    libgmp-dev \
    libtbb-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python

# Environment
ENV HIPSYCL_INSTALL_DIR=/opt/hipsycl
ENV PATH="${HIPSYCL_INSTALL_DIR}/bin:/usr/lib/openmpi/bin:${PATH}"
ENV CPATH="${HIPSYCL_INSTALL_DIR}/include:${CPATH}"
ENV LD_LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"
ENV LIBRARY_PATH="${HIPSYCL_INSTALL_DIR}/lib:/usr/local/cuda/lib64:${LIBRARY_PATH}"
ENV CC=cc
ENV CXX=acpp
ENV LLVM_COV=/usr/local/bin/llvm-cov

CMD ["bash"]
