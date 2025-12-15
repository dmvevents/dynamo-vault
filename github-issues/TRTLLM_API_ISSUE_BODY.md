### Summary
The `fused_qk_norm_rope` function signature changed between rc4 and rc5 from 15 to 16 arguments (adding `is_qk_norm` parameter), breaking API compatibility for downstream consumers like NVIDIA Dynamo.

### Problem
When using TensorRT-LLM rc5 binaries with rc4 Python code (common when updating incrementally), the following error occurs:

```
TypeError: fused_qk_norm_rope(): expected 16 arguments, got 15
```

This happens because:
- rc4: `fused_qk_norm_rope(q, k, cos, sin, interleaved, q_norm_weight, k_norm_weight, q_norm_bias, k_norm_bias, eps, position_ids, factor, low, high, attention_factor)`
- rc5: `fused_qk_norm_rope(q, k, cos, sin, interleaved, q_norm_weight, k_norm_weight, q_norm_bias, k_norm_bias, eps, position_ids, factor, low, high, attention_factor, is_qk_norm)`

### Impact
- NVIDIA Dynamo's base image uses rc4 TensorRT-LLM
- Users wanting LIBFABRIC support (added in rc5) cannot simply replace binaries
- Must also patch Python code to add the missing `is_qk_norm` argument

### Suggested Solutions

1. **Default Parameter**: Add `is_qk_norm: bool = True` as a default parameter for backward compatibility

2. **Deprecation Warning**: Add a deprecation path where the 15-arg signature still works but warns

3. **Version Check**: Document clearly which binary/Python combinations are compatible

### Workaround
We're currently patching `qk_norm_attention.py` at container build time:

```python
# Add to __init__ signature
is_qk_norm: bool = True,

# Add to __init__ body
self.is_qk_norm = is_qk_norm

# Update fused_qk_norm_rope call
attention_factor, self.is_qk_norm)  # Add is_qk_norm argument
```

### Environment
- TensorRT-LLM: 1.2.0rc5 binaries with rc4 Python
- Issue introduced in: rc5
- Platform: AWS EKS with H100

### Related
- This issue is related to LIBFABRIC support (PR #9225)
- Documentation issue: #10014
