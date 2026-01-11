# Use an official Ubuntu 24.04 LTS as a parent image
FROM ubuntu:24.04

# Set environment variables to non-interactive (this avoids some prompts)
ENV DEBIAN_FRONTEND=noninteractive

# Define the default Clang version as an argument with a default value
ARG CLANG_VERSION=18

# Set AdaptiveCpp version
ARG ACPP_VERSION=v25.02.0

# Install necessary packages and add LLVM repository
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
    # use last version 3 cmake version
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

# Set clang and llvm-config binaries to the installed version
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-${CLANG_VERSION} 100 \
    && update-alternatives --install /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-${CLANG_VERSION} 100 \
    && if [ -x /usr/bin/llvm-cov-${CLANG_VERSION} ]; then \
         ln -sf /usr/bin/llvm-cov-${CLANG_VERSION} /usr/local/bin/llvm-cov; \
       elif [ -x /usr/lib/llvm-${CLANG_VERSION}/bin/llvm-cov ]; then \
         ln -sf /usr/lib/llvm-${CLANG_VERSION}/bin/llvm-cov /usr/local/bin/llvm-cov; \
       fi

# Clone the AdaptiveCpp repository
RUN git clone --depth 1 --branch $ACPP_VERSION https://github.com/illuhad/hipSYCL.git /hipsycl

# Set the working directory to the hipSYCL directory
WORKDIR /hipsycl

# Create a build directory
RUN mkdir build

# Configure the project with CMake
RUN cmake -S . -B build \
    -DCMAKE_INSTALL_PREFIX=/opt/hipsycl \
    -DCMAKE_BUILD_TYPE=Release \
    -DWITH_CPU_BACKEND=ON \
    -DWITH_CUDA_BACKEND=OFF \
    -DWITH_ROCM_BACKEND=OFF \
    -DLLVM_DIR=/usr/lib/llvm-${CLANG_VERSION} \
    -DCLANG_EXECUTABLE_PATH=/usr/bin/clang++-${CLANG_VERSION}

# Build and install
RUN cmake --build build --target install

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
