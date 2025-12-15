#!/bin/bash
# Build script for UCX backend Docker image
#
# Usage:
#   ./build.sh                    # Build with default tag
#   ./build.sh my-custom-tag      # Build with custom tag

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAG="${1:-ucx}"

echo "=== Building TRT-LLM + Dynamo with UCX backend ==="
echo "Tag: dynamo-trtllm:$TAG"
echo ""

cd "$SCRIPT_DIR"

# Verify required files exist
if [[ ! -f "Dockerfile" ]]; then
    echo "ERROR: Dockerfile not found in $SCRIPT_DIR"
    exit 1
fi

# Build the image
docker build \
    -t "dynamo-trtllm:$TAG" \
    -f Dockerfile \
    .

echo ""
echo "=== Build complete ==="
echo "Image: dynamo-trtllm:$TAG"
echo ""
echo "To push to ECR:"
echo "  docker tag dynamo-trtllm:$TAG public.ecr.aws/YOUR_REGISTRY/dynamo-trtllm:$TAG"
echo "  docker push public.ecr.aws/YOUR_REGISTRY/dynamo-trtllm:$TAG"
