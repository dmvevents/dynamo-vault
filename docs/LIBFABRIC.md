# LIBFABRIC Backend for AWS EFA

This document describes deploying TensorRT-LLM disaggregated inference with LIBFABRIC backend on AWS EFA.

## Overview

LIBFABRIC is NVIDIA's high-performance networking backend that integrates with AWS Elastic Fabric Adapter (EFA) for low-latency KV cache transfer in disaggregated inference.

## Prerequisites

### AWS Infrastructure
- EKS cluster with GPU nodes
- p5.48xlarge or p4d.24xlarge instances (with EFA)
- EFA device plugin installed
- NVIDIA GPU operator

### Software
- kubectl configured for cluster
- Docker with NVIDIA runtime
- AWS CLI with ECR access

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│  Prefill Worker │────▶│  Decode Worker  │
│   (HTTP API)    │     │  (KV Cache Gen) │     │ (Token Gen)     │
└─────────────────┘     └────────┬────────┘     └────────▲────────┘
                                 │                       │
                                 │   NIXL KV Transfer    │
                                 │      (LIBFABRIC)      │
                                 │     over AWS EFA      │
                                 └───────────────────────┘
```

## Environment Variables

### Required
```bash
NIXL_BACKEND=LIBFABRIC          # Select LIBFABRIC backend
FI_PROVIDER=efa                  # Use EFA provider
FI_EFA_USE_DEVICE_RDMA=1        # Enable RDMA
```

### Recommended
```bash
FI_HMEM_DISABLE_P2P=1           # Disable peer-to-peer (required for EFA)
FI_EFA_ENABLE_SHM=0             # Disable shared memory
FI_MR_CACHE_MAX_COUNT=0         # Disable memory region cache
FI_MR_CACHE_MONITOR=disabled    # Disable cache monitor
FI_EFA_FORK_SAFE=1              # Enable fork safety
RDMAV_FORK_SAFE=1               # Enable RDMA fork safety
```

### Performance Tuning
```bash
FI_EFA_TX_SIZE=8192             # TX queue size
FI_EFA_RX_SIZE=8192             # RX queue size
FI_EFA_CQ_SIZE=16384            # Completion queue size
```

## Kubernetes Configuration

### EFA Device Mounting
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: "1"
  requests:
    vpc.amazonaws.com/efa: "1"
volumeMounts:
- name: dev-infiniband
  mountPath: /dev/infiniband
volumes:
- name: dev-infiniband
  hostPath:
    path: /dev/infiniband
    type: DirectoryOrCreate
```

### Security Context
```yaml
securityContext:
  capabilities:
    add:
    - IPC_LOCK
    - SYS_RESOURCE
    - NET_ADMIN
    - SYS_ADMIN
  privileged: true
```

### Hugepages
```yaml
resources:
  limits:
    hugepages-2Mi: 5120Mi
  requests:
    hugepages-2Mi: 5120Mi
volumeMounts:
- name: hugepages
  mountPath: /dev/hugepages
volumes:
- name: hugepages
  emptyDir:
    medium: HugePages
```

## Quick Start

```bash
# 1. Build LIBFABRIC image
cd docker/libfabric
./build.sh

# 2. Push to ECR
docker tag dynamo-trtllm:libfabric public.ecr.aws/YOUR_REGISTRY/dynamo-trtllm:libfabric
docker push public.ecr.aws/YOUR_REGISTRY/dynamo-trtllm:libfabric

# 3. Deploy
kubectl apply -f kubernetes/common/configmap.yaml
kubectl apply -f kubernetes/libfabric/deployment.yaml

# 4. Test
./scripts/test-inference.sh trtllm-libfabric
```

## Troubleshooting

### EFA Not Detected
```bash
# Check for EFA devices
kubectl exec -it <pod> -- ibv_devices
kubectl exec -it <pod> -- ls -la /dev/infiniband/
```

### LIBFABRIC Plugin Not Found
```bash
# Verify plugin exists
kubectl exec -it <pod> -- ls -la /opt/nvidia/nvda_nixl/lib/x86_64-linux-gnu/plugins/libplugin_LIBFABRIC.so
```

### Backend Not Initialized
Check logs for:
```
NIXL Connect: Using backend(s): ['LIBFABRIC']
Backend LIBFABRIC was instantiated
```

If you see UCX instead, verify:
1. NIXL_BACKEND environment variable is set
2. The patched image is being used
3. The pod is using the correct image tag
