# Grafana on Kubernetes

## Instance Details

| Detail | Value |
|---|---|
| **URL** | https://grafana.kamenet.org |
| **Namespace** | `monitoring` |
| **Pod** | `prometheus-grafana-57cc4d7fc4-9pxmm` |
| **Image** | `grafana/grafana:12.3.0` |
| **Service** | `ClusterIP 10.43.156.75:80` |
| **Ingress** | Traefik @ `192.168.12.66` |

## Credentials

| Field | Value |
|---|---|
| **Username** | `admin` |
| **Password** | `admin` |

## Reset Admin Password

If the password stops working, reset it via kubectl:

```bash
kubectl exec -n monitoring prometheus-grafana-57cc4d7fc4-9pxmm -c grafana -- \
  grafana cli admin reset-admin-password <new-password>
```

## Notes

- Deployed as part of the `prometheus` Helm release (kube-prometheus-stack)
- Each container had 1 restart ~107 days after initial deploy (likely node reboot), stable since
- LDAP is configured but not enabled — local auth is used

----

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion