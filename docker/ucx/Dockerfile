# Dockerfile for TRT-LLM + Dynamo with UCX Backend (Standard)
#
# This Dockerfile uses the standard Dynamo base image with UCX backend.
# UCX is the default backend and works on any hardware (TCP, InfiniBand, RoCE).
#
# Use Cases:
# - On-premises deployments without EFA
# - AWS instances without EFA support
# - Development and testing
#
# Build:
#   docker build -t dynamo-trtllm:ucx .

FROM public.ecr.aws/v9l4g5s4/dynamo-trtllm:h100-v19-flashinfer-stub

USER root

# Set default environment for UCX
ENV NIXL_BACKEND=UCX
ENV UCX_TLS=tcp,srd,cuda_copy,cuda_ipc,sm,self
ENV UCX_NET_DEVICES=all
ENV UCX_IB_GPU_DIRECT_RDMA=yes

# Labels
LABEL version="ucx"
LABEL description="TRT-LLM + Dynamo with UCX backend (standard)"

USER dynamo

CMD ["/bin/bash"]
