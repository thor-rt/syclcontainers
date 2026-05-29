# AdaptiveCpp HPC image
#
# The HPC libraries (HDF5, OpenMPI, GMP, TBB) now live in adaptivecpp-runtime,
# which adaptivecpp-base is built on top of, so this image no longer adds
# anything. It is kept as a thin alias of adaptivecpp-base for backward
# compatibility with consumers that pull adaptivecpp-hpc.
#
# Produces: ghcr.io/thor-rt/adaptivecpp-hpc:main

ARG BASE_IMAGE=ghcr.io/thor-rt/adaptivecpp-base:main
FROM ${BASE_IMAGE}

CMD ["bash"]
