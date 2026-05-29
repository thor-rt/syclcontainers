#!/bin/bash
# Build the container images locally and tag them as ghcr.io/thor-rt/<name>:main
# so downstream images resolve their FROM/build-args against the local builds.
#
# Usage:
#   ./build-local.sh                # build the AdaptiveCpp chain (toolchain..base)
#   ./build-local.sh cuda           # ...plus adaptivecpp-hpc-cuda
#   ./build-local.sh rocm           # ...plus adaptivecpp-hpc-rocm
#   ./build-local.sh multigpu       # ...plus adaptivecpp-hpc-multigpu (cuda+rocm)
#   ./build-local.sh intel          # build the Intel oneAPI chain
#   ./build-local.sh all            # everything
set -e

REGISTRY_PREFIX="ghcr.io/thor-rt"
TARGET="${1:-base}"

build() {
  local name="$1"
  echo ""
  echo "==> Building ${name}..."
  docker build -t "${name}:local" -t "${REGISTRY_PREFIX}/${name}:main" "./${name}"
}

build_acpp_chain() {
  build adaptivecpp-toolchain
  build adaptivecpp-runtime
  build adaptivecpp-base
}

case "$TARGET" in
  base)
    build_acpp_chain
    ;;
  cuda)
    build_acpp_chain
    build adaptivecpp-hpc-cuda
    ;;
  rocm)
    build_acpp_chain
    build adaptivecpp-hpc-rocm
    ;;
  multigpu)
    build_acpp_chain
    build adaptivecpp-hpc-multigpu
    ;;
  intel)
    build intel-sycl-base
    build intel-sycl-hpc
    ;;
  all)
    build_acpp_chain
    build adaptivecpp-hpc-cuda
    build adaptivecpp-hpc-rocm
    build adaptivecpp-hpc-multigpu
    build intel-sycl-base
    build intel-sycl-hpc
    ;;
  *)
    echo "Unknown target: $TARGET" >&2
    echo "Valid targets: base, cuda, rocm, multigpu, intel, all" >&2
    exit 1
    ;;
esac

echo ""
echo "Build complete."
echo ""
echo "Quick checks:"
echo "  docker run --rm adaptivecpp-toolchain:local bash -c 'clang --version && cmake --version'"
echo "  docker run --rm -v ./tests:/tests adaptivecpp-base:local /tests/run_tests.sh"

if [ "$TARGET" = "multigpu" ] || [ "$TARGET" = "all" ]; then
  echo ""
  echo "NOTE: multigpu is a dev/CI-only image and is not built by the CI"
  echo "pipeline. Publish it manually after building, e.g.:"
  echo "  docker push ${REGISTRY_PREFIX}/adaptivecpp-hpc-multigpu:main"
fi
