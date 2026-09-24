# Kubernetes Deployment

Production-grade manifests for running the Secure Polling App on Kubernetes.
Everything is wired through [Kustomize](https://kubectl.docs.kubernetes.io/), so
a single `kubectl apply -k k8s/` deploys the whole stack.

## What you get

| Resource          | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| `namespace.yaml`  | `polling` namespace (all resources are scoped to it)                    |
| `configmap.yaml`  | Non-secret config (`FLASK_ENV`, `DATA_DIR`, optional `DATABASE_URL`)    |
| `secret` (gen)    | `poll-secrets` Secret built from gitignored `k8s/secrets.env`           |
| `persistent-volume-claim.yaml` | 1Gi RWO volume for SQLite, encryption key and audit ledger   |
| `deployment.yaml` | App pod: init container (DB + admin bootstrap) + gunicorn with probes   |
| `service.yaml`    | ClusterIP service, port 80 -> 5000                                      |
| `ingress.yaml`    | Optional Ingress for `polls.example.com` (TLS via cert-manager)         |

## 1. Build & push the image

The image already runs as a non-root user (`appuser`, UID/GID 10001) matching
the pod `securityContext`. Push it to your registry and update
`k8s/kustomization.yaml`:

```bash
docker build -t ghcr.io/your-org/secure-polling-app:1.1.0 .
docker push ghcr.io/your-org/secure-polling-app:1.1.0
```

In `k8s/kustomization.yaml` set the `images` override (uncomment the block) so
the Deployment and init container pull your image.

## 2. Create secrets

```bash
cp k8s/secrets.env.example k8s/secrets.env
# edit k8s/secrets.env - set strong random values
openssl rand -hex 32                       # SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # POLL_ENCRYPTION_KEY
```

`k8s/secrets.env` is gitignored; Kustomize turns it into a `Secret` at apply
time. Values must avoid `#` and leading/trailing whitespace.

> Note: `POLL_ENCRYPTION_KEY` is the Fernet key that decrypts stored votes.
> It must stay stable for the life of the data — changing it makes existing
> votes unreadable.

## 3. Deploy

```bash
kubectl apply -k k8s/
kubectl get pods -n polling -w          # wait for 1/1 Running
kubectl get svc -n polling
```

The `db-init` init container creates the SQLite tables and the admin user
(`ADMINU`/`ADMINP` from the secret) before gunicorn starts.

## 4. Verify

```bash
kubectl exec -n polling deploy/poll-app -- curl -s localhost:5000/health
kubectl exec -n polling deploy/poll-app -- curl -s localhost:5000/ready
```

- `/health`  -> liveness probe
- `/ready`   -> readiness probe (checks the DB connection), 503 until ready

## 5. Expose it

Edit `k8s/ingress.yaml` (set your `host`) and uncomment what you need:

```bash
kubectl apply -k k8s/
curl -H "Host: polls.example.com" http://<LOAD_BALANCER_IP>/
```

TLS example with cert-manager is commented out — uncomment the annotations and
`tls` block and set the issuer name.

## Scaling

**SQLite mode (default):** exactly `replicas: 1`. SQLite is single-writer, and
the RWO PVC can only be attached to one node, so the Deployment uses a
`Recreate` strategy (never scale beyond 1 replica, and do not switch to
`RollingUpdate`).

**Multi-replica mode:** point the app at a shared database by uncommenting
`DATABASE_URL` in `k8s/configmap.yaml` (e.g. PostgreSQL), then raise
`replicas`. Stored votes keep using the same Fernet `POLL_ENCRYPTION_KEY`.

## Upgrades

Because `Recreate` is used, a rollout fully terminates the old pod before the
new one mounts the volume:

```bash
# update the image tag in kustomization.yaml, then:
kubectl apply -k k8s/
kubectl rollout status deploy/poll-app -n polling
```

## Teardown

```bash
kubectl delete -k k8s/
```

> The `poll-data` PVC is deleted too — back it up first if you care about the
> data (see `kubectl get pvc -n polling -o yaml` before deleting).