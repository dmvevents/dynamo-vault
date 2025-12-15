# Troubleshooting Guide

## Common Issues

### 1. Segfault in KVCacheManager

**Symptom:**
```
Signal 11 (SIGSEGV) received in KVCacheManager::findBlocksInReuseTreeByBlockKey
```

**Cause:** ABI mismatch between C++ binaries. Mixing rc4 and rc5 binaries causes memory corruption.

**Solution:** Use the LIBFABRIC image which copies ALL rc5 binaries:
- libtensorrt_llm.so
- libtensorrt_llm_nixl_wrapper.so
- libth_common.so
- bindings.cpython-312-x86_64-linux-gnu.so

### 2. fused_qk_norm_rope Argument Mismatch

**Symptom:**
```
TypeError: fused_qk_norm_rope(): expected 16 arguments, got 15
```

**Cause:** rc5 changed the function signature from 15 to 16 arguments (added `is_qk_norm`).

**Solution:** The LIBFABRIC Dockerfile patches `qk_norm_attention.py` to add the missing argument.

### 3. NIXL Backend Not Detected

**Symptom:**
Logs show `Backend UCX was instantiated` instead of `Backend LIBFABRIC was instantiated`

**Cause:** Dynamo's nixl_connect ignores NIXL_BACKEND environment variable by default.

**Solution:** Use the patched image which includes `patch_nixl_connect.py`.

**Verification:**
```bash
kubectl logs <pod> | grep "NIXL Connect"
# Should show: NIXL Connect: Using backend(s): ['LIBFABRIC']
```

### 4. EFA Devices Not Found

**Symptom:**
```
No IB devices found
/dev/infiniband not mounted
```

**Cause:** EFA device plugin not configured or devices not mounted.

**Solution:**
1. Verify EFA device plugin is installed:
```bash
kubectl get pods -n kube-system | grep efa
```

2. Check node has EFA devices:
```bash
kubectl exec -it <pod> -- ibv_devices
```

3. Verify deployment has EFA resources:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: "1"
volumeMounts:
- name: dev-infiniband
  mountPath: /dev/infiniband
```

### 5. LIBFABRIC Plugin Missing

**Symptom:**
```
WARNING: LIBFABRIC plugin not found
```

**Cause:** NIXL LIBFABRIC plugin not present in base image.

**Solution:** Verify the plugin exists:
```bash
kubectl exec -it <pod> -- ls -la /opt/nvidia/nvda_nixl/lib/x86_64-linux-gnu/plugins/libplugin_LIBFABRIC.so
```

If missing, the base image doesn't support LIBFABRIC.

### 6. Memory Registration Errors

**Symptom:**
```
fi_mr_reg failed
Cannot allocate memory
```

**Cause:** Memory region cache issues with EFA.

**Solution:** Set these environment variables:
```yaml
- name: FI_MR_CACHE_MAX_COUNT
  value: "0"
- name: FI_MR_CACHE_MONITOR
  value: "disabled"
```

### 7. Fork Safety Errors

**Symptom:**
```
rdma_get_request_for_pid failed
Fork detected but not safe
```

**Cause:** RDMA/EFA not configured for fork safety.

**Solution:** Set fork safety variables:
```yaml
- name: FI_EFA_FORK_SAFE
  value: "1"
- name: RDMAV_FORK_SAFE
  value: "1"
```

### 8. Side Channel Connection Failed

**Symptom:**
```
NIXL side channel connection timed out
Cannot connect to peer
```

**Cause:** Pods can't reach each other's NIXL side channel.

**Solution:**
1. Ensure NIXL_SIDE_CHANNEL_HOST uses Pod IP:
```yaml
- name: NIXL_SIDE_CHANNEL_HOST
  valueFrom:
    fieldRef:
      fieldPath: status.podIP
```

2. Verify port 5600 is not blocked by network policies.

### 9. GPU Memory OOM

**Symptom:**
```
CUDA out of memory
```

**Cause:** KV cache fraction too high.

**Solution:** Reduce `free_gpu_memory_fraction` in ConfigMap:
```yaml
kv_cache_config:
  free_gpu_memory_fraction: 0.3  # Default is 0.5
```

## Debugging Commands

### Check Pod Status
```bash
kubectl get pods -l app.kubernetes.io/instance=trtllm-libfabric
kubectl describe pod <pod-name>
```

### View Logs
```bash
# Frontend
kubectl logs -l app.kubernetes.io/component=frontend

# Prefill worker
kubectl logs -l app.kubernetes.io/component=prefill

# Decode worker
kubectl logs -l app.kubernetes.io/component=decode
```

### Interactive Shell
```bash
kubectl exec -it <pod> -- /bin/bash

# Check NIXL configuration
env | grep NIXL
env | grep FI_

# Verify binaries
strings /opt/dynamo/venv/lib/python3.12/site-packages/tensorrt_llm/libs/libth_common.so | grep fused_qk_norm_rope
```

### Test Inference
```bash
kubectl port-forward svc/trtllm-libfabric-frontend 8000:8000 &
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-0.6B", "prompt": "Hello", "max_tokens": 10}'
```
