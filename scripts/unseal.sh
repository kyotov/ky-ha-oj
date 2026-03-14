#!/usr/bin/env bash
set -euo pipefail

SEALED_SECRET="${1:-k8s/secret.yaml}"
KEYFILE=$(mktemp)
trap 'rm -f "$KEYFILE"' EXIT

echo "Fetching master key from cluster..." >&2
kubectl get secret -n kube-system \
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o jsonpath='{.items[0].data.tls\.key}' | base64 -d > "$KEYFILE"

echo "Decrypting $SEALED_SECRET..." >&2
PLAIN=$(kubeseal --recovery-unseal --recovery-private-key "$KEYFILE" < "$SEALED_SECRET")

USERNAME=$(echo "$PLAIN" | python3 -c "import sys,json,base64; d=json.load(sys.stdin)['data']; print(base64.b64decode(d['username']).decode())")
PASSWORD=$(echo "$PLAIN" | python3 -c "import sys,json,base64; d=json.load(sys.stdin)['data']; print(base64.b64decode(d['password']).decode())")

echo "Starting server..." >&2
THERMOSTAT_USERNAME="$USERNAME" THERMOSTAT_PASSWORD="$PASSWORD" uvicorn main:app --port 8001 --reload
