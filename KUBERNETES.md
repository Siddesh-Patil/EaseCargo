# 🚀 EaseCargo Kubernetes Deployment Guide

Complete guide for deploying EaseCargo to Kubernetes clusters on Azure, AWS, GCP, and local environments.

## Quick Start

### Prerequisites

- `kubectl` CLI installed and configured
- Access to a Kubernetes cluster
- Docker image pushed to a container registry (Docker Hub, Azure Container Registry, etc.)

### Deploy to Cluster

```bash
# 1. Apply all manifests
kubectl apply -f k8s/

# 2. Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services

# 3. Get the external IP (may take a minute)
kubectl get svc easecargo-service

# 4. Access the application
# Visit: http://<EXTERNAL-IP>:80
```

### View Logs

```bash
# Follow logs from all pods
kubectl logs -f deployment/easecargo

# Follow logs from specific pod
kubectl logs -f pod/easecargo-xxxxx

# Stream logs from all containers
kubectl logs -f deployment/easecargo --timestamps=true
```

### Scale the Deployment

```bash
# Manually scale to specify replica count
kubectl scale deployment/easecargo --replicas=5

# Check current replicas
kubectl get deployment/easecargo
```

## Detailed Deployment

### 1. Prepare Container Image

#### Build Locally

```bash
docker build -t easecargo:latest .
docker tag easecargo:latest easecargo:v1.0.0
```

#### Push to Registry

**Docker Hub:**
```bash
docker login
docker push username/easecargo:latest
docker push username/easecargo:v1.0.0
```

**Azure Container Registry:**
```bash
az acr login --name <registry-name>
docker tag easecargo:latest <registry-name>.azurecr.io/easecargo:latest
docker push <registry-name>.azurecr.io/easecargo:latest
```

**AWS ECR:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag easecargo:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/easecargo:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/easecargo:latest
```

### 2. Update Image Reference

Edit `k8s/deployment.yaml` to use your registry:

```yaml
containers:
- name: easecargo
  image: your-registry/easecargo:latest  # Update this line
  imagePullPolicy: Always
```

For private registries, create and reference an ImagePullSecret:

```bash
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email>
```

Then add to deployment:

```yaml
spec:
  template:
    spec:
      imagePullSecrets:
      - name: regcred
```

### 3. Configure Secrets

Update sensitive data in `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: easecargo-secrets
type: Opaque
stringData:
  SECRET_KEY: "your-secure-secret-key-here"
  # For database password if using PostgreSQL:
  # DATABASE_URL: "postgresql://user:password@postgres-host/easecargo"
```

Or create from command line:

```bash
kubectl create secret generic easecargo-secrets \
  --from-literal=SECRET_KEY="your-secret-key" \
  --from-literal=DATABASE_URL="postgresql://user:password@host/db"
```

### 4. Deploy

Apply all manifests:

```bash
kubectl apply -f k8s/
```

This creates:
- Deployment with 3 replicas
- LoadBalancer Service
- ConfigMap with configuration
- Secret with sensitive data
- PersistentVolumeClaim for database
- ServiceAccount for RBAC
- Ingress for HTTP routing (optional)
- HorizontalPodAutoscaler for auto-scaling

### 5. Verify Deployment

```bash
# Check deployments
kubectl get deployments
kubectl describe deployment easecargo

# Check pods
kubectl get pods
kubectl describe pod <pod-name>

# Check services
kubectl get svc
kubectl describe svc easecargo-service

# Check events
kubectl get events
```

## Cloud Provider Specific Guidance

### Azure Kubernetes Service (AKS)

#### Create Cluster
```bash
az aks create \
  --resource-group myResourceGroup \
  --name myAKSCluster \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard \
  --enable-managed-identity \
  --network-plugin azure \
  --docker-bridge-address 172.17.0.1/16
```

#### Get Credentials
```bash
az aks get-credentials \
  --resource-group myResourceGroup \
  --name myAKSCluster
```

#### Use Azure Container Registry
```bash
# Attach ACR to AKS
az aks update \
  --name myAKSCluster \
  --resource-group myResourceGroup \
  --attach-acr <registry-name>

# Update image reference in deployment.yaml
image: <registry-name>.azurecr.io/easecargo:latest
```

#### Configure Managed Identity (Recommended)
```bash
# AKS will automatically use managed identity to pull from ACR
# No need for ImagePullSecret
```

#### Set Up HTTPS with Let's Encrypt
```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Update ingress.yaml to reference certificate
```

### AWS Elastic Kubernetes Service (EKS)

#### Create Cluster
```bash
eksctl create cluster \
  --name easecargo-cluster \
  --version 1.28 \
  --region us-east-1 \
  --nodegroup-name easecargo-nodes \
  --node-type t3.medium \
  --nodes 3
```

#### Update kubeconfig
```bash
aws eks update-kubeconfig \
  --name easecargo-cluster \
  --region us-east-1
```

#### AWS Load Balancer Controller (for LoadBalancer services)
```bash
# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=easecargo-cluster
```

### Google Kubernetes Engine (GKE)

#### Create Cluster
```bash
gcloud container clusters create easecargo-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-1
```

#### Get Credentials
```bash
gcloud container clusters get-credentials easecargo-cluster --zone us-central1-a
```

### Local Testing (Minikube)

#### Install and Start
```bash
minikube start --cpus=4 --memory=4096
eval $(minikube docker-env)
```

#### Build and Deploy
```bash
# Build image (inside minikube's Docker)
docker build -t easecargo:latest .

# Deploy
kubectl apply -f k8s/

# Access service
minikube service easecargo-service
```

## Monitoring and Maintenance

### Check Application Health

```bash
# Direct health check
kubectl exec -it <pod-name> -- curl localhost:5000/

# Port forward to local
kubectl port-forward svc/easecargo-service 5000:80

# Then visit: http://localhost:5000
```

### Update Application

```bash
# Build and push new image
docker build -t easecargo:v1.1.0 .
docker push your-registry/easecargo:v1.1.0

# Update deployment
kubectl set image deployment/easecargo \
  easecargo=your-registry/easecargo:v1.1.0 \
  --record

# Check rollout status
kubectl rollout status deployment/easecargo

# Rollback if needed
kubectl rollout undo deployment/easecargo
```

### Scale Application

```bash
# Manual scaling
kubectl scale deployment easecargo --replicas=5

# Check HPA status
kubectl get hpa
kubectl describe hpa easecargo-hpa

# View HPA events
kubectl get events --field-selector involvedObject.name=easecargo-hpa
```

### Database Management

For production, consider using a managed database:

**Azure Database for PostgreSQL:**
```bash
az postgres flexible-server create \
  --resource-group myResourceGroup \
  --name easecargo-db \
  --location eastus
```

Update `DATABASE_URL` in configmap:
```yaml
DATABASE_URL: "postgresql://user:password@easecargo-db.postgres.database.azure.com/easecargo"
```

### Backup and Recovery

```bash
# Export resource definitions
kubectl get all -n default -o yaml > backup.yaml

# Re-apply from backup
kubectl apply -f backup.yaml

# Backup persistent volume data
# (depends on your storage backend - check provider docs)
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status and events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # For crashed containers
```

### Image pull errors

```bash
# Check image pull policy
kubectl get pod <pod-name> -o yaml | grep imagePullPolicy

# Verify image exists in registry
docker pull your-registry/easecargo:latest

# Check ImagePullSecret if using private registry
kubectl get secret regcred
```

### Service not accessible

```bash
# Check service configuration
kubectl get svc easecargo-service
kubectl describe svc easecargo-service

# Check endpoints
kubectl get endpoints easecargo-service

# Port forward to test
kubectl port-forward svc/easecargo-service 5000:80
```

### Storage issues

```bash
# Check PVC status
kubectl get pvc
kubectl describe pvc easecargo-db-pvc

# Check PV
kubectl get pv
kubectl describe pv <pv-name>
```

## Performance Tuning

### Adjust Resource Limits

In `k8s/deployment.yaml`:
```yaml
resources:
  requests:
    cpu: 500m          # Increase if needed
    memory: 1Gi
  limits:
    cpu: 1000m
    memory: 2Gi
```

### Increase Replicas

```bash
kubectl scale deployment easecargo --replicas=10
```

### Enable Autoscaling

HorizontalPodAutoscaler is already configured in `k8s/ingress.yaml`

Monitor metrics:
```bash
# View HPA metrics
kubectl top pods
kubectl top nodes
```

## Production Checklist

- [ ] Container image tested locally
- [ ] Image pushed to secure registry
- [ ] Secrets and credentials configured
- [ ] Persistent storage configured
- [ ] Ingress and TLS certificates set up
- [ ] RBAC roles configured
- [ ] Network policies defined
- [ ] Monitoring and logging enabled
- [ ] Backup and recovery tested
- [ ] Resource limits set appropriately
- [ ] Auto-scaling configured
- [ ] Load testing completed

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [GKE Documentation](https://cloud.google.com/kubernetes-services/)

## Support

For issues:
1. Check pod logs: `kubectl logs <pod-name>`
2. Describe resources: `kubectl describe <resource-type> <resource-name>`
3. Check events: `kubectl get events`
4. Review Kubernetes documentation for the specific error

---

**Happy Kubernetes deploying! 🚀**
