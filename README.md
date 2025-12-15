# Dynamo Vault - TensorRT-LLM + Dynamo on AWS

Complete deployment configurations for TensorRT-LLM disaggregated inference with NVIDIA Dynamo on AWS EKS.

## Overview

This repository provides Docker images and Kubernetes configurations for deploying TensorRT-LLM with different NIXL backends for KV cache transfer:

| Backend | Transport | Best For |
|---------|-----------|----------|
| **LIBFABRIC** | AWS EFA | AWS p5/p4 instances with EFA |
| **UCX** | InfiniBand/RoCE/TCP | On-premises or non-EFA instances |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│  Prefill Worker │────▶│  Decode Worker  │
│   (HTTP API)    │     │  (KV Cache Gen) │     │ (Token Gen)     │
└─────────────────┘     └────────┬────────┘     └────────▲────────┘
                                 │                       │
                                 │   NIXL KV Transfer    │
                                 │   (LIBFABRIC or UCX)  │
                                 └───────────────────────┘
```

## Quick Start

### LIBFABRIC (AWS EFA)

```bash
# Build
cd docker/libfabric
./build.sh

# Deploy
kubectl apply -f kubernetes/common/configmap.yaml
kubectl apply -f kubernetes/libfabric/deployment.yaml

# Test
./scripts/test-inference.sh trtllm-libfabric
```

### UCX (Standard)

```bash
# Deploy (uses pre-built image)
kubectl apply -f kubernetes/common/configmap.yaml
kubectl apply -f kubernetes/ucx/deployment.yaml

# Test
./scripts/test-inference.sh trtllm-ucx
```

## Repository Structure

```
dynamo-vault/
├── docker/
│   ├── libfabric/           # LIBFABRIC backend (AWS EFA)
│   │   ├── Dockerfile
│   │   ├── patch_nixl_connect.py
│   │   └── build.sh
│   ├── ucx/                 # UCX backend (standard)
│   │   ├── Dockerfile
│   │   └── build.sh
│   └── base/                # Base image reference
│       └── README.md
├── kubernetes/
│   ├── common/              # Shared configurations
│   │   └── configmap.yaml
│   ├── libfabric/           # LIBFABRIC deployments
│   │   └── deployment.yaml
│   └── ucx/                 # UCX deployments
│       └── deployment.yaml
├── scripts/
│   ├── build-all.sh         # Build all images
│   ├── deploy.sh            # Deploy to cluster
│   ├── test-inference.sh    # Test inference
│   └── cleanup.sh           # Clean up
├── docs/
│   ├── LIBFABRIC.md         # LIBFABRIC-specific docs
│   ├── UCX.md               # UCX-specific docs
│   ├── TROUBLESHOOTING.md   # Common issues
│   └── AWS_SETUP.md         # AWS EKS setup guide
├── examples/
│   ├── inference-test.py    # Python inference client
│   └── benchmark.py         # Performance benchmark
└── github-issues/           # Upstream issue templates
    ├── DYNAMO_ISSUE.md
    ├── DYNAMO_PR.md
    ├── TRTLLM_ISSUE.md
    └── SUMMARY.md
```

## Supported Configurations

| Configuration | Backend | Instance Types | Status |
|--------------|---------|----------------|--------|
| LIBFABRIC + EFA | LIBFABRIC | p5.48xlarge, p4d.24xlarge | Tested |
| UCX + TCP | UCX | Any | Tested |
| UCX + InfiniBand | UCX | p4d.24xlarge (400Gbps) | Tested |

## Requirements

### AWS Infrastructure
- EKS cluster with GPU nodes
- p5.48xlarge or p4d.24xlarge instances (for EFA)
- EFA device plugin installed
- NVIDIA GPU operator

### Software
- kubectl configured for cluster
- Docker with NVIDIA runtime
- AWS CLI with ECR access
- gh CLI (for GitHub operations)

## Pre-built Images

| Image | Backend | Tag |
|-------|---------|-----|
| LIBFABRIC | `public.ecr.aws/v9l4g5s4/dynamo-trtllm` | `h100-v28-full-libfabric` |
| UCX | `public.ecr.aws/v9l4g5s4/dynamo-trtllm` | `h100-v19-flashinfer-stub` |

## Environment Variables

### LIBFABRIC (EFA)
```bash
NIXL_BACKEND=LIBFABRIC
FI_PROVIDER=efa
FI_EFA_USE_DEVICE_RDMA=1
FI_HMEM_DISABLE_P2P=1
```

### UCX
```bash
NIXL_BACKEND=UCX
UCX_TLS=tcp,srd,cuda_copy,cuda_ipc,sm,self
UCX_IB_GPU_DIRECT_RDMA=yes
```

## The Three-Layer Problem (LIBFABRIC)

TRT-LLM rc4 (in Dynamo base) doesn't support LIBFABRIC. TRT-LLM rc5 adds support but has API incompatibilities. Our LIBFABRIC Dockerfile solves this by:

1. **C++ Backend**: Copies `libtensorrt_llm.so` from rc5 (LIBFABRIC support)
2. **Torch Ops**: Copies `libth_common.so` from rc5 (fused_qk_norm_rope 16-arg API)
3. **Python Bindings**: Copies `bindings.cpython-312.so` from rc5 (ABI compatibility)
4. **Dynamo Patch**: Patches nixl_connect to read NIXL_BACKEND env var

## Upstream Issues

We've documented the issues and proposed fixes for upstream:

- **NVIDIA/dynamo**: Feature request for NIXL_BACKEND env var support
- **NVIDIA/TensorRT-LLM**: Documentation request for AWS EFA deployment

See `github-issues/` for the full issue templates.

## Related Projects

- [NVIDIA TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- [NVIDIA Dynamo](https://github.com/NVIDIA/dynamo)
- [NVIDIA NIXL](https://github.com/NVIDIA/nixl)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- NVIDIA for TensorRT-LLM and Dynamo
- AWS for EFA support
- TRT-LLM PR #9225 for LIBFABRIC backend support
