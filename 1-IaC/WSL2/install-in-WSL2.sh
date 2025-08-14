#!/bin/bash 
set -e
set -x

###################
# 0 - kubectl alias function
# This function allows you to use `k` as an alias for `kubectl` commands
###################
k() {
    sudo microk8s kubectl "$@"
}

###################
# 1 - update ubuntu
###################
sudo apt-get update -y
sudo apt-get upgrade -y

################################################
# 2 - Install mandatory tools like docker,  kubectl 
#     and git and clone the repo
################################################

## 2.1 - docker
# Docker is a platform for developing, shipping, and running applications in containers.
# It provides a way to package applications and their dependencies into a single container image that can be run on any system that supports Docker.
########
# Prerequisites
sudo apt-get install -y ca-certificates curl gnupg lsb-release
# Add Docker’s official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
# Install Docker Engine
sudo apt update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
# Optional: Add your user to the docker group
sudo usermod -aG docker $USER

## 2.2 - kubectl
# kubectl is the command-line tool for interacting with Kubernetes clusters.
# It allows users to create, modify, and manage Kubernetes resources using a command-line interface (CLI).
#########
sudo apt-get update
# apt-transport-https may be a dummy package; if so, you can skip that package
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg
# If the folder `/etc/apt/keyrings` does not exist, it should be created before the curl command, read the note below.
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
sudo chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg # allow unprivileged APT programs to read this keyring
# Download the public signing key for the Kubernetes package repositories
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo chmod 644 /etc/apt/sources.list.d/kubernetes.list
#Install
sudo apt-get update
sudo apt-get install -y kubectl
# Verify
kubectl version --client

## 2.3 - Install Helm
# Helm is a package manager for Kubernetes that simplifies the deployment and management of applications in Kubernetes clusters
########
# The default Ubuntu repositories do not yet provide the Helm package
# https://cloudcone.com/docs/article/how-to-install-helm-on-ubuntu-22-04/
sudo snap install helm --classic
helm version

## 2.4 - Install git
# Deploy git and clone the repo
########
sudo apt-get install git -y
cd ~
git clone https://github.com/inigokintana/homelab-2-prod-ai-golden-path.git

######################
# 3 - Install microk8s
# MicroK8s is a lightweight, single-node Kubernetes distribution designed for developers and DevOps teams.
# It provides a simple way to run a FULL Kubernetes (networking all options)  on a local machine or in a development environment.
######################
sudo snap version
sudo snap list
sudo snap install microk8s --classic --channel=1.32/stable
sudo microk8s status --wait-ready
# microk8s add-on offer easy way to enable dns dashboard storage 
# registry -> (LLM images can be heavy)
# rbac -> (Role-based access control) needed by dapr and other like argoCD
sudo microk8s enable dns dashboard hostpath-storage registry rbac
# kubectl alias k
# aliases in Ubuntu WSL2
#alias k="sudo microk8s kubectl"
echo "# microk8s alias" >> ~/.bashrc
echo "alias k='sudo microk8s kubectl'" >> ~/.bashrc
# execute the bashrc to get the alias working
#source  ~/.bashrc
k get nodes -o wide
# return to home directory
cd ~
# make microk8s credentials available
if [ -d .kube ]; then
    echo "Directory exists: .kube"
else
    echo "Directory does not exist. Creating: .kube"
    mkdir -p .kube
    echo "Directory created: .kube"
fi
sudo cp -p /var/snap/microk8s/current/credentials/client.config .kube/config
sudo chown $USER:microk8s .kube/config
# for helm root .kube/config is necesary
sudo su -c "microk8s config > /root/.kube/config"
# This command starts a proxy to the Kubernetes Dashboard UI in the background
# it will be available at https://127.0.0.1:10443
sudo microk8s dashboard-proxy &
# Because we enabled rbac in the microk8s cluster, we need to create a service account and cluster role binding for the microk8s dashboard
k create serviceaccount kubernetes-admin-dashboard -n kube-system --dry-run=client -o yaml > sa-kubernetes-admin-dashboard.yaml
k apply -f ./sa-kubernetes-admin-dashboard.yaml
k create clusterrolebinding kubernetes-admin-dashboard --clusterrole=cluster-admin --serviceaccount=kube-system:kubernetes-admin-dashboard -n kube-system --dry-run=client -o yaml > rb-kubernetes-admin-dashboard.yaml
k apply -f ./rb-kubernetes-admin-dashboard.yaml
# Since k 1.18 service account token is not created by default
# To get the token for the service account, run the following command
TOKEN=(k create token kubernetes-admin-dashboard -n kube-system)
echo "k create token kubernetes-admin-dashboard -n kube-system" > token-kubernetes-admin-dashboard.yaml
echo $TOKEN >> token-kubernetes-admin-dashboard.yaml

##########################
# 4 - Install Dapr in WSL2
##########################
## Install Dapr various CPUs architectures (INTEL & AMD or ARM) - change version file when needed
# Dapr is a portable, event-driven runtime that makes it easy for developers to build resilient, microservices-based applications.
# It provides APIs that simplify the development of microservices by abstracting away the complexities of distributed systems.

# See Dapr releases in https://github.com/dapr/cli/releases
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]
  then
    echo "Detected Intel or AMD architecture"
    wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_amd64.tar.gz
    tar -xvzf dapr_linux_amd64.tar.gz
elif [[ "$ARCH" == "aarch64" ]] 
  then
    echo "Detected ARM architecture"
    wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_arm64.tar.gz
    tar -xvzf dapr_linux_arm64.tar.gz
else
    echo "Unsupported architecture"
    exit 1
fi
sudo mv dapr /usr/local/bin/dapr

# Install dapr in k8s with redis and zipkin 
dapr init --kubernetes --dev
# in case uninstall is needed "dapr uninstall --kubernetes --all"
echo "Waiting for Dapr to be ready..."
sleep 180 # wait for Dapr to be ready
k get pods -n dapr-system
k get pods -n default
# Get status of Dapr services from Kubernetes
dapr status -k 
#Dapr provides a dashboard to monitor and interact with the services running in the cluster. To access the dashboard, run:
dapr dashboard -k -p 9999 &

## 4.1 - Configure zipkin and install prometheus to help dapr monitoring
########
# we must configure zipkin in advance before any other mandatory service or agent, daprd sidecar goes crazy otherwise
# so we install prometheus to keep monitoring together

## 4.1.a - install zipkin to get tracing information
# Zipkin is a distributed tracing system that helps gather timing data needed to troubleshoot latency problems in microservice architectures.
# It provides a way to collect and visualize trace data from distributed systems, making it easier to identify performance bottlenecks and understand the flow of requests through the system.
# See https://zipkin.io/
# Enable zipkin tracing in Dapr
cd ~/homelab-2-prod-ai-golden-path/4-optional-k8s-services/zipkin
k apply -f zipkin.yaml

## 4.1.b install prometheus for dapr metrics
# Prometheus is an open-source monitoring and alerting toolkit designed for reliability and scalability.
# https://docs.dapr.io/operations/observability/metrics/prometheus/
cd /home/ubuntu/homelab-2-prod-ai-golden-path/4-optional-k8s-services/prometheus
# k apply -f namespace.yaml
sudo helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
sudo helm repo update
#For automatic discovery of Dapr targets (Service Discovery), use
sudo helm install dapr-prom prometheus-community/prometheus -f values.yaml -n dapr-monitoring --create-namespace --set prometheus-node-exporter.hostRootFsMount.enabled=false
# Ensure Prometheus is running in your cluster.
k get pods -n dapr-monitoring
sleep 10  
#To view the Prometheus dashboard and check service discovery:
k port-forward svc/dapr-prom-prometheus-server 9090:80 -n dapr-monitoring &
# Get he t the Alertmanager service to monitor alerts
k port-forward svc/dapr-prom-alertmanager 9093:9093 -n dapr-monitoring &

## 4.1.c install grafana for dapr metrics
# Grafana is an open-source platform for monitoring and observability that provides a powerful and flexible way to visualize and analyze metrics, logs, and traces from various data sources.
# https://docs.dapr.io/operations/observability/metrics/grafana/
# Add the Grafana Helm repo:
sudo helm repo add grafana https://grafana.github.io/helm-charts
sudo helm repo update
# Install the chart - dev persistence disabled
sudo helm install grafana grafana/grafana -n dapr-monitoring --set persistence.enabled=false
# Retrieve the admin password for Grafana login:
k get secret --namespace dapr-monitoring grafana -o jsonpath="{.data.admin-password}" | base64 --decode ; echo
echo "You will get a password similar to cj3m0OfBNx8SLzUlTx91dEECgzRlYJb60D2evof1%. If at the end there is % character remove it from the password to get cj3m0OfBNx8SLzUlTx91dEECgzRlYJb60D2evof1 as the admin password."
# Validation Grafana is running in your cluster:
k get pods -n dapr-monitoring
sleep 10  
# To access the Grafana dashboard, you can use port forwarding:
k port-forward svc/grafana 8080:80 -n dapr-monitoring &

########################################
# 5 - Install mandatory k8s services
########################################

## 5.1 - Install Ollama arm/Intel/AMD architecture - Preload Encodding: all-minilm & LLM: llama3.2:1b
########
cd ~/homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/ollama/deploy
# Ollama is a platform for running and sharing large language models (LLMs) locally.
# It provides a simple command-line interface (CLI) for running LLMs and a web-based UI for managing and sharing models.
# Ollama is designed to be easy to use and provides a variety of pre-trained models that can be run locally.
k apply -f namespace.yaml
k apply -f deployment.yaml
k apply -f service.yaml
# Port forwarding to check the http status of Ollama locally or from broser
echo "Waiting for Ollama to be ready..."
sleep 180 # wait for Ollama to be ready
k -n ollama port-forward service/ollama 11434:80 &
sleep 5 # wait for port-forward to be ready
k get pod -n ollama
# Test the Ollama API locally
# k -n ollama exec -it pod/ollama-59476b6f4c-rmjkz -- sh
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "What is Kubernetes?",
  "stream": false,
  "raw": true
  }'

## 5.2 - Install Timescale DB with pgvector extension and vectorizer for LLM RAG
########
cd ~/homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/timescaleDB/deploy
k  apply -f namespace.yaml
k  apply -f data-pv.yaml
k  apply -f data-pv-claim.yaml
# we need to change permisson in the mount point
sudo mkdir -p /mnt/pgdata
sudo chown $USER:$USER /mnt/pgdata
k  apply -f secret-pgvector.yaml
# vectorizer to ollama connection config is done with k8s DNS no Dapr naming - to check with Dapr naming app_id='ollama-llm.ollama' 
# post http://localhost:3500/v1.0/invoke/ollama-llm.ollama/method/chat
k  apply -f deployment.yaml
k  apply -f service.yaml
echo "Waiting for TimescaleDB and Vectorizer to be ready..."
sleep 180 # wait for TimescaleDB to be ready
# be able to connect to postgres from Ubuntu 22.04 locally
k -n pgvector port-forward service/pgvector 15432:5432 &
sleep 5 # wait for port-forward to be ready

##############################################
# 6- Install dapr microservices agents in K8s
##############################################
# two options:
# microk8s kubectl get pods -n container-registry
# docker tag myapp:latest localhost:32000/myapp:latest
# docker push localhost:32000/myapp:latest
# or
# microk8s.docker build -t localhost:32000/myapp:latest .
# microk8s.docker push localhost:32000/myapp:latest

## 6.1 - psql database
##### 
# psql password
sudo apt-get install -y postgresql-client-common
sudo apt-get install -y postgresql-client
echo "localhost:15432:postgres:postgres:pgvector" > ~/.pgpass
chmod 600 ~/.pgpass
## NOTE
## This password was created in deployment.yaml & secret-pgvector.yaml
## in  ./homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/timescaleDB/deploy

## 6.2 - Install pgAI in postgres
########
# pgAI is a PostgreSQL extension that provides AI capabilities, such as vectorization and embedding, for PostgreSQL databases.
# See -- https://github.com/timescale/pgai/issues/858  --
# TimescaleDB images are released periodically and do not mantain pgAI version inside the image.
# Additionally,  before pgAI 0.10 we need to "CREATE EXTENSION IF NOT EXISTS ai CASCADE;" but 
# after pgAI 0.10 it is intalled outside the database with python this way
sudo apt-get install -y python3-pip
pip install pgai
export PATH=$PATH:/home/$USER/.local/bin
pgai install -d postgres://postgres:pgvector@localhost:15432/postgres # IN PROD you should change postgres password later

## 6.3 - Injection Agent Web Dapr
########
# create database table & create the vectorized table
cd ~/homelab-2-prod-ai-golden-path/3-dapr-microservices-agents/2-injection-agent-web-dapr
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-table.sql
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-vectorized-table.sql
# create local registry image -  build the image with microk8s docker
docker build -t localhost:32000/injection-agent-web-dapr:latest .
# push the image to the local registry
docker push localhost:32000/injection-agent-web-dapr:latest    
# deploy the application into mikrok8s - create Dev environment
k apply -f ./k8s/overlays/dev/output_dev.yaml
# secret permision for the agent-web-dapr to access the database 
k apply -f ./k8s/base/secret-reader-role.yaml
k apply -f ./k8s/base/secret-reader-rolebinding.yaml

## 6.4 - User Web Dapr Agent
########
# create database table & create the vectorized table
cd ~/homelab-2-prod-ai-golden-path/3-dapr-microservices-agents/2-injection-agent-web-dapr/sql
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-table.sql
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-vectorized-table.sql
# create local registry image -  build the image with microk8s docker
docker build -t localhost:32000/user-web-dapr:latest .
# push the image to the local registry
docker push localhost:32000/user-web-dapr:latest    
# deploy the application into mikrok8s - create Dev environment
# OpeanAI api key - Substitute it manually later and do not generate YAML not to get your OpenAI key exposed
# we must set it knownow with a fake value otherwise user-web pod fails to start
k -n agents create secret generic openai-api-key --from-literal=dapr=test-change-it
k apply -f ./k8s/overlays/dev/output_dev.yaml
# 5000 flask port forward
sleep 10 # wait for user-web to be ready
k -n agents port-forward service/user-web-dapr 5000:80 &

#####################################
# 7 - Optional tools and utilities
#####################################

## 7.1 - Opentofu
# Opentofu is an open-source alternative to Terraform, a popular infrastructure as code (IaC) tool.
# Opentofu is designed to be compatible with Terraform configurations and provides a similar command-line interface
######
# tooling
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg
# Add the OpenTofu APT repo
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://get.opentofu.org/opentofu.gpg | sudo tee /etc/apt/keyrings/opentofu.gpg >/dev/null
curl -fsSL https://packages.opentofu.org/opentofu/tofu/gpgkey | sudo gpg --no-tty --batch --dearmor -o /etc/apt/keyrings/opentofu-repo.gpg >/dev/null
sudo chmod a+r /etc/apt/keyrings/opentofu.gpg /etc/apt/keyrings/opentofu-repo.gpg
# create the OpenTofu source list
echo \
  "deb [signed-by=/etc/apt/keyrings/opentofu.gpg,/etc/apt/keyrings/opentofu-repo.gpg] https://packages.opentofu.org/opentofu/tofu/any/ any main
deb-src [signed-by=/etc/apt/keyrings/opentofu.gpg,/etc/apt/keyrings/opentofu-repo.gpg] https://packages.opentofu.org/opentofu/tofu/any/ any main" | \
  sudo tee /etc/apt/sources.list.d/opentofu.list > /dev/null
sudo chmod a+r /etc/apt/sources.list.d/opentofu.list

# Install OpenTofu
sudo apt update
sudo apt-get install -y tofu
# Verify
tofu version

# 7.2 - Kustomize
# Kustomize is a tool for managing Kubernetes configurations.
# It allows users to create, modify, and manage Kubernetes resources using a declarative approach.
#######
# Download latest kustomize release (replace version as needed)
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
# Move to a global location
sudo mv kustomize /usr/local/bin/
# Verify
kustomize version


# 7.3 - Tilt
# Tilt is a tool for managing Kubernetes applications.
# It provides a way to build, deploy, and manage applications in Kubernetes using a simple configuration file.
#########
# Install Tilt
curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash
# Verify
tilt version

## 7.4 - VSCode
# Visual Studio Code (VSCode) is a popular open-source code editor developed by Microsoft.
# It provides a powerful and flexible environment for developing applications in a variety of programming languages.        
#######
# Install dependencies
sudo apt install -y wget gpg apt-transport-https software-properties-common
# Import Microsoft GPG key
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -o root -g root -m 644 packages.microsoft.gpg /usr/share/keyrings/
rm packages.microsoft.gpg
# Add the VS Code repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/packages.microsoft.gpg] \
https://packages.microsoft.com/repos/code stable main" | \
sudo tee /etc/apt/sources.list.d/vscode.list
# Update package list and install
sudo apt update
sudo apt install -y code

################
# 8 - ports info
################
echo "
--Ports info--
# Microk8s Dashboard: https://localhost:10443
# Ollama: http://localhost:11434 - k -n ollama port-forward service/ollama 11434:80
# Ollama API: http://localhost:11434/api/generate
# Ollama Dashboard: http://localhost:11434/ollama
# PGVector: psql - k -n pgvector port-forward service/pgvector 15432:5432 &
# Dapr Dashboard: http://localhost:9999
# Flask user web: http://localhost:5000/ - k -n agents port-forward service/user-web-dapr 5000:80
# Optional: Tilt : http://localhost:10350 
# ##Monitoring##
# Zipkin tracing tool: http://localhost:9411 # see https://docs.dapr.io/operations/observability/tracing/zipkin/
#                                             - k -n default port-forward service/dapr-dev-zipkin 9411:9411 &
# Prometheus: http://localhost:9090 - k port-forward svc/dapr-prom-prometheus-server 9090:80 -n dapr-monitoring &
# Prometheus Alertmanager: http://localhost:9093 - k port-forward svc/dapr-prom-alertmanager 9093:9093 -n dapr-monitoring &
# Grafana: http://localhost:8080 - kubectl port-forward svc/grafana 8080:80 -n dapr-monitoring &
--Ports info--
"