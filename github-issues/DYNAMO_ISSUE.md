# GitHub Issue: NVIDIA/dynamo

## Title
[Feature Request] nixl_connect should support NIXL_BACKEND environment variable for backend selection

---

## Description

### Summary
The `nixl_connect` module in Dynamo always creates NIXL agents with the default backend (UCX), ignoring the `NIXL_BACKEND` environment variable. This prevents users from selecting alternative backends like LIBFABRIC for AWS EFA deployments.

### Current Behavior
In `dynamo/nixl_connect/__init__.py`, the NIXL agent is created with default configuration:

```python
self._nixl = nixl_api.nixl_agent(self._worker_id)
```

This always uses UCX backend regardless of the `NIXL_BACKEND` environment variable.

### Expected Behavior
The code should read the `NIXL_BACKEND` environment variable and configure the agent accordingly:

```python
import os
nixl_backend = os.environ.get('NIXL_BACKEND', 'UCX')
backends = [nixl_backend]
nixl_config = nixl_api.nixl_agent_config(backends=backends)
self._nixl = nixl_api.nixl_agent(self._worker_id, nixl_config)
```

### Use Case
On AWS with EFA (Elastic Fabric Adapter), users want to use LIBFABRIC backend instead of UCX for better performance with the EFA provider. TensorRT-LLM rc5 added LIBFABRIC support (PR #9225), but Dynamo's nixl_connect doesn't allow selecting it.

### Environment
- TensorRT-LLM version: 1.2.0rc5
- Dynamo version: (from base image)
- Platform: AWS EKS with p5.48xlarge (H100 + EFA)

### Workaround
Currently requires patching the source code at container build time:

```python
# Patch to nixl_connect/__init__.py
import os as _nixl_os
_nixl_backend = _nixl_os.environ.get('NIXL_BACKEND', 'UCX')
_backends = [_nixl_backend] if _nixl_backend != 'UCX' else ['UCX']
logger.info(f"NIXL Connect: Using backend(s): {_backends}")
_nixl_config = nixl_api.nixl_agent_config(backends=_backends)
self._nixl = nixl_api.nixl_agent(self._worker_id, _nixl_config)
```

### Suggested Fix
Add environment variable support in `nixl_connect/__init__.py`:

```python
def __init__(self, ...):
    ...
    # Support NIXL_BACKEND environment variable for backend selection
    nixl_backend = os.environ.get('NIXL_BACKEND', 'UCX')
    supported_backends = ['UCX', 'LIBFABRIC']
    if nixl_backend not in supported_backends:
        logger.warning(f"Unknown NIXL backend '{nixl_backend}', falling back to UCX")
        nixl_backend = 'UCX'

    backends = [nixl_backend]
    logger.info(f"NIXL Connect: Using backend(s): {backends}")
    nixl_config = nixl_api.nixl_agent_config(backends=backends)
    self._nixl = nixl_api.nixl_agent(self._worker_id, nixl_config)
```

### Labels
- enhancement
- aws
- efa
- nixl

---

## To Create This Issue

```bash
gh issue create \
  --repo NVIDIA/dynamo \
  --title "[Feature Request] nixl_connect should support NIXL_BACKEND environment variable for backend selection" \
  --body-file DYNAMO_ISSUE.md \
  --label "enhancement"
```
