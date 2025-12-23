# NIXL SerDes Multi-Rail Deserialization Bug Analysis

## Overview

This document analyzes the root cause of the `Deserialization of tag dest_data_ep_X failed` error that occurs when running TensorRT-LLM with NIXL LIBFABRIC backend on AWS P5.48xlarge instances.

## Error Symptoms

```
[nixl_log.h:30] Deserialization of tag dest_data_ep_5 failed
```

The error occurs during KV cache transfer between prefill and decode workers when using disaggregated inference.

## Technical Root Cause

### 1. SerDes Architecture

NIXL uses a custom serialization/deserialization system (`nixlSerDes` class) with the following characteristics:

- **Header**: `nixlSerDes|` (11 bytes)
- **Tag-Length-Value format**: Each field has a tag, binary length (ssize_t = 8 bytes), and value
- **Delimiter**: `|` character between fields
- **Offset-based parsing**: Uses `des_offset` to track position during deserialization

### 2. Serialization Format

```
nixlSerDes|<tag1><len:8bytes><value>|<tag2><len:8bytes><value>|...
```

Example for rail endpoints:
```
nixlSerDes|num_rails<len>2|dest_data_ep_0<len><ep_name_0>|dest_data_ep_1<len><ep_name_1>|...
```

### 3. The Bug

When serializing multiple EFA endpoints, offset calculations can become misaligned due to:

1. **Variable endpoint name lengths**: EFA endpoint names can vary in length
2. **Binary length encoding**: The ssize_t (8-byte) length field is stored as raw bytes
3. **Accumulated offset drift**: Small misalignments accumulate across multiple endpoints

### 4. Code Analysis

**serdes.cpp - Deserialization failure point** (line 87-102):
```cpp
ssize_t nixlSerDes::getBufLen(const std::string &tag) const{
    if(workingStr.compare(des_offset, tag.size(), tag) != 0){
        NIXL_ERROR << "Deserialization of tag " << tag << " failed";
        return -1;
    }
    ssize_t len;
    _stringToBytes(&len, workingStr.substr(des_offset + tag.size(), sizeof(ssize_t)), sizeof(ssize_t));
    return len;
}
```

The `workingStr.compare(des_offset, tag.size(), tag)` check fails when `des_offset` points to the wrong position in the serialized string.

**libfabric_rail_manager.cpp - Serialization** (line 803-820):
```cpp
void nixlLibfabricRailManager::serializeRailEndpoints(nixlSerDes &ser_des,
                                                     const std::string &key_prefix,
                                                     RailType rail_type) const {
    auto &rails = (rail_type == RailType::DATA) ? data_rails_ : control_rails_;
    ser_des.addStr(NUM_RAILS_TAG, std::to_string(rails.size()));

    for (size_t rail_id = 0; rail_id < rails.size(); ++rail_id) {
        std::string rail_key = key_prefix + std::to_string(rail_id);
        // ep_name is padded to LF_EP_NAME_MAX_LEN (56 bytes)
        ser_des.addBuf(rail_key.c_str(), ep_name, ep_name_len);
    }
}
```

Each rail endpoint adds:
- Tag: `dest_data_ep_N` (variable length: 14-15 bytes for N=0-9, 16 bytes for N=10+)
- Length: 8 bytes (ssize_t)
- Value: 56 bytes (LF_EP_NAME_MAX_LEN)
- Delimiter: 1 byte (`|`)

### 5. Why Single Rail Works

With `FI_EFA_DEV_LIST=0` forcing a single EFA device:
- Only one rail is discovered and serialized
- No accumulated offset drift
- Deserialization succeeds

With multiple rails (4 or 32 devices):
- Multiple endpoints are serialized
- Offset misalignment accumulates
- Deserialization fails at some endpoint (typically ep_4 or ep_5)

## Failed Workaround Attempts

| Approach | Environment Variable | Result |
|----------|---------------------|--------|
| K8s EFA limits | `vpc.amazonaws.com/efa: "4"` | FAILED - NIXL still discovers devices internally |
| Interface filter | `FI_EFA_INTERFACE=rdmap0s0-rdma0` | FAILED - Doesn't prevent device discovery |
| Manual rail count | `NIXL_LIBFABRIC_NUM_RAILS=1` | FAILED alone - Needs FI_EFA_DEV_LIST |

## Working Solution

The only working solution is to prevent libfabric from discovering multiple EFA devices at the provider level:

```yaml
FI_EFA_DEV_LIST: "0"  # Force libfabric to only see device 0
NIXL_LIBFABRIC_NUM_RAILS: "1"  # Tell NIXL to expect single rail
```

## Potential Upstream Fixes

1. **Fix offset calculation in serdes.cpp**: Ensure proper alignment after each field
2. **Add checksums**: Validate serialized data integrity
3. **Use structured serialization**: Replace custom format with protobuf/msgpack
4. **Add versioning**: Allow for format changes

## State Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NIXL LIBFABRIC Flow                             │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   Prefill    │
                              │   Worker     │
                              └──────┬───────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ NIXL Initialization   │
                         │ - fi_getinfo()        │
                         │ - Discover EFA devs   │
                         └───────────┬───────────┘
                                     │
              ┌──────────────────────┴──────────────────────┐
              │                                             │
              ▼                                             ▼
   ┌─────────────────────┐                     ┌─────────────────────┐
   │ FI_EFA_DEV_LIST=0   │                     │ All 32 EFA devices  │
   │ (Single device)     │                     │ discovered          │
   └──────────┬──────────┘                     └──────────┬──────────┘
              │                                           │
              ▼                                           ▼
   ┌─────────────────────┐                     ┌─────────────────────┐
   │ Serialize 1 rail    │                     │ Serialize 32 rails  │
   │ dest_data_ep_0      │                     │ dest_data_ep_0..31  │
   └──────────┬──────────┘                     └──────────┬──────────┘
              │                                           │
              ▼                                           ▼
   ┌─────────────────────┐                     ┌─────────────────────┐
   │ Send metadata via   │                     │ Send metadata via   │
   │ side channel        │                     │ side channel        │
   └──────────┬──────────┘                     └──────────┬──────────┘
              │                                           │
              │                                           │
              ▼                                           ▼
   ┌─────────────────────┐                     ┌─────────────────────┐
   │ Decode worker       │                     │ Decode worker       │
   │ deserializes        │                     │ deserializes        │
   └──────────┬──────────┘                     └──────────┬──────────┘
              │                                           │
              ▼                                           ▼
   ┌─────────────────────┐                     ┌─────────────────────┐
   │ ✓ SUCCESS           │                     │ ✗ FAILURE           │
   │ Single endpoint OK  │                     │ Offset misalignment │
   └─────────────────────┘                     │ at dest_data_ep_5   │
                                               └─────────────────────┘
```

## References

- NIXL GitHub: https://github.com/ai-dynamo/nixl
- NIXL 0.8.0 Release Notes
- TensorRT-LLM Disaggregated Inference Documentation
- AWS EFA Best Practices
