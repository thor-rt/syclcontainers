# Use the custom Intel SYCL base image
ARG BASE_IMAGE=ghcr.io/thor-rt/intel-sycl-base:main
FROM ${BASE_IMAGE}

# Set environment variables to non-interactive
ENV DEBIAN_FRONTEND=noninteractive

# Install HDF5 and additional HPC libraries
# Note: Intel MPI is already included in the oneAPI HPC Kit base image
RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-serial-dev \
    hdf5-tools \
    libgmp-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/intel-mpi-2021.17.0.377_offline.sh \
        https://registrationcenter-download.intel.com/akdlm/IRC_NAS/0a3cb474-49c7-45a9-9dea-104122592a63/intel-mpi-2021.17.0.377_offline.sh \
    && sh /tmp/intel-mpi-2021.17.0.377_offline.sh \
        -a --silent --cli --eula accept \
    && rm -f /tmp/intel-mpi-2021.17.0.377_offline.sh

# Intel MPI environment variables
ENV I_MPI_ROOT="/opt/intel/oneapi/mpi/latest"
ENV PATH="${I_MPI_ROOT}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${I_MPI_ROOT}/lib:${I_MPI_ROOT}/opt/mpi/libfabric/lib:${LD_LIBRARY_PATH}"
ENV FI_PROVIDER_PATH="${I_MPI_ROOT}/opt/mpi/libfabric/lib/prov:/usr/lib/x86_64-linux-gnu/libfabric"
ENV CPATH="${I_MPI_ROOT}/include:${CPATH}"

# Command to keep the container running
CMD ["bash"]
