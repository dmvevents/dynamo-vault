# AWS EKS Setup Guide

This guide covers setting up an AWS EKS cluster for TensorRT-LLM disaggregated inference with EFA support.

## Prerequisites

- AWS CLI configured
- eksctl installed
- kubectl installed
- Helm installed

## 1. Create EKS Cluster

```bash
eksctl create cluster \
  --name trtllm-cluster \
  --region us-west-2 \
  --version 1.29 \
  --without-nodegroup
```

## 2. Create GPU Node Group with EFA

```yaml
# nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: trtllm-cluster
  region: us-west-2

managedNodeGroups:
  - name: gpu-efa-nodes
    instanceType: p5.48xlarge
    desiredCapacity: 2
    minSize: 0
    maxSize: 4
    volumeSize: 500
    efaEnabled: true
    gpu: true
    labels:
      workload: gpu
    taints:
      - key: nvidia.com/gpu
        value: "true"
        effect: NoSchedule
```

```bash
eksctl create nodegroup -f nodegroup.yaml
```

## 3. Install NVIDIA GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm install --wait \
  --namespace gpu-operator \
  --create-namespace \
  gpu-operator nvidia/gpu-operator \
  --set driver.enabled=true \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true
```

## 4. Install EFA Device Plugin

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-eks-pod-identity-webhook/master/config/webhook.yaml

kubectl apply -f https://raw.githubusercontent.com/aws/aws-k8s-efa-plugin/master/config/efa-k8s-device-plugin.yaml
```

## 5. Verify Setup

### Check GPU Nodes
```bash
kubectl get nodes -l workload=gpu
kubectl describe node <node-name> | grep -A10 "Allocatable"
```

Expected:
```
nvidia.com/gpu: 8
vpc.amazonaws.com/efa: 32
```

### Check Device Plugins
```bash
kubectl get pods -n kube-system | grep -E "efa|nvidia"
```

## 6. Install NVIDIA Dynamo Operator

```bash
# Add Dynamo Helm repo (if available)
helm repo add nvidia-dynamo https://nvidia.github.io/dynamo
helm repo update

# Install Dynamo operator
helm install dynamo-operator nvidia-dynamo/dynamo-operator \
  --namespace dynamo-system \
  --create-namespace
```

## 7. Configure Storage (Optional)

For model caching, set up EFS:

```bash
# Create EFS file system
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode elastic \
  --tags Key=Name,Value=trtllm-models

# Install EFS CSI driver
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm install aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver \
  --namespace kube-system
```

## 8. Security Groups

Ensure your EKS security groups allow:
- EFA traffic (all ports between nodes in the same security group)
- Port 5600 for NIXL side channel
- Port 8000 for frontend HTTP

## 9. Deploy TensorRT-LLM

```bash
# Apply ConfigMap
kubectl apply -f kubernetes/common/configmap.yaml

# Deploy LIBFABRIC variant
kubectl apply -f kubernetes/libfabric/deployment.yaml

# Or deploy UCX variant
kubectl apply -f kubernetes/ucx/deployment.yaml
```

## 10. Verify Deployment

```bash
# Check pods
kubectl get pods -l app.kubernetes.io/instance=trtllm-libfabric

# Check EFA allocation
kubectl describe pod <prefill-pod> | grep efa

# Test inference
kubectl port-forward svc/trtllm-libfabric-frontend 8000:8000 &
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-0.6B", "prompt": "Hello", "max_tokens": 10}'
```

## Instance Type Reference

| Instance | GPUs | EFA | Recommended For |
|----------|------|-----|-----------------|
| p5.48xlarge | 8x H100 | 32x | Production LIBFABRIC |
| p4d.24xlarge | 8x A100 | 4x | Production LIBFABRIC |
| p4de.24xlarge | 8x A100 | 4x | Production LIBFABRIC |
| g5.48xlarge | 8x A10G | No | UCX only |

## Cost Optimization

- Use Spot instances for development
- Scale down to 0 nodes when not in use
- Use smaller models (Qwen/Qwen3-0.6B) for testing
