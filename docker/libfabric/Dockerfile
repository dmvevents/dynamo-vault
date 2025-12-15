# Dockerfile for TRT-LLM + Dynamo with LIBFABRIC Backend Support
#
# This Dockerfile creates an image that enables LIBFABRIC backend for NIXL
# KV cache transfer in TensorRT-LLM disaggregated inference on AWS EFA.
#
# PROBLEM SOLVED:
# - TRT-LLM rc4 (in Dynamo base image) only supports UCX backend
# - TRT-LLM rc5 adds LIBFABRIC support but has API incompatibilities
# - This image surgically replaces specific rc5 binaries and patches Python code
#
# STRATEGY:
# 1. Start from rc4 base (Dynamo + CUDA 13 + FlashInfer stub)
# 2. Copy ALL rc5 C++ binaries that interact:
#    - libtensorrt_llm.so (NIXL backend + KV cache manager)
#    - libtensorrt_llm_nixl_wrapper.so (NIXL wrapper)
#    - libth_common.so (torch ops - fused_qk_norm_rope)
#    - bindings.cpython-312-x86_64-linux-gnu.so (Python bindings to C++)
# 3. Patch rc4 Python code to match rc5 API
# 4. Patch Dynamo nixl_connect to read NIXL_BACKEND env var
#
# Build:
#   docker build -t dynamo-trtllm:libfabric .
#
# Required context files:
#   - patch_nixl_connect.py (in same directory as Dockerfile)

FROM nvcr.io/nvidia/tensorrt-llm/release:1.2.0rc5 AS trtllm_rc5

FROM public.ecr.aws/v9l4g5s4/dynamo-trtllm:h100-v19-flashinfer-stub AS base

USER root

# Step 1: Copy ALL rc5 C++ binaries that need to be ABI-compatible
# These files all interact with each other and must be from the same version
COPY --from=trtllm_rc5 /usr/local/lib/python3.12/dist-packages/tensorrt_llm/libs/libtensorrt_llm.so /tmp/rc5/libtensorrt_llm.so
COPY --from=trtllm_rc5 /usr/local/lib/python3.12/dist-packages/tensorrt_llm/libs/libtensorrt_llm_nixl_wrapper.so /tmp/rc5/libtensorrt_llm_nixl_wrapper.so
COPY --from=trtllm_rc5 /usr/local/lib/python3.12/dist-packages/tensorrt_llm/libs/libth_common.so /tmp/rc5/libth_common.so
COPY --from=trtllm_rc5 /usr/local/lib/python3.12/dist-packages/tensorrt_llm/bindings.cpython-312-x86_64-linux-gnu.so /tmp/rc5/bindings.cpython-312-x86_64-linux-gnu.so

RUN SITE_PACKAGES=/opt/dynamo/venv/lib/python3.12/site-packages && \
    echo "=== Replacing rc5 C++ binaries for LIBFABRIC support + ABI compatibility ===" && \
    \
    # Backup rc4 binaries
    cp "$SITE_PACKAGES/tensorrt_llm/libs/libtensorrt_llm.so" \
       "$SITE_PACKAGES/tensorrt_llm/libs/libtensorrt_llm.so.rc4.bak" && \
    cp "$SITE_PACKAGES/tensorrt_llm/libs/libtensorrt_llm_nixl_wrapper.so" \
       "$SITE_PACKAGES/tensorrt_llm/libs/libtensorrt_llm_nixl_wrapper.so.rc4.bak" && \
    cp "$SITE_PACKAGES/tensorrt_llm/libs/libth_common.so" \
       "$SITE_PACKAGES/tensorrt_llm/libs/libth_common.so.rc4.bak" && \
    cp "$SITE_PACKAGES/tensorrt_llm/bindings.cpython-312-x86_64-linux-gnu.so" \
       "$SITE_PACKAGES/tensorrt_llm/bindings.cpython-312-x86_64-linux-gnu.so.rc4.bak" && \
    \
    # Install rc5 binaries
    cp /tmp/rc5/libtensorrt_llm.so "$SITE_PACKAGES/tensorrt_llm/libs/libtensorrt_llm.so" && \
    cp /tmp/rc5/libtensorrt_llm_nixl_wrapper.so "$SITE_PACKAGES/tensorrt_llm/libs/libtensorrt_llm_nixl_wrapper.so" && \
    cp /tmp/rc5/libth_common.so "$SITE_PACKAGES/tensorrt_llm/libs/libth_common.so" && \
    cp /tmp/rc5/bindings.cpython-312-x86_64-linux-gnu.so "$SITE_PACKAGES/tensorrt_llm/bindings.cpython-312-x86_64-linux-gnu.so" && \
    \
    echo "=== rc5 binaries installed ===" && \
    echo "Verifying libth_common.so has 16-arg fused_qk_norm_rope:" && \
    strings "$SITE_PACKAGES/tensorrt_llm/libs/libth_common.so" | grep "fused_qk_norm_rope" | head -2 && \
    \
    echo "" && echo "=== File sizes ===" && \
    ls -la "$SITE_PACKAGES/tensorrt_llm/libs/"*.so | head -10 && \
    ls -la "$SITE_PACKAGES/tensorrt_llm/bindings"*.so && \
    \
    rm -rf /tmp/rc5

# Step 2: Patch qk_norm_attention.py to add is_qk_norm argument
# rc5 changed fused_qk_norm_rope from 15 to 16 arguments
RUN SITE_PACKAGES=/opt/dynamo/venv/lib/python3.12/site-packages && \
    QK_NORM_FILE="$SITE_PACKAGES/tensorrt_llm/_torch/modules/qk_norm_attention.py" && \
    \
    echo "=== Patching qk_norm_attention.py ===" && \
    \
    # Backup original
    cp "$QK_NORM_FILE" "${QK_NORM_FILE}.rc4.bak" && \
    \
    # PATCH 1: Add is_qk_norm parameter to __init__ signature
    sed -i '/attn_output_gate: Optional\[bool\] = None,$/a\        is_qk_norm: bool = True,' "$QK_NORM_FILE" && \
    \
    # PATCH 2: Add self.is_qk_norm = is_qk_norm assignment
    sed -i '/self.skip_rope = skip_rope$/a\        self.is_qk_norm = is_qk_norm' "$QK_NORM_FILE" && \
    \
    # PATCH 3: Update the fused_qk_norm_rope call to include self.is_qk_norm
    sed -i 's/position_ids\.view(-1), factor, low, high, attention_factor)/position_ids.view(-1), factor, low, high, attention_factor, self.is_qk_norm)/' "$QK_NORM_FILE" && \
    \
    echo "=== is_qk_norm occurrences ===" && \
    grep -n "is_qk_norm" "$QK_NORM_FILE"

# Step 3: Verify the patch
RUN SITE_PACKAGES=/opt/dynamo/venv/lib/python3.12/site-packages && \
    QK_NORM_FILE="$SITE_PACKAGES/tensorrt_llm/_torch/modules/qk_norm_attention.py" && \
    \
    echo "=== Verifying patch ===" && \
    \
    if grep -A1 "attn_output_gate: Optional\[bool\] = None," "$QK_NORM_FILE" | grep -q "is_qk_norm: bool = True,"; then \
        echo "CHECK 1 PASSED: is_qk_norm in __init__ signature" ; \
    else \
        echo "CHECK 1 FAILED" && exit 1 ; \
    fi && \
    \
    if grep -q "self.is_qk_norm = is_qk_norm" "$QK_NORM_FILE"; then \
        echo "CHECK 2 PASSED: self.is_qk_norm assignment" ; \
    else \
        echo "CHECK 2 FAILED" && exit 1 ; \
    fi && \
    \
    if grep -q "attention_factor, self.is_qk_norm)" "$QK_NORM_FILE"; then \
        echo "CHECK 3 PASSED: fused_qk_norm_rope call updated" ; \
    else \
        echo "CHECK 3 FAILED" && exit 1 ; \
    fi && \
    \
    echo "=== ALL PATCHES VERIFIED ==="

# Step 4: Verify Python syntax
RUN SITE_PACKAGES=/opt/dynamo/venv/lib/python3.12/site-packages && \
    QK_NORM_FILE="$SITE_PACKAGES/tensorrt_llm/_torch/modules/qk_norm_attention.py" && \
    source /opt/dynamo/venv/bin/activate && \
    python3 -m py_compile "$QK_NORM_FILE" && \
    echo "=== SYNTAX VALID ===" || (echo "=== SYNTAX ERROR ===" && exit 1)

# Step 5: Patch Dynamo nixl_connect to read NIXL_BACKEND env var
COPY patch_nixl_connect.py /tmp/patch_nixl_connect.py

RUN NIXL_CONNECT_FILE=/opt/dynamo/venv/lib/python3.12/site-packages/dynamo/nixl_connect/__init__.py && \
    \
    echo "=== Patching Dynamo nixl_connect ===" && \
    \
    cp "$NIXL_CONNECT_FILE" "${NIXL_CONNECT_FILE}.original.bak" && \
    \
    if ! grep -q "self._nixl = nixl_api.nixl_agent(self._worker_id)$" "$NIXL_CONNECT_FILE"; then \
        echo "ERROR: Could not find target code to patch" && exit 1 ; \
    fi && \
    \
    python3 /tmp/patch_nixl_connect.py "$NIXL_CONNECT_FILE" && \
    \
    if grep -q "LIBFABRIC PATCH" "$NIXL_CONNECT_FILE"; then \
        echo "=== NIXL_CONNECT PATCH VERIFIED ===" ; \
    else \
        echo "=== ERROR: Patch not applied ===" && exit 1 ; \
    fi && \
    \
    rm /tmp/patch_nixl_connect.py

# Verify nixl_connect Python syntax
RUN NIXL_CONNECT_FILE=/opt/dynamo/venv/lib/python3.12/site-packages/dynamo/nixl_connect/__init__.py && \
    source /opt/dynamo/venv/bin/activate && \
    python3 -m py_compile "$NIXL_CONNECT_FILE" && \
    echo "=== NIXL_CONNECT SYNTAX VALID ===" || (echo "=== SYNTAX ERROR ===" && exit 1)

# Update library cache
RUN ldconfig

# Verify NIXL LIBFABRIC plugin
RUN ls -la /opt/nvidia/nvda_nixl/lib/x86_64-linux-gnu/plugins/libplugin_LIBFABRIC.so && \
    echo "=== LIBFABRIC plugin verified ===" || echo "=== WARNING: LIBFABRIC plugin not found ==="

# Set default environment for LIBFABRIC
ENV NIXL_BACKEND=LIBFABRIC
ENV FI_PROVIDER=efa
ENV FI_EFA_USE_DEVICE_RDMA=1

# Labels
LABEL version="libfabric"
LABEL description="TRT-LLM + Dynamo with full LIBFABRIC backend support"
LABEL fix="Copies rc5 binaries (libtensorrt_llm.so, libth_common.so, bindings.cpython-312.so) for ABI compatibility"

USER dynamo

CMD ["/bin/bash"]
