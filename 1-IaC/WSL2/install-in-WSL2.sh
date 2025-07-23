#!/bin/bash 
# set -e
# set -x

###################
# 1 - update ubuntu
###################
sudo apt-get update -y
sudo apt-get upgrade -y

######################
# 2 - Install microk8s
######################
sudo snap version
sudo snap list
sudo snap install microk8s --classic --channel=1.32/stable
sudo microk8s status --wait-ready
# microk8s add-on offer easy way to enable dns dashboard storage 
# registry -> (LLM images can be heavy)
# rbac -> (Role-based access control) needed by dapr and argoCD
sudo microk8s enable dns dashboard storage registry rbac
# kubectl alias k
# aliases in Ubuntu WSL2
echo "# microk8s alias" >> /home/ubuntu/.bashrc
echo "alias k="sudo microk8s kubectl"" >> /home/ubuntu/.bashrc
# execute the bashrc to get the alias working
source /home/ubuntu/.bashrc
k get nodes -o wide
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
# 3 - Install Dapr in WSL2
##########################
## Install Dapr arm architecture - change version file when needed
# Dapr is a portable, event-driven runtime that makes it easy for developers to build resilient, microservices-based applications.
# It provides APIs that simplify the development of microservices by abstracting away the complexities of distributed systems.
# Dapr is designed to work with any programming language and can be deployed on any cloud or on-premises environment.
# Dapr is a set of building blocks for microservices, providing capabilities such as service invocation, state management, pub/sub messaging, and more.
# Dapr is designed to be language-agnostic and can be used with any programming language that supports HTTP or gRPC.

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
# return to home directory
cd 
# make microk8s credentials available
mkdir .kube
sudo cp -p /var/snap/microk8s/current/credentials/client.config .kube/config
sudo chown ubuntu:microk8s .kube/config
# Install dapr in k8s with redis and zipkin 
dapr init --kubernetes --dev
k get pods -n dapr-system
k get pods -n default
# Get status of Dapr services from Kubernetes
dapr status -k 

#Dapr provides a dashboard to monitor and interact with the services running in the cluster. To access the dashboard, run:
dapr dashboard -k -p 9999 &

################################################
# 4 - Install git and clone the repo
################################################
# Deploy git and clone the repo
sudo apt-get install git -y
git clone https://github.com/inigokintana/homelab-2-prod-ai-golden-path.git


########################################
# 5 - Install mandatory k8s services
########################################
## 5.1 - Install Ollama arm/Intel/AMD architecture - Preload Encodding: all-minilm & LLM: llama3.2:1b
########
cd ./homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/ollama/deploy
# Ollama is a platform for running and sharing large language models (LLMs) locally.
# It provides a simple command-line interface (CLI) for running LLMs and a web-based UI for managing and sharing models.
# Ollama is designed to be easy to use and provides a variety of pre-trained models that can be run locally.
k apply -f namespace.yaml
k apply -f deployment.yaml
k apply -f service.yaml
# Port forwarding to check the http status of Ollama locally or from broser
kubectl -n ollama port-forward service/ollama 11434:80 &
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
cd ./homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/timescaleDB/deploy
k  apply -f namespace.yaml
k  apply -f data-pv.yaml
k  apply -f data-pvc.yaml
k  apply -f secret-pgvector.yaml
# vectorizer to ollama connection config is done with k8s DNS no Dapr naming - to check with Dapr naming app_id='ollama-llm.ollama' 
# post http://localhost:3500/v1.0/invoke/ollama-llm.ollama/method/chat
k  apply -f deployment.yaml
k  apply -f service.yaml
# be able to connect to postgres from Ubuntu 22.04 locally
kubectl -n ollama port-forward service/pgvector 15432:5432 &


##############################################
# 6- Install dapr microservices agents in K8s
##############################################
# microk8s kubectl get pods -n container-registry
# docker tag myapp:latest localhost:32000/myapp:latest
# docker push localhost:32000/myapp:latest
# or
# microk8s.docker build -t localhost:32000/myapp:latest .
# microk8s.docker push localhost:32000/myapp:latest

# psql 
##### *** review when/where is password created
kubectl -n pgvector port-forward service/pgvector 15432:5432  &
# psql password
echo "localhost:15432:postgres:postgres:pgvector" > ~/.pgpass
chmod 600 ~/.pgpass

########################################
# 6.1 - Injection Agent Web Dapr
########################################
# create database table & create the vectorized table
cd ~/homelab-2-prod-ai-golden-path/3-dapr-microservices-agents/2-injection-agent-web-dapr
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-table.sql
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-vectorized-table.sql
# create local registry image -  build the image with microk8s docker
microk8s.docker build -t localhost:32000/injection-agent-web-dapr:latest .
# push the image to the local registry
microk8s.docker push localhost:32000/injection-agent-web-dapr:latest    
# deploy the application into mikrok8s - create Dev environment
k apply -f ./k8s/overlays/dev/output_dev.yaml

########################################
# 6.2 - User Web Dapr Agent
########################################
# create database table & create the vectorized table
cd ~/homelab-2-prod-ai-golden-path/3-dapr-microservices-agents/2-injection-agent-web-dapr/sql
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-table.sql
psql -U postgres -d postgres -h localhost -p 15432 < .sql/create-vectorized-table.sql
# create local registry image -  build the image with microk8s docker
microk8s.docker build -t localhost:32000/user-web-dapr:latest .
# push the image to the local registry
microk8s.docker push localhost:32000/user-web-dapr:latest    
# deploy the application into mikrok8s - create Dev environment
k apply -f ./k8s/overlays/dev/output_dev.yaml
