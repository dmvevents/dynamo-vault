# NIXL LIBFABRIC Multi-Rail Deserialization Fix for AWS P5.48xlarge

## Problem Summary

When running TensorRT-LLM with NIXL LIBFABRIC backend on AWS P5.48xlarge instances (32 EFA devices, 8 H100 GPUs), the decode worker fails with:

```
Deserialization of tag dest_data_ep_5 failed
```

This occurs because NIXL 0.8.0's SerDes system has offset alignment issues when serializing multiple EFA endpoints.

## Root Cause

The issue is in NIXL's serialization/deserialization system (`serdes.cpp`) which uses offset-based parsing with binary length fields. When NIXL discovers all 32 EFA devices on P5.48xlarge and attempts to serialize multiple rail endpoints, the offsets become misaligned.

### Source Code Reference

**serdes.cpp** - Core serialization failure point:
```cpp
ssize_t nixlSerDes::getBufLen(const std::string &tag) const{
    if(workingStr.compare(des_offset, tag.size(), tag) != 0){
        NIXL_ERROR << "Deserialization of tag " << tag << " failed";
        return -1;
    }
    // ...
}
```

**libfabric_rail_manager.cpp** - Multi-rail serialization:
```cpp
void nixlLibfabricRailManager::serializeRailEndpoints(nixlSerDes &ser_des,
                                                     const std::string &key_prefix,
                                                     RailType rail_type) const {
    auto &rails = (rail_type == RailType::DATA) ? data_rails_ : control_rails_;
    ser_des.addStr(NUM_RAILS_TAG, std::to_string(rails.size()));
    for (size_t rail_id = 0; rail_id < rails.size(); ++rail_id) {
        std::string rail_key = key_prefix + std::to_string(rail_id);
        ser_des.addBuf(rail_key.c_str(), ep_name, ep_name_len);
    }
}
```

## Solution: Single EFA Device Workaround

The working workaround is to force libfabric to use only a single EFA device, avoiding the multi-rail serialization bug:

```yaml
envs:
  - name: FI_EFA_DEV_LIST
    value: "0"
  - name: NIXL_LIBFABRIC_NUM_RAILS
    value: "1"
```

## Test Results

| Configuration | EFA Devices | Result |
|--------------|-------------|--------|
| v56a (FI_EFA_DEV_LIST=0) | 1 | **SUCCESS** |
| v56b (vpc.amazonaws.com/efa: 4) | 4 | FAILED - `dest_data_ep_4` |
| v56c (FI_EFA_INTERFACE filter) | 1 filtered | FAILED - `dest_data_ep_4` |

## Files in This Gist

1. **Dockerfile.nixl-080** - Builds NIXL 0.8.0 with LIBFABRIC plugin
2. **trtllm-disagg-v56a-single-efa.yaml** - Working K8s deployment
3. **configmap-trtllm-config.yaml** - TRT-LLM worker configurations
4. **NIXL-SERDES-ANALYSIS.md** - Technical analysis of the bug

## Quick Start

1. Build the Docker image:
```bash
docker build -f Dockerfile.nixl-080 -t dynamo-trtllm:v55-nixl-080-libfabric .
docker push your-registry/dynamo-trtllm:v55-nixl-080-libfabric
```

2. Apply the ConfigMap:
```bash
kubectl apply -f configmap-trtllm-config.yaml
```

3. Deploy the working configuration:
```bash
kubectl apply -f trtllm-disagg-v56a-single-efa.yaml
```

4. Test:
```bash
kubectl port-forward svc/trtllm-v56a-single-efa-frontend 8000:8000
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-0.6B", "prompt": "The capital of France is", "max_tokens": 30}'
```

## Critical Environment Variables

```yaml
# Force single EFA device (CRITICAL WORKAROUND)
FI_EFA_DEV_LIST: "0"

# NIXL Configuration
NIXL_BACKEND: "LIBFABRIC"
TRTLLM_NIXL_KVCACHE_BACKEND: "LIBFABRIC"
NIXL_LIBFABRIC_NUM_RAILS: "1"
NIXL_SKIP_TOPOLOGY_CHECK: "1"
NIXL_CONTAINER_AWARE_TOPOLOGY: "1"

# Libfabric tuning
FI_PROVIDER: "efa"
FI_EFA_USE_DEVICE_RDMA: "0"
FI_EFA_ENABLE_SHM: "0"
FI_MR_CACHE_MAX_COUNT: "0"
FI_MR_CACHE_MONITOR: "disabled"
```

## Known Limitations

- Uses only 1 of 32 EFA devices (reduced bandwidth)
- Workaround until NIXL fixes multi-rail serialization
- May need adjustment for different instance types

## Related Issues

- NIXL GitHub: Multi-rail serialization offset bug in SerDes
- TensorRT-LLM: KV cache disaggregation with NIXL LIBFABRIC backend
