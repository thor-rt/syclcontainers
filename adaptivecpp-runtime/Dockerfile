# AdaptiveCpp runtime image
#
# The toolchain plus the HPC libraries (HDF5, OpenMPI, GMP, TBB) needed to run
# AdaptiveCpp applications. AdaptiveCpp's host compile path still invokes clang
# at runtime, so the full LLVM/Clang toolchain is retained rather than slimmed.
#
# This is the final-stage base for every AdaptiveCpp image in this repo:
#   FROM ghcr.io/thor-rt/adaptivecpp-runtime:main
#   COPY --from=builder /opt/hipsycl /opt/hipsycl
#
# Building FROM the toolchain image keeps the LLVM/CMake apt block defined in
# exactly one place (adaptivecpp-toolchain).
#
# Produces: ghcr.io/thor-rt/adaptivecpp-runtime:main

ARG TOOLCHAIN_IMAGE=ghcr.io/thor-rt/adaptivecpp-toolchain:main
FROM ${TOOLCHAIN_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

# Install HPC libraries (HDF5, OpenMPI, GMP, TBB)
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

# Make OpenMPI binaries (mpirun/orterun) discoverable
ENV PATH="/usr/lib/openmpi/bin:${PATH}"

CMD ["bash"]
