#!/usr/bin/env bash
set -euo pipefail

IMAGE=registry.kamenet.org/oj-microline:latest

podman build -t "$IMAGE" .
podman push "$IMAGE"
kubectl rollout restart deployment/oj-microline -n monitoring
kubectl rollout status deployment/oj-microline -n monitoring
