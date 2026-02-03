# Note: Using Ubuntu base instead of intel/oneapi-hpckit (~10-15 GB) which is too large for GitHub Actions runners
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Intel oneAPI repository and only the SYCL compiler components
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    && wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB | gpg --dearmor | tee /usr/share/keyrings/oneapi-archive-keyring.gpg > /dev/null \
    && echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" | tee /etc/apt/sources.list.d/oneAPI.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gdb \
    cmake \
    ninja-build \
    libboost-dev \
    libboost-program-options-dev \
    python3-pip \
    intel-oneapi-compiler-dpcpp-cpp-2025.0 \
    intel-oneapi-mkl-devel-2025.0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* \
    && rm -rf /opt/intel/oneapi/compiler/latest/opt/oclfpga

# Build PoCL from source with SPIR-V support for SYCL compatibility
# Ubuntu's packaged PoCL lacks SPIR-V support required by Intel SYCL
ARG LLVM_VERSION=19
ARG POCL_VERSION=v7.1

RUN wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key | tee /etc/apt/trusted.gpg.d/apt.llvm.org.asc >/dev/null \
    && echo "deb http://apt.llvm.org/noble/ llvm-toolchain-noble-${LLVM_VERSION} main" > /etc/apt/sources.list.d/llvm.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    clang-${LLVM_VERSION} \
    llvm-${LLVM_VERSION}-dev \
    libclang-${LLVM_VERSION}-dev \
    libclang-cpp${LLVM_VERSION}-dev \
    libpolly-${LLVM_VERSION}-dev \
    llvm-spirv-${LLVM_VERSION} \
    libllvmspirvlib-${LLVM_VERSION}-dev \
    libhwloc-dev \
    libzstd-dev \
    zlib1g-dev \
    ocl-icd-libopencl1 \
    ocl-icd-opencl-dev \
    clinfo \
    # Build PoCL with static LLVM to avoid symbol conflicts with DPC++
    && git clone --depth 1 --branch ${POCL_VERSION} https://github.com/pocl/pocl.git /tmp/pocl \
    && sed -i 's/",+SPV_INTEL_inline_assembly";/",+SPV_INTEL_inline_assembly"\n                                       ",+SPV_INTEL_optnone";/' \
        /tmp/pocl/lib/CL/devices/common_utils.c \
    && mkdir /tmp/pocl-build && cd /tmp/pocl-build \
    && CC=clang-${LLVM_VERSION} CXX=clang++-${LLVM_VERSION} cmake /tmp/pocl \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/opt/pocl \
        -DENABLE_SPIRV=ON \
        -DLLVM_SPIRV=/usr/bin/llvm-spirv-${LLVM_VERSION} \
        -DWITH_LLVM_CONFIG=/usr/bin/llvm-config-${LLVM_VERSION} \
        -DLLVM_SPIRV_INCLUDEDIR=/usr/include/LLVMSPIRVLib \
        -DLLVM_SPIRV_LIB=/usr/lib/x86_64-linux-gnu/libLLVMSPIRVLib.so \
        -DSTATIC_LLVM=ON \
        -DENABLE_ICD=ON \
        -G Ninja \
    && ninja -j$(nproc) \
    && ninja install \
    # Cleanup build artifacts and dev packages
    && rm -rf /tmp/pocl /tmp/pocl-build \
    && apt-get remove -y --purge \
        llvm-${LLVM_VERSION}-dev libclang-${LLVM_VERSION}-dev libclang-cpp${LLVM_VERSION}-dev \
        libpolly-${LLVM_VERSION}-dev libclang-rt-${LLVM_VERSION}-dev libclang-common-${LLVM_VERSION}-dev \
        mesa-vulkan-drivers mesa-libgallium libllvm20 libllvm17t64 ocl-icd-opencl-dev \
    && apt-mark manual libboost-dev libboost-program-options-dev \
    && apt-get autoremove -y && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/*

# Create ICD file for PoCL
RUN mkdir -p /etc/OpenCL/vendors \
    && echo '/opt/pocl/lib/libpocl.so' > /etc/OpenCL/vendors/pocl.icd

# Set up Intel oneAPI environment variables
ENV ONEAPI_ROOT=/opt/intel/oneapi
ENV CMPLR_ROOT=${ONEAPI_ROOT}/compiler/latest
ENV PATH=${CMPLR_ROOT}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CMPLR_ROOT}/lib:${ONEAPI_ROOT}/tbb/latest/lib:${ONEAPI_ROOT}/umf/latest/lib
ENV CPATH=${CMPLR_ROOT}/include
ENV LIBRARY_PATH=${CMPLR_ROOT}/lib

# Set Intel compilers as default
ENV CC=icx
ENV CXX=icpx

CMD ["bash"]
