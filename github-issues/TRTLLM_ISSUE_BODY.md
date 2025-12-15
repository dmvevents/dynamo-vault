### Summary
Request for documentation on deploying TensorRT-LLM disaggregated inference with LIBFABRIC backend on AWS EFA. While PR #9225 added LIBFABRIC support, there's no guide on how to configure it properly with Dynamo on AWS.

### Background
TensorRT-LLM v1.2.0rc5 added LIBFABRIC backend support for NIXL KV cache transfer (PR #9225). However, deploying this on AWS with EFA requires:

1. Understanding which binaries support LIBFABRIC (`kSUPPORTED_BACKENDS` in `transferAgent.cpp`)
2. Proper environment variables for LIBFABRIC/EFA
3. Integration with NVIDIA Dynamo for disaggregated inference
4. Kubernetes configuration for EFA devices

### Current Challenges

When trying to use LIBFABRIC on AWS EFA, we encountered:

1. **Version Compatibility**: Dynamo's base image uses rc4 which doesn't have LIBFABRIC support
2. **API Changes**: rc5 changed `fused_qk_norm_rope` from 15 to 16 arguments, breaking compatibility
3. **ABI Issues**: Mixing rc4 and rc5 binaries causes segfaults
4. **Dynamo Integration**: Dynamo's `nixl_connect` doesn't read `NIXL_BACKEND` env var

### Requested Documentation

1. **Supported Configurations**
   - Which TRT-LLM versions support LIBFABRIC?
   - What are the binary compatibility requirements?

2. **Environment Variables**
   - `NIXL_BACKEND=LIBFABRIC`
   - `FI_PROVIDER=efa`
   - `FI_EFA_USE_DEVICE_RDMA=1`
   - Required library paths

3. **Kubernetes Deployment**
   - EFA device mounting (`/dev/infiniband`)
   - Required capabilities (`IPC_LOCK`, `SYS_RESOURCE`)
   - Hugepages configuration

4. **Integration with Dynamo**
   - How to configure NIXL backend in disaggregated mode
   - NIXL side channel configuration for cross-node

### Environment
- TensorRT-LLM: 1.2.0rc5
- Platform: AWS EKS with p5.48xlarge (H100 + EFA)
- Dynamo: Latest

### Additional Context
We've successfully deployed TRT-LLM with LIBFABRIC on AWS EFA by:
1. Replacing rc5 binaries into Dynamo base image
2. Patching Python code for API compatibility
3. Patching Dynamo nixl_connect to read NIXL_BACKEND

A documentation guide would help other users avoid these challenges.

### Reference Implementation
We've documented our working solution:
https://github.com/dmvevents/dynamo-vault
