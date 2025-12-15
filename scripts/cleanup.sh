#!/bin/bash
# Clean up TensorRT-LLM deployments
#
# Usage:
#   ./cleanup.sh libfabric            # Clean up LIBFABRIC deployment
#   ./cleanup.sh ucx                  # Clean up UCX deployment
#   ./cleanup.sh all                  # Clean up all deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

CLEANUP_TARGET="${1:-}"

if [[ -z "$CLEANUP_TARGET" ]]; then
    echo "Usage: $0 [libfabric|ucx|all]"
    exit 1
fi

cleanup_libfabric() {
    echo "=== Cleaning up LIBFABRIC deployment ==="
    kubectl delete -f "$REPO_ROOT/kubernetes/libfabric/deployment.yaml" --ignore-not-found
}

cleanup_ucx() {
    echo "=== Cleaning up UCX deployment ==="
    kubectl delete -f "$REPO_ROOT/kubernetes/ucx/deployment.yaml" --ignore-not-found
}

cleanup_common() {
    echo "=== Cleaning up common ConfigMap ==="
    kubectl delete -f "$REPO_ROOT/kubernetes/common/configmap.yaml" --ignore-not-found
}

case "$CLEANUP_TARGET" in
    libfabric)
        cleanup_libfabric
        ;;
    ucx)
        cleanup_ucx
        ;;
    all)
        cleanup_libfabric
        cleanup_ucx
        cleanup_common
        ;;
    *)
        echo "Unknown target: $CLEANUP_TARGET"
        echo "Usage: $0 [libfabric|ucx|all]"
        exit 1
        ;;
esac

echo ""
echo "=== Cleanup complete ==="
kubectl get pods 2>/dev/null | grep -E "trtllm-(libfabric|ucx)" || echo "No trtllm pods remaining"
