#!/bin/bash
# Deploy TensorRT-LLM to Kubernetes
#
# Usage:
#   ./deploy.sh libfabric             # Deploy LIBFABRIC variant
#   ./deploy.sh ucx                   # Deploy UCX variant
#   ./deploy.sh all                   # Deploy both variants

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

DEPLOY_TARGET="${1:-}"

if [[ -z "$DEPLOY_TARGET" ]]; then
    echo "Usage: $0 [libfabric|ucx|all]"
    exit 1
fi

deploy_common() {
    echo "=== Deploying common ConfigMap ==="
    kubectl apply -f "$REPO_ROOT/kubernetes/common/configmap.yaml"
}

deploy_libfabric() {
    echo "=== Deploying LIBFABRIC variant ==="
    kubectl apply -f "$REPO_ROOT/kubernetes/libfabric/deployment.yaml"
    echo ""
    echo "Waiting for pods..."
    kubectl get pods -l app.kubernetes.io/instance=trtllm-libfabric -w &
    WATCH_PID=$!
    sleep 30
    kill $WATCH_PID 2>/dev/null || true
    kubectl get pods -l app.kubernetes.io/instance=trtllm-libfabric
}

deploy_ucx() {
    echo "=== Deploying UCX variant ==="
    kubectl apply -f "$REPO_ROOT/kubernetes/ucx/deployment.yaml"
    echo ""
    echo "Waiting for pods..."
    kubectl get pods -l app.kubernetes.io/instance=trtllm-ucx -w &
    WATCH_PID=$!
    sleep 30
    kill $WATCH_PID 2>/dev/null || true
    kubectl get pods -l app.kubernetes.io/instance=trtllm-ucx
}

deploy_common

case "$DEPLOY_TARGET" in
    libfabric)
        deploy_libfabric
        ;;
    ucx)
        deploy_ucx
        ;;
    all)
        deploy_libfabric
        deploy_ucx
        ;;
    *)
        echo "Unknown target: $DEPLOY_TARGET"
        echo "Usage: $0 [libfabric|ucx|all]"
        exit 1
        ;;
esac

echo ""
echo "=== Deployment complete ==="
