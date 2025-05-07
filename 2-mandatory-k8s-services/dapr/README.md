DAPR is installed with the shell script provided in 1-IaC

These are the steps:

## Install Dapr arm architecture - change version file when needed
## Install Dapr Intel architecture - change version file when needed

# Dapr is a portable, event-driven runtime that makes it easy for developers to build resilient, microservices-based applications.
# It provides APIs that simplify the development of microservices by abstracting away the complexities of distributed systems.
# Dapr is designed to work with any programming language and can be deployed on any cloud or on-premises environment.
# Dapr is a set of building blocks for microservices, providing capabilities such as service invocation, state management, pub/sub messaging, and more.
# Dapr is designed to be language-agnostic and can be used with any programming language that supports HTTP or gRPC.
wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_arm64.tar.gz
tar -xvzf dapr_linux_arm64.tar.gz
    or
wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_amd64.tar.gz
tar -xvzf dapr_linux_amd64.tar.gz

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