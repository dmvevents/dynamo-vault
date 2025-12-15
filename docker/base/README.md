# Base Images

This directory documents the base images used for building the LIBFABRIC and UCX variants.

## Base Image

**Image**: `public.ecr.aws/v9l4g5s4/dynamo-trtllm:h100-v19-flashinfer-stub`

This image contains:
- NVIDIA Dynamo framework
- TensorRT-LLM 1.2.0rc4
- FlashInfer (stub)
- CUDA 13
- Python 3.12

## Source Images

### TensorRT-LLM rc5
**Image**: `nvcr.io/nvidia/tensorrt-llm/release:1.2.0rc5`

Used for extracting LIBFABRIC-compatible binaries:
- `libtensorrt_llm.so`
- `libtensorrt_llm_nixl_wrapper.so`
- `libth_common.so`
- `bindings.cpython-312-x86_64-linux-gnu.so`

## Why Multi-Stage Build?

TRT-LLM rc4 (in Dynamo base) only supports UCX backend. TRT-LLM rc5 added LIBFABRIC support but has API incompatibilities (fused_qk_norm_rope changed from 15 to 16 arguments).

Our LIBFABRIC Dockerfile:
1. Starts from rc4 base (Dynamo compatibility)
2. Extracts rc5 C++ binaries (LIBFABRIC + ABI compatibility)
3. Patches Python code to match rc5 API
4. Patches Dynamo nixl_connect to read NIXL_BACKEND env var
