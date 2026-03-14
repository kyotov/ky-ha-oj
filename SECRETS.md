# Secret Management

Secrets are managed with [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets).
`k8s/secret.yaml` contains encrypted ciphertext and is safe to commit to git.
Only the in-cluster controller can decrypt it.

## How it works

1. `kubeseal` encrypts a plain Secret using the controller's public key
2. The encrypted `SealedSecret` is stored in git
3. When applied to the cluster, the controller decrypts it and creates the real `Secret`

## Update credentials

```bash
kubectl create secret generic thermostat-credentials \
  --namespace monitoring \
  --from-literal=username=your@email.com \
  --from-literal=password=yourpassword \
  --dry-run=client -o yaml | \
  kubeseal --controller-namespace kube-system --format yaml > k8s/secret.yaml

kubectl apply -f k8s/secret.yaml
git add k8s/secret.yaml && git commit -m "Update thermostat credentials"
```

## Install kubeseal CLI

```bash
KUBESEAL_VERSION=$(curl -s https://api.github.com/repos/bitnami-labs/sealed-secrets/releases/latest \
  | grep '"tag_name"' | cut -d'"' -f4 | tr -d 'v')
curl -sL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz" \
  | tar xz -C ~/.local/bin kubeseal
```

## Backup the controller key

The controller generates a keypair on first install. If the cluster is lost, you
cannot decrypt existing SealedSecrets without the private key. Back it up:

```bash
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o yaml > sealed-secrets-master-key.yaml
```

Store this file somewhere safe (password manager, encrypted storage) — do **not**
commit it to git.

To restore on a new cluster:
```bash
kubectl apply -f sealed-secrets-master-key.yaml
kubectl rollout restart deployment/sealed-secrets-controller -n kube-system
```
