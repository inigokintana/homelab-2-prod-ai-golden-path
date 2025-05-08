#!/bin/bash 
# set -e
# set -x
############################
### wait  network to come up
#URL="api.snapcraft.io"  # snap server api
# The HTTP status code to check for (200 OK)
#SUCCESS_STATUS=200
# Start an infinite loop
# while true; do
#     # Send a GET request to the URL and capture the HTTP status code
#     HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
#     # Check if the status code is 200
#     if [ "$HTTP_STATUS" -eq "$SUCCESS_STATUS" ]; then
#         echo "Request successful! HTTP status code: $HTTP_STATUS"
#         break  # Exit the loop if successful
#     else
#         echo "Request failed with status code: $HTTP_STATUS. Retrying..."
#     fi
#     # Optional: Add a delay before retrying
#     sleep 5
# done
############################
# update ubuntu
sudo apt-get update -y
sudo apt-get upgrade -y
# # set FQDN  <- var.ec2_vm_name+var.ec2_fqdn
# ssh RSA public from selected users <-- ec2_user_public_rsa
echo "${var.ec2_user_public_rsa}" >> /home/ubuntu/.ssh/authorized_keys
sudo snap version
sudo snap list
sudo snap install microk8s --classic --channel=1.32/stable
sudo microk8s status --wait-ready
# microk8s add-on offer easy way to enable dns dashboard storage 
# registry -> (LLM images can be heavy)
# rbac -> (Role-based access control) needed by dapr and argoCD
sudo microk8s enable dns dashboard storage registry rbac
# kubectl alias
#aliases in Ubuntu WSL2
echo "# microk8s alias" >> /home/ubuntu/.bashrc
echo "alias k="sudo microk8s kubectl"" >> /home/ubuntu/.bashrc
# execute the bashrc to get the alias working
source /home/ubuntu/.bashrc
k get nodes -o wide
# This command starts a proxy to the Kubernetes Dashboard UI in the background
# it will be available at https://127.0.0.1:10443
sudo microk8s dashboard-proxy &
# Because we enabled rbac in the cluster, we need to create a service account and cluster role binding for the microk8s dashboard
k create serviceaccount kubernetes-admin-dashboard -n kube-system --dry-run=client -o yaml > sa-kubernetes-admin-dashboard.yaml
k apply-f ./sa-kubernetes-admin-dashboard.yaml
k create clusterrolebinding kubernetes-admin-dashboard --clusterrole=cluster-admin --serviceaccount=kube-system:kubernetes-admin-dashboard -n kube-system --dry-run=client -o yaml > rb-kubernetes-admin-dashboard.yaml
k apply -f ./rb-kubernetes-admin-dashboard.yaml
# Since k 1.18 service account token is not created by default
# To get the token for the service account, run the following command
TOKEN=(k create token kubernetes-admin-dashboard -n kube-system)
echo "k create token kubernetes-admin-dashboard -n kube-system" > token-kubernetes-admin-dashboard.yaml
echo $TOKEN >> token-kubernetes-admin-dashboard.yaml

# To Access to the MicroK8S dashboard from public IP that we have to edit config file.
# kubectl -n kube-system edit service kubernetes-dashboard
# changing ‘ClusterIP’ to ‘NodePort’,
# kubectl get service <service-name> -n <namespace> -o yaml > service.yaml
# sed -i 's/type: ClusterIP/type: NodePort/' service.yaml
# sed  nodePort: 30080 
# kubectl apply -f service.yaml
# Microk8s web dashboard:system microk8s-dashboard-token
# exit

## Install Dapr arm architecture - change version file when needed
# Dapr is a portable, event-driven runtime that makes it easy for developers to build resilient, microservices-based applications.
# It provides APIs that simplify the development of microservices by abstracting away the complexities of distributed systems.
# Dapr is designed to work with any programming language and can be deployed on any cloud or on-premises environment.
# Dapr is a set of building blocks for microservices, providing capabilities such as service invocation, state management, pub/sub messaging, and more.
# Dapr is designed to be language-agnostic and can be used with any programming language that supports HTTP or gRPC.
wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_arm64.tar.gz
tar -xvzf dapr_linux_arm64.tar.gz
sudo mv dapr /usr/local/bin/dapr
cd 
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

# Deploy git and clone the repo
sudo apt-get install git -y
git clone https://github.com/inigokintana/homelab-2-prod-ai-golden-path.git

## Install Ollama arm/Intel/AMD architecture - Preload Encodding: all-minilm & LLM: llama3.2:1b
cd ./homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/ollama/deploy
# Ollama is a platform for running and sharing large language models (LLMs) locally.
# It provides a simple command-line interface (CLI) for running LLMs and a web-based UI for managing and sharing models.
# Ollama is designed to be easy to use and provides a variety of pre-trained models that can be run locally.
k apply -f namespace.yaml
k apply -f deployment.yaml
k apply -f service.yaml
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

# Install Timescale DB with pgvector extension and vectorizer for LLM RAG
cd ./homelab-2-prod-ai-golden-path/2-mandatory-k8s-services/timescaleDB/deploy
k  apply -f namespace.yaml
k  apply -f data-pv.yaml
k  apply -f data-pvc.yaml
k  apply -f secret-pgvector.yaml
# vectorizer to ollama connection config is done with k8s DNS no Dapr naming - to check with Dapr naming app_id='ollama-llm.ollama' 
# post http://localhost:3500/v1.0/invoke/ollama-llm.ollama/method/chat
k  apply -f deployment.yaml
k  apply -f service.yaml
# be able to connect to postgres from Ubuntu 22.04
kubectl -n ollama port-forward service/pgvector 15432:5432 &

# Load data into TimescaleDB with automatic vectorization
# guess-poems with dapr sdk & http - no database use
# guess-films with dapr sdk
# guess-wiki-questions http

# deploy 
# guess-poems with dapr sdk & http - no database use
# guess-films with dapr sdk
# guess-wiki-questions http


# Install ArgoCD arm architecture
# Dapr ArgoCD https://www.diagrid.io/blog/dapr-meets-gitops-a-guide-to-dapr-and-argo-cd
# github argocd https://medium.com/be-tech-with-santander/from-git-to-kubernetes-in-10-minutes-with-argocd-3027a2d5ea62
# kubectl create namespace argocd
# kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
#expose via port server
# kubectl port-forward svc/argocd-server -n argocd 8080:443 &
# login argoCD user admin
# kubectl -n argocd get secret argocd-initial-admin-secret -o=jsonpath='{.data.password}' | base64 -d
# connect from local ssh to port 8888
# ssh -L 8888:127.0.0.1:8080 ubuntu@<ec2-public-ip>
# get the my-app-argo.yaml with wget from github or S3
# github https://github/my-app-argo.yaml
# kubectl apply -f my-app-argo.yaml
# Deploy task flask api with the comand above

# Deploy Dapr with Agent automations using OpenAI - later susbtitute component to Ollama