# Developer Guide

This guide talks about how to setup local environment for your development and testing for Krkn-AI.


## 1. Setup Krkn-AI repository

```bash
# Option 1: Clone repository
git clone https://github.com/krkn-chaos/krkn-ai.git

# Option 2: Fork the repository to your Github profile and clone it.
git clone https://github.com/<username>/krkn-ai.git
```

Install the necessary pre-requisites and Krkn-AI CLI as per project [readme](../README.md).

```bash
# Verify krkn-ai installation
uv run krkn_ai --help
```

## 2. Setup Minikube

We will be using [minikube](https://minikube.sigs.k8s.io/docs/start/) to setup a small local cluster.

```bash
# Install on Linux
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64

# Create minikube cluster
minikube start

# Verify cluster
kubectl get pods -A

# Generate kubeconfig
./scripts/generate-kubeconfig.sh
ls -l | grep kubeconfig.yaml
```


## 3. Install Prometheus

### Install Prometheus Operator

[Prometheus Operator](https://prometheus-operator.dev/) makes it easier to manage Prometheus instances on cluster. 

```bash
LATEST=$(curl -s https://api.github.com/repos/prometheus-operator/prometheus-operator/releases/latest | jq -cr .tag_name)
curl -sL https://github.com/prometheus-operator/prometheus-operator/releases/download/${LATEST}/bundle.yaml | kubectl create -f -
```

### Setup Prometheus Instance

```bash
# Install Prometheus
kubectl apply -f scripts/monitoring/prometheus.yaml

# Setup monitoring services for kube and node metrics 
kubectl apply -f scripts/monitoring/kube_state_metrics.yaml
kubectl apply -f scripts/monitoring/node_exporter.yaml
```

After setting up above monitoring serivces, we should be able to query prometheus after couple of minutes.

```bash
curl -G \
  "http://$(minikube ip):30900/api/v1/query" \
  --data-urlencode 'query=up'
```

## 4. Deploy Sample Microservice

```bash
# Deploy robot-shop example
export DEMO_NAMESPACE=robot-shop
export IS_OPENSHIFT=false
./scripts/setup-demo-microservice.sh

# Switch to application namespace
kubectl config set-context --current --namespace=$DEMO_NAMESPACE
kubectl get pods

# Setup nginx reverse proxy
./scripts/setup-nginx.sh
export HOST="http://$(minikube ip):$(kubectl get service rs -o json | jq -r '.spec.ports[0].nodePort')"

# Verify nginx setup
./scripts/test-nginx-routes.sh
```

## 5. Running Krkn-AI

### Discover components

Let us auto-generate initial krkn-ai config file for the testing.

```bash
uv run krkn_ai discover -k ./kubeconfig.yaml \
  -n "robot-shop" \
  -pl "service" \
  -nl "kubernetes.io/hostname" \
  -o ./krkn-ai.yaml \
  --skip-pod-name "nginx-proxy.*"
```

This command will generate `krkn-ai.yaml` that contains details about cluster components along with few boilerplate code for test configuration. Feel free to modify the code, add health check endpoints, update Fitness function, enable scenarios before running the krkn-ai test.

> Note: Specific scenarios might not work depending on the cluster environment, as we are not using an actual node or due to limited permissions.

### Start Krkn-AI tests

```bash
export PROMETHEUS_URL="http://$(minikube ip):30900"

uv run krkn_ai run -vv \
    -r krknhub \
    -c ./krkn-ai.yaml \
    -o ./results \
    -p HOST=$HOST
```

