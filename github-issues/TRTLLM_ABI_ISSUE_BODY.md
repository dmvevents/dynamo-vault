### Summary
Mixing TensorRT-LLM rc4 and rc5 C++ binaries causes segmentation faults due to ABI incompatibility. Specifically, using rc5 `libtensorrt_llm.so` with rc4 `bindings.cpython-312-x86_64-linux-gnu.so` crashes in KVCacheManager.

### Problem
When attempting to use LIBFABRIC support (added in rc5) with Dynamo's rc4-based image, users naturally try to replace only the core library. This causes:

```
Signal 11 (SIGSEGV) received
Backtrace:
  KVCacheManager::findBlocksInReuseTreeByBlockKey
  KVCacheManager::findBlocks
  ...
```

### Root Cause
The Python bindings (`bindings.cpython-312-x86_64-linux-gnu.so`) are compiled against specific C++ class layouts. When `libtensorrt_llm.so` changes internal structures between rc4 and rc5, the bindings access incorrect memory offsets, causing corruption.

### Files That Must Be Updated Together
Through trial and error, we discovered these files must ALL be from the same version:

1. `libtensorrt_llm.so` - Core library
2. `libtensorrt_llm_nixl_wrapper.so` - NIXL wrapper
3. `libth_common.so` - Torch operations
4. `bindings.cpython-312-x86_64-linux-gnu.so` - Python bindings

Replacing only 1-3 without #4 causes the segfault.

### Impact
- Users cannot incrementally adopt new features (like LIBFABRIC)
- The segfault provides no indication of the root cause
- Debugging requires understanding internal ABI details

### Suggested Solutions

1. **Documentation**: Document which binaries must be updated together

2. **Version Check**: Add runtime version checking between bindings and libraries
   ```python
   # In bindings initialization
   if bindings_version != libtensorrt_llm_version:
       raise RuntimeError(f"Version mismatch: bindings={bindings_version}, lib={libtensorrt_llm_version}")
   ```

3. **ABI Stability**: Consider ABI stability guarantees for patch releases

### Environment
- TensorRT-LLM: 1.2.0rc4 bindings + 1.2.0rc5 libraries
- Crash location: `KVCacheManager::findBlocksInReuseTreeByBlockKey`
- Platform: AWS EKS with H100

### Reproduction
1. Start with Dynamo base image (uses TRT-LLM rc4)
2. Replace only `libtensorrt_llm.so` from rc5
3. Run inference
4. Observe segfault in KVCacheManager

### Related Issues
- #10014 - Documentation request for LIBFABRIC deployment
- #10015 - fused_qk_norm_rope API breaking change
