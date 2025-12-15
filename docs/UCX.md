# UCX Backend (Standard)

This document describes deploying TensorRT-LLM disaggregated inference with UCX backend.

## Overview

UCX (Unified Communication X) is the default NIXL backend that works on any hardware. It supports TCP, InfiniBand, RoCE, and shared memory transports.

## Use Cases

- On-premises deployments without EFA
- AWS instances without EFA support
- Development and testing
- InfiniBand clusters (p4d.24xlarge with 400Gbps IB)

## Prerequisites

### Infrastructure
- Kubernetes cluster with GPU nodes
- Any NVIDIA GPU instances
- NVIDIA GPU operator

### Software
- kubectl configured for cluster
- Docker with NVIDIA runtime

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│  Prefill Worker │────▶│  Decode Worker  │
│   (HTTP API)    │     │  (KV Cache Gen) │     │ (Token Gen)     │
└─────────────────┘     └────────┬────────┘     └────────▲────────┘
                                 │                       │
                                 │   NIXL KV Transfer    │
                                 │        (UCX)          │
                                 │   TCP/IB/RoCE/SHM     │
                                 └───────────────────────┘
```

## Environment Variables

### Required
```bash
NIXL_BACKEND=UCX                 # Select UCX backend (default)
```

### Transport Configuration
```bash
UCX_TLS=tcp,srd,cuda_copy,cuda_ipc,sm,self
UCX_NET_DEVICES=all
UCX_IB_GPU_DIRECT_RDMA=yes
```

### Debugging
```bash
UCX_LOG_LEVEL=warn               # info, debug, trace
```

## Quick Start

```bash
# 1. Deploy (uses pre-built image)
kubectl apply -f kubernetes/common/configmap.yaml
kubectl apply -f kubernetes/ucx/deployment.yaml

# 2. Test
./scripts/test-inference.sh trtllm-ucx
```

## Optional: Build Custom Image

```bash
cd docker/ucx
./build.sh
```

## Kubernetes Configuration

UCX deployments are simpler than LIBFABRIC - no EFA devices or special mounts needed.

### Minimal Resources
```yaml
resources:
  limits:
    cpu: "16"
    memory: 64Gi
    nvidia.com/gpu: "1"
  requests:
    cpu: "16"
    memory: 64Gi
    nvidia.com/gpu: "1"
```

### Security Context
```yaml
securityContext:
  capabilities:
    add:
    - IPC_LOCK
    - SYS_RESOURCE
  privileged: true
```

## Transport Selection

UCX automatically selects the best transport based on available hardware:

| Transport | Description | When Used |
|-----------|-------------|-----------|
| tcp | TCP/IP | Always available |
| srd | InfiniBand SRD | p4d instances |
| cuda_copy | GPU-CPU memory copy | NVIDIA GPUs |
| cuda_ipc | GPU shared memory | Same node GPUs |
| sm | Shared memory | Same node |
| self | Self-loop | Local |

## Troubleshooting

### UCX Not Initializing
```bash
# Check UCX configuration
kubectl exec -it <pod> -- ucx_info -d
```

### Slow Performance
Try different transport configurations:
```bash
# InfiniBand only
UCX_TLS=rc,ud,cuda_copy,cuda_ipc

# TCP only
UCX_TLS=tcp,cuda_copy
```
