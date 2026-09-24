# Secure Polling App - Helm Chart

Helm (v3) chart for deploying the [Secure Polling App](../../README.md) on
Kubernetes. It ships the same hardened deployment as the Kustomize manifests in
[`k8s/`](../../k8s/) but is fully parameterized via `values.yaml`.

## Install

```bash
helm repo add ...            # or use the local chart directly
helm install poll helm/secure-polling-app --namespace polling --create-namespace
```

By default the chart auto-generates `SECRET_KEY`, `ADMINP` and a valid Fernet
`POLL_ENCRYPTION_KEY` on first install and **reuses them across upgrades** (via
`helm lookup`), so data stays decryptable. Provide explicit values for full
control:

```bash
helm install poll helm/secure-polling-app \
  --namespace polling --create-namespace \
  --set image.repository=ghcr.io/your-org/secure-polling-app \
  --set image.tag=1.1.0 \
  --set secrets.SECRET_KEY="$(openssl rand -hex 32)" \
  --set secrets.ADMINU=admin \
  --set secrets.ADMINP='A Very Strong Password! 123' \
  --set secrets.POLL_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

## Configuration

See [`values.yaml`](values.yaml) for the full reference. Key knobs:

| Parameter | Default | Notes |
|---|---|---|
| `image.repository` / `image.tag` | `poll-app` / `1.1.0-k8s` | point at your registry |
| `replicaCount` | `1` | keep `1` with SQLite |
| `env.DATABASE_URL` | `""` | set to a shared DB before scaling / autoscaling |
| `env.GUNICORN_WORKERS` / `GUNICORN_THREADS` | `4` / `4` | gunicorn tuning via config map |
| `secrets.existingSecret` | `""` | reference a pre-created Secret instead |
| `secrets.SECRET_KEY` / `ADMINP` / `POLL_ENCRYPTION_KEY` | auto/empty | explicit secret values |
| `persistence.size` / `storageClass` | `1Gi` / default | database + key + ledger volume |
| `ingress.enabled` | `false` | host + tls in `ingress.*` |
| `resources` | 200m/256Mi → 1000m/512Mi | app container requests/limits |
| `autoscaling.enabled` | `false` | requires `env.DATABASE_URL` |

Leave `replicaCount` / autoscaling at single-replica settings unless you set
`env.DATABASE_URL` to a shared database (SQLite is single-writer). The
Deployment uses a `Recreate` strategy so the ReadWriteOnce PVC can be
re-attached cleanly on upgrades.

## Checking credentials

```bash
kubectl get secret poll-secure-polling-app-secrets -n polling \
  -o jsonpath='{.data.ADMINP}' | base64 -d; echo
```

## Run the built-in test

```bash
helm test poll -n polling
```

## Upgrade / uninstall

```bash
helm upgrade poll helm/secure-polling-app --namespace polling
helm uninstall poll --namespace polling   # note: deletes the PVC (and data)
```

Recommended `values-production.yaml` snippet:

```yaml
image:
  repository: ghcr.io/your-org/secure-polling-app
  tag: "1.1.0"
secrets:
  existingSecret: poll-secrets   # managed externally (SOPS/SealedSecrets/Vault)
persistence:
  size: 5Gi
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: polls.example.com
  tls:
    - secretName: poll-tls
      hosts:
        - polls.example.com
```