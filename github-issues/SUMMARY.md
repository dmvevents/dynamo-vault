# GitHub Issues and PRs Summary

## Overview

This document summarizes the GitHub issues and pull requests for upstreaming our LIBFABRIC/EFA solution.

---

## Issues Created

### 1. NVIDIA/TensorRT-LLM - Documentation Request
**URL**: https://github.com/NVIDIA/TensorRT-LLM/issues/10014
**Title**: [Documentation] AWS EFA/LIBFABRIC deployment guide for disaggregated inference
**Status**: CREATED

### 2. NVIDIA/TensorRT-LLM - API Compatibility Bug
**URL**: https://github.com/NVIDIA/TensorRT-LLM/issues/10015
**Title**: [Bug] fused_qk_norm_rope API breaking change between rc4 and rc5 (15 vs 16 arguments)
**Status**: CREATED

---

## Issues Pending (Repo Not Public)

### 1. NVIDIA/dynamo - Feature Request
**File**: `DYNAMO_ISSUE.md`

**Title**: [Feature Request] nixl_connect should support NIXL_BACKEND environment variable for backend selection

**Summary**: Dynamo's nixl_connect always uses UCX backend, ignoring NIXL_BACKEND env var. This prevents using LIBFABRIC on AWS EFA.

**Action**: Feature request for environment variable support
**Status**: PENDING - NVIDIA/dynamo repo not publicly available

---

## Pull Request to Create

### 1. NVIDIA/dynamo - Feature PR
**File**: `DYNAMO_PR.md`

**Title**: feat(nixl_connect): Add NIXL_BACKEND environment variable support for backend selection

**Summary**: Adds support for NIXL_BACKEND environment variable in nixl_connect module.

**Changes**:
```python
# Before
self._nixl = nixl_api.nixl_agent(self._worker_id)

# After
nixl_backend = os.environ.get('NIXL_BACKEND', 'UCX')
nixl_config = nixl_api.nixl_agent_config(backends=[nixl_backend])
self._nixl = nixl_api.nixl_agent(self._worker_id, nixl_config)
```

---

## Commands to Create Issues

```bash
# 1. Dynamo Feature Request
cd /home/ubuntu/trtllm-libfabric-solution/github-issues
gh issue create \
  --repo NVIDIA/dynamo \
  --title "[Feature Request] nixl_connect should support NIXL_BACKEND environment variable" \
  --body-file DYNAMO_ISSUE.md

# 2. TensorRT-LLM Documentation Request
gh issue create \
  --repo NVIDIA/TensorRT-LLM \
  --title "[Documentation] AWS EFA/LIBFABRIC deployment guide for disaggregated inference" \
  --body-file TRTLLM_ISSUE.md
```

---

## Steps to Create PR for Dynamo

```bash
# 1. Fork NVIDIA/dynamo to your account

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/dynamo.git
cd dynamo

# 3. Create feature branch
git checkout -b feat/nixl-backend-env-var

# 4. Edit the file
# dynamo/nixl_connect/__init__.py
# Apply the changes from DYNAMO_PR.md

# 5. Commit
git add .
git commit -m "feat(nixl_connect): Add NIXL_BACKEND environment variable support"

# 6. Push
git push origin feat/nixl-backend-env-var

# 7. Create PR via GitHub UI or gh CLI
gh pr create \
  --repo NVIDIA/dynamo \
  --title "feat(nixl_connect): Add NIXL_BACKEND environment variable support" \
  --body-file DYNAMO_PR.md
```

---

## Related Links

- [TensorRT-LLM PR #9225](https://github.com/NVIDIA/TensorRT-LLM/pull/9225) - Original LIBFABRIC support
- [NVIDIA Dynamo](https://github.com/NVIDIA/dynamo)
- [NVIDIA NIXL](https://github.com/NVIDIA/nixl)
- [AWS EFA Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)

---

## Date: December 15, 2025
