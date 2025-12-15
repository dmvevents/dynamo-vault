#!/bin/bash
# Test inference endpoint
#
# Usage:
#   ./test-inference.sh trtllm-libfabric    # Test LIBFABRIC deployment
#   ./test-inference.sh trtllm-ucx          # Test UCX deployment

set -e

DEPLOYMENT_NAME="${1:-trtllm-libfabric}"
MODEL="${2:-Qwen/Qwen3-0.6B}"
PROMPT="${3:-Hello, how are you?}"

SERVICE_NAME="${DEPLOYMENT_NAME}-frontend"
LOCAL_PORT=8000

echo "=== Testing inference for $DEPLOYMENT_NAME ==="
echo "Model: $MODEL"
echo "Prompt: $PROMPT"
echo ""

# Check if service exists
if ! kubectl get svc "$SERVICE_NAME" &>/dev/null; then
    echo "ERROR: Service $SERVICE_NAME not found"
    echo "Available services:"
    kubectl get svc | grep frontend || echo "No frontend services found"
    exit 1
fi

# Check if pods are ready
echo "Checking pod status..."
kubectl get pods -l app.kubernetes.io/instance="$DEPLOYMENT_NAME"

FRONTEND_POD=$(kubectl get pods -l app.kubernetes.io/instance="$DEPLOYMENT_NAME",app.kubernetes.io/component=frontend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [[ -z "$FRONTEND_POD" ]]; then
    echo "ERROR: Frontend pod not found"
    exit 1
fi

POD_STATUS=$(kubectl get pod "$FRONTEND_POD" -o jsonpath='{.status.phase}')
if [[ "$POD_STATUS" != "Running" ]]; then
    echo "WARNING: Frontend pod is $POD_STATUS, not Running"
fi

# Start port-forward in background
echo ""
echo "Starting port-forward..."
kubectl port-forward "svc/$SERVICE_NAME" "$LOCAL_PORT:8000" &
PF_PID=$!
sleep 3

# Function to cleanup port-forward
cleanup() {
    kill $PF_PID 2>/dev/null || true
}
trap cleanup EXIT

# Test health endpoint
echo ""
echo "Testing health endpoint..."
if curl -sf "http://localhost:$LOCAL_PORT/health" &>/dev/null; then
    echo "Health check: OK"
else
    echo "Health check: FAILED (might not have /health endpoint)"
fi

# Test completions endpoint
echo ""
echo "Testing completions endpoint..."
RESPONSE=$(curl -sf "http://localhost:$LOCAL_PORT/v1/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$MODEL\", \"prompt\": \"$PROMPT\", \"max_tokens\": 30}" 2>&1)

if [[ $? -eq 0 ]]; then
    echo "Response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""
    echo "=== Inference test PASSED ==="
else
    echo "ERROR: Inference request failed"
    echo "$RESPONSE"
    echo ""
    echo "=== Inference test FAILED ==="
    exit 1
fi
