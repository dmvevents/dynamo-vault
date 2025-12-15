#!/bin/bash
# Build all Docker images
#
# Usage:
#   ./build-all.sh                    # Build all images
#   ./build-all.sh libfabric          # Build LIBFABRIC only
#   ./build-all.sh ucx                # Build UCX only

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

BUILD_TARGET="${1:-all}"

build_libfabric() {
    echo "=== Building LIBFABRIC image ==="
    cd "$REPO_ROOT/docker/libfabric"
    ./build.sh h100-libfabric
}

build_ucx() {
    echo "=== Building UCX image ==="
    cd "$REPO_ROOT/docker/ucx"
    ./build.sh h100-ucx
}

case "$BUILD_TARGET" in
    libfabric)
        build_libfabric
        ;;
    ucx)
        build_ucx
        ;;
    all)
        build_libfabric
        build_ucx
        ;;
    *)
        echo "Unknown target: $BUILD_TARGET"
        echo "Usage: $0 [libfabric|ucx|all]"
        exit 1
        ;;
esac

echo ""
echo "=== Build complete ==="
docker images | grep dynamo-trtllm
