#!/bin/bash 
# set -e
# set -x

#################################
# 0 - SSH key
#################################
# # set FQDN  <- var.ec2_vm_name+var.ec2_fqdn
# ssh RSA public from selected users <-- ec2_user_public_rsa
echo "${var.ec2_user_public_rsa}" >> /home/ubuntu/.ssh/authorized_keys

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
# Download the latest binary
curl -LO "https://dl.k8s.io/release/$(curl -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
# Install it
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
# Verify
kubectl version --client

## 2.3 - Install git
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
sudo microk8s enable dns dashboard storage registry rbac
# kubectl alias k
# aliases in Ubuntu WSL2
echo "# microk8s alias" >> ~/.bashrc
echo "alias k="sudo microk8s kubectl"" >> ~/.bashrc
# execute the bashrc to get the alias working
source  ~/.bashrc
k get nodes -o wide
# return to home directory
cd ~
# make microk8s credentials available
mkdir .kube
sudo cp -p /var/snap/microk8s/current/credentials/client.config .kube/config
sudo chown $USER:microk8s .kube/config
# This command starts a proxy to the Kubernetes Dashboard UI in the background
# it will be available at https://127.0.0.1:10443
sudo microk8s dashboard-proxy &
# Because we enabled rbac in the microk8s cluster, we need to create a service account and cluster role binding for the microk8s dashboard
k create serviceaccount kubernetes-admin-dashboard -n kube-system --dry-run=client -o yaml > sa-kubernetes-admin-dashboard.yaml
k apply-f ./sa-kubernetes-admin-dashboard.yaml
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
if [ `cat /proc/cpuinfo | grep -i "model name" | uniq | grep -i Intel` ] || [ `cat /proc/cpuinfo | grep -i "model name" | uniq | grep -i AMD` ]
  then
    echo "Detected Intel or AMD architecture"
    wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_amd64.tar.gz
    tar -xvzf dapr_linux_amd64.tar.gz
elif [ `cat /proc/cpuinfo | grep -i "model name" | uniq | grep -i ARM` ] 
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
k get pods -n dapr-system
k get pods -n default
# Get status of Dapr services from Kubernetes
dapr status -k 
#Dapr provides a dashboard to monitor and interact with the services running in the cluster. To access the dashboard, run:
dapr dashboard -k -p 9999 &

# ########################################
# # 5 - Install mandatory k8s services
# ########################################

# ## 5.1 - Install Ollama arm/Intel/AMD architecture - Preload Encodding: all-minilm & LLM: llama3.2:1b
# ########
# cd ~/homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/ollama/deploy
# # Ollama is a platform for running and sharing large language models (LLMs) locally.
# # It provides a simple command-line interface (CLI) for running LLMs and a web-based UI for managing and sharing models.
# # Ollama is designed to be easy to use and provides a variety of pre-trained models that can be run locally.
# k apply -f namespace.yaml
# k apply -f deployment.yaml
# k apply -f service.yaml
# # Port forwarding to check the http status of Ollama locally or from broser
# kubectl -n ollama port-forward service/ollama 11434:80 &
# k get pod -n ollama
# # Test the Ollama API locally
# # k -n ollama exec -it pod/ollama-59476b6f4c-rmjkz -- sh
# curl http://localhost:11434/api/generate -d '{
#   "model": "llama3.2:1b",
#   "prompt": "What is Kubernetes?",
#   "stream": false,
#   "raw": true
#   }'

# ## 5.2 - Install Timescale DB with pgvector extension and vectorizer for LLM RAG
# ########
# cd ~/homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/timescaleDB/deploy
# k  apply -f namespace.yaml
# k  apply -f data-pv.yaml
# k  apply -f data-pvc.yaml
# k  apply -f secret-pgvector.yaml
# # vectorizer to ollama connection config is done with k8s DNS no Dapr naming - to check with Dapr naming app_id='ollama-llm.ollama' 
# # post http://localhost:3500/v1.0/invoke/ollama-llm.ollama/method/chat
# k  apply -f deployment.yaml
# k  apply -f service.yaml
# # be able to connect to postgres from Ubuntu 22.04 locally
# kubectl -n pgvector port-forward service/pgvector 15432:5432 &

# ##############################################
# # 6- Install dapr microservices agents in K8s
# ##############################################
# # microk8s kubectl get pods -n container-registry
# # docker tag myapp:latest localhost:32000/myapp:latest
# # docker push localhost:32000/myapp:latest
# # or
# # microk8s.docker build -t localhost:32000/myapp:latest .
# # microk8s.docker push localhost:32000/myapp:latest

# ## 6.1 - psql database
# ##### 
# kubectl -n pgvector port-forward service/pgvector 15432:5432  &
# # psql password
# echo "localhost:15432:postgres:postgres:pgvector" > ~/.pgpass
# chmod 600 ~/.pgpass
# ## NOTE
# ## This password was created in deployment.yaml & secret-pgvector.yaml
# ## in  ./homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/timescaleDB/deploy

# ## 6.2 - Injection Agent Web Dapr
# ########
# # create database table & create the vectorized table
# cd ~/homelab-2-prod-ai-golden-path/3-dapr-microservices-agents/2-injection-agent-web-dapr
# psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-table.sql
# psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-vectorized-table.sql
# # create local registry image -  build the image with microk8s docker
# microk8s.docker build -t localhost:32000/injection-agent-web-dapr:latest .
# # push the image to the local registry
# microk8s.docker push localhost:32000/injection-agent-web-dapr:latest    
# # deploy the application into mikrok8s - create Dev environment
# k apply -f ./k8s/overlays/dev/output_dev.yaml

# ## 6.3 - User Web Dapr Agent
# ########
# # create database table & create the vectorized table
# cd ~/homelab-2-prod-ai-golden-path/3-dapr-microservices-agents/2-injection-agent-web-dapr/sql
# psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-table.sql
# psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-vectorized-table.sql
# # create local registry image -  build the image with microk8s docker
# microk8s.docker build -t localhost:32000/user-web-dapr:latest .
# # push the image to the local registry
# microk8s.docker push localhost:32000/user-web-dapr:latest    
# # deploy the application into mikrok8s - create Dev environment
# k apply -f ./k8s/overlays/dev/output_dev.yaml

#####################################
# 7 - Optional tools and utilities
#####################################

## 7.1 - Opentofu
# Opentofu is an open-source alternative to Terraform, a popular infrastructure as code (IaC) tool.
# Opentofu is designed to be compatible with Terraform configurations and provides a similar command-line interface
######
# Add the OpenTofu APT repo
curl -fsSL https://pkgs.opentofu.org/opentofu-opentofu/gpg.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/opentofu.gpg > /dev/null
echo "deb [signed-by=/etc/apt/trusted.gpg.d/opentofu.gpg] https://pkgs.opentofu.org/opentofu-opentofu/deb/ all main" | \
  sudo tee /etc/apt/sources.list.d/opentofu.list
# Install OpenTofu
sudo apt update
sudo apt-get install -y opentofu
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
# Add Tilt’s APT repo
curl -fsSL https://repo.tilt.dev/apt.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/tilt-archive.gpg
echo "deb [signed-by=/etc/apt/trusted.gpg.d/tilt-archive.gpg] https://repo.tilt.dev/apt stable main" | sudo tee /etc/apt/sources.list.d/tilt.list
# Install Tilt
sudo apt update
sudo apt-get install -y tilt
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
--Ports info--
"