# Pull Request: NVIDIA/dynamo

## Title
feat(nixl_connect): Add NIXL_BACKEND environment variable support for backend selection

---

## Description

### Summary
This PR adds support for the `NIXL_BACKEND` environment variable in the `nixl_connect` module, allowing users to select alternative NIXL backends like LIBFABRIC for AWS EFA deployments.

### Motivation
TensorRT-LLM rc5 added LIBFABRIC backend support for NIXL (PR NVIDIA/TensorRT-LLM#9225), but Dynamo's `nixl_connect` module always creates agents with the default UCX backend. This prevents users from leveraging AWS EFA's high-bandwidth networking for KV cache transfer in disaggregated inference.

### Changes

**File: `dynamo/nixl_connect/__init__.py`**

```diff
- self._nixl = nixl_api.nixl_agent(self._worker_id)
+ # Support NIXL_BACKEND environment variable for backend selection
+ # Default to UCX for backward compatibility
+ import os
+ nixl_backend = os.environ.get('NIXL_BACKEND', 'UCX')
+ supported_backends = ['UCX', 'LIBFABRIC']
+ if nixl_backend not in supported_backends:
+     logger.warning(f"Unknown NIXL backend '{nixl_backend}', falling back to UCX")
+     nixl_backend = 'UCX'
+
+ backends = [nixl_backend]
+ logger.info(f"NIXL Connect: Using backend(s): {backends}")
+ nixl_config = nixl_api.nixl_agent_config(backends=backends)
+ self._nixl = nixl_api.nixl_agent(self._worker_id, nixl_config)
```

### Usage

To use LIBFABRIC backend on AWS EFA:
```bash
export NIXL_BACKEND=LIBFABRIC
export FI_PROVIDER=efa
```

Or in Kubernetes:
```yaml
envs:
  - name: NIXL_BACKEND
    value: "LIBFABRIC"
```

### Testing

Tested on AWS EKS with p5.48xlarge nodes (H100 + EFA):
1. Set `NIXL_BACKEND=LIBFABRIC`
2. Deploy TRT-LLM disaggregated inference
3. Verified logs show: `Backend LIBFABRIC was instantiated`
4. Inference works correctly

### Backward Compatibility
- Default value is `UCX`, maintaining existing behavior
- Invalid backend values fall back to UCX with warning

### Related
- NVIDIA/TensorRT-LLM#9225 (LIBFABRIC backend support)

---

## PR Template

```markdown
## Summary
Add NIXL_BACKEND environment variable support to nixl_connect for backend selection.

## Test plan
- [x] Tested with NIXL_BACKEND=LIBFABRIC on AWS EFA
- [x] Tested default behavior (UCX) without env var
- [x] Tested invalid backend value falls back to UCX

## Checklist
- [x] Code follows project style guidelines
- [x] Backward compatible
- [x] Documentation updated (inline comments)
```
