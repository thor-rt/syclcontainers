# AdaptiveCpp runtime image
#
# The toolchain plus the HPC libraries (HDF5, Open MPI, GMP, TBB) needed to run
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
# Open MPI 5 and UCX are built from source into /opt/openmpi. Ubuntu 24.04
# packages Open MPI 4.1.6, whose PMIx client segfaults when two threads of a
# rank make first contact with a peer at the same time (UCX transport,
# MPI_THREAD_MULTIPLE). UCX is built with thread support, without which Open
# MPI refuses it under MPI_THREAD_MULTIPLE. Launch multi-node jobs with
# `srun --mpi=pmix`: Open MPI 5 has no PMI-1/PMI-2 support. [AI-Claude]
#
# Produces: ghcr.io/thor-rt/adaptivecpp-runtime:main

ARG TOOLCHAIN_IMAGE=ghcr.io/thor-rt/adaptivecpp-toolchain:main

# ============================================================
# Stage 1: Build UCX and Open MPI
# ============================================================
FROM ${TOOLCHAIN_IMAGE} AS mpi-builder

ENV DEBIAN_FRONTEND=noninteractive
ARG UCX_VERSION=1.16.0
ARG UCX_SHA256=f73770d3b583c91aba5fb07557e655ead0786e057018bfe42f0ebe8716e9d28c
ARG OMPI_VERSION=5.0.11
ARG OMPI_SHA256=e668a3c4acd50c41dc204c8a6dd98a611e0f26af89cf677577fa9be8a2698003
ARG MPI_PREFIX=/opt/openmpi

# The network stacks Ubuntu's Open MPI also supports: InfiniBand/RoCE (verbs and
# rdmacm, through UCX), libfabric (OFI) and Omni-Path (PSM2).
RUN apt-get update && apt-get install -y \
    wget bzip2 perl \
    libibverbs-dev librdmacm-dev libnuma-dev \
    libfabric-dev libpsm2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /build && cd /build \
    && wget -q https://github.com/openucx/ucx/releases/download/v${UCX_VERSION}/ucx-${UCX_VERSION}.tar.gz \
    && wget -q https://download.open-mpi.org/release/open-mpi/v${OMPI_VERSION%.*}/openmpi-${OMPI_VERSION}.tar.bz2 \
    && echo "${UCX_SHA256}  ucx-${UCX_VERSION}.tar.gz" | sha256sum -c - \
    && echo "${OMPI_SHA256}  openmpi-${OMPI_VERSION}.tar.bz2" | sha256sum -c -

# The GNU compilers build both libraries.
RUN cd /build && tar xzf ucx-${UCX_VERSION}.tar.gz && cd ucx-${UCX_VERSION} \
    && CC=gcc CXX=g++ ./contrib/configure-release --prefix=${MPI_PREFIX} --enable-mt \
       --disable-static --without-cuda --without-rocm --without-java \
    && make -j"$(nproc)" && make install

RUN cd /build && tar xjf openmpi-${OMPI_VERSION}.tar.bz2 && cd openmpi-${OMPI_VERSION} \
    && CC=gcc CXX=g++ ./configure --prefix=${MPI_PREFIX} \
       --with-ucx=${MPI_PREFIX} --with-ofi --with-psm2 --with-slurm \
       --with-pmix=internal --with-prrte=internal \
       --with-hwloc=internal --with-libevent=internal \
       --disable-mpi-fortran --disable-oshmem --disable-static \
    && make -j"$(nproc)" && make install

# ============================================================
# Stage 2: Toolchain + HPC libraries + Open MPI
# ============================================================
FROM ${TOOLCHAIN_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ARG MPI_PREFIX=/opt/openmpi

# Install HPC libraries (HDF5, GMP, TBB) and the network libraries Open MPI links
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-serial-dev \
    hdf5-tools \
    libgmp-dev \
    libtbb-dev \
    libibverbs1 ibverbs-providers librdmacm1t64 libnuma1 \
    libfabric1 libpsm2-2 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python

COPY --from=mpi-builder ${MPI_PREFIX} ${MPI_PREFIX}

# Make Open MPI's wrappers, launchers and libraries discoverable
RUN echo "${MPI_PREFIX}/lib" > /etc/ld.so.conf.d/openmpi.conf && ldconfig
ENV PATH="${MPI_PREFIX}/bin:${PATH}"

CMD ["bash"]
