# AdaptiveCpp toolchain image
#
# The single source of truth for the LLVM/Clang + CMake build environment used
# by every AdaptiveCpp image in this repo. It contains *no* AdaptiveCpp build
# and *no* HPC libraries (HDF5/OpenMPI) — it is the toolchain only.
#
# Downstream images use this as their build stage:
#   FROM ghcr.io/thor-rt/adaptivecpp-toolchain:main AS builder
# and pair it with the matching adaptivecpp-runtime image for the final stage.
#
# Produces: ghcr.io/thor-rt/adaptivecpp-toolchain:main

FROM ubuntu:24.04

# Set environment variables to non-interactive (this avoids some prompts)
ENV DEBIAN_FRONTEND=noninteractive

# Define the default Clang version as an argument with a default value
ARG CLANG_VERSION=18

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

# Set the default command to bash
CMD ["bash"]
