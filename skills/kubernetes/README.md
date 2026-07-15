# Kubernetes

Inspect and operate a Kubernetes cluster through the Kubernetes REST API using a ServiceAccount
bearer token. Pure Python standard library (`urllib` + `ssl`) — no `kubectl`, no third-party
packages. Talks directly to the API server, verifying TLS against the cluster CA.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `kubernetes.list_namespaces` | none | List all namespaces (`GET /api/v1/namespaces`). |
| `kubernetes.list_pods` | none | List pods in a namespace or cluster-wide; returns name, phase, node, restarts. |
| `kubernetes.get_pod_logs` | none | Fetch a pod's logs (optional container, tailLines); returned as `{"logs": ...}`. |
| `kubernetes.list_deployments` | none | List deployments; returns name, desired replicas, available. |
| `kubernetes.list_services` | none | List services (type, clusterIP, ports). |
| `kubernetes.list_nodes` | none | List nodes with Ready status and kubelet version. |
| `kubernetes.scale_deployment` | medium | Scale a deployment to a given replica count (merge-patch on the `/scale` subresource). |

## Connection / Auth

Configure the Kubernetes connection with:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `apiServer` | url | yes | API server base URL, e.g. `https://10.0.0.1:6443`. |
| `token` | secret | yes | ServiceAccount bearer token with rights over the target resources. |
| `caCert` | text | no | Cluster CA certificate (PEM) used to verify the API server's TLS certificate. |
| `insecureSkipVerify` | text | no | Set to `'true'` to skip TLS verification (not recommended). |

All requests send `Authorization: Bearer {token}`. TLS is verified against `caCert` when provided;
otherwise the system trust store is used. Setting `insecureSkipVerify` to `'true'` disables
certificate verification entirely — prefer supplying the cluster CA instead.

Every API or validation error is returned as `{"error": "..."}` on stdout with exit code 0.

## Permissions

The ServiceAccount token needs RBAC permission for the resources you use: `get`/`list` on
namespaces, pods, pods/log, deployments, services and nodes, and `patch` on
`deployments/scale` for `kubernetes.scale_deployment`.

## Trademarks

Kubernetes is a registered trademark of The Linux Foundation. This integration is community-built
and not affiliated with or endorsed by the Kubernetes project or the Cloud Native Computing
Foundation.
