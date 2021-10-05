# Resource Tracking Kubernetes Kustomize overlay configuration

Declarative management of Kubernetes objects using Kustomize.

# How to use

Within an overlay directory, create a `.env` file to contain required secret
values in the format KEY=value (i.e. `overlays/uat/.env`). Example:

    POSTGRES_PASSWORD=value
    DATABASE_URL=value
    SECRET_KEY=value

See the main project `README` for all required values.

Run `kubectl` with the `-k` flag to generate resources for a given overlay:

```bash
kubectl apply -k overlays/uat
```

# References:

* https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/
* https://github.com/kubernetes-sigs/kustomize
* https://github.com/kubernetes-sigs/kustomize/tree/master/examples
