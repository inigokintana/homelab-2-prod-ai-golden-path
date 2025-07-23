# How to install microK8S in Windows WSL2 Ubuntu or any Ubuntu
TOC
- [How to install microK8S in Windows WSL2 Ubuntu](#how-to-install-microk8s-in-windows-wsl2-ubuntu)
  - [1 - Install WSL2 & microK8s install](#1---install-wsl2--microk8s-install)
    - [1.1 - In case you are behind company proxy](#11---in-case-you-are-behind-company-proxy)
    - [1.2 - Checking everything is right](#12---checking-everything-is-right)
    - [1.3 - Microk8s web dashboard proxy](#13---microk8s-web-dashboard-proxy)
    - [1.4 - Microk8s web dashboard using service NodePort](#14---microk8s-web-dashboard-using-service-nodeport)
    - [1.5 - Linux alias](#15---linux-alias)
  - [2 - Troubleshooting](#2---troubleshooting)

## 1 - Install WSL2 & microK8s install
Follow steps in the link [WSL2 install](https://microk8s.io/docs/install-wsl2)

### 1.1 - In case you are behind company proxy
```
wsl --update --web-download 
wsl -l -v
wsl --install -d Ubuntu-22.04
```

### 1.2 - Checking everything is right:
````
wsl 
# update ubuntu
sudo apt-get update -y
sudo apt-get upgrade -y           
sudo microk8s status --wait-ready
  microk8s is running

sudo microk8s kubectl version
  Client Version: v1.32.2
  Kustomize Version: v5.5.0
  Server Version: v1.32.2
 
````

### 1.3 - Microk8s web dashboard proxy:
````
kubectl describe secret -n kube-system microk8s-dashboard-token

sudo microk8s dashboard-proxy &
````
- This last command starts a proxy to the Kubernetes Dashboard UI and it will be available at https://127.0.0.1:10443
- Launch it as a background process with <span style="color: red;">&</span> in order to regain console foreground control
- Use the token got above to log into Dashboard
### 1.4 - Microk8s web dashboard using service NodePort:
Alternatively, if you do not want to use the proxy service above, you can convert dashboard service from clusterip service into nodeport service. For example:
````yaml
sudo microk8s kubectl edit  svc/kubernetes-dashboard -n kube-system
  type: NodePort
  nodePort: 30080

sudo microk8s kubectl describe svc/kubernetes-dashboard -n kube-system
  Name:                     kubernetes-dashboard
  Namespace:                kube-system
  Labels:                   k8s-app=kubernetes-dashboard
  Annotations:              <none>
  Selector:                 k8s-app=kubernetes-dashboard
  # check NodePort type
  Type:                     NodePort
  IP Family Policy:         SingleStack
  IP Families:              IPv4
  IP:                       10.152.183.21
  IPs:                      10.152.183.21
  Port:                     <unset>  443/TCP
  TargetPort:               8443/TCP
  # check NodePort port
  NodePort:                 <unset>  30080/TCP
  Endpoints:                10.1.101.69:8443
  Session Affinity:         None
  External Traffic Policy:  Cluster
  Internal Traffic Policy:  Cluster
  Events:                   <none>

# to get the server IP
sudo microk8s kubectl get nodes -o wide
  NAME              STATUS   ROLES    AGE   VERSION   INTERNAL-IP      EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION                       CONTAINER-RUNTIME
  desktop-41ahscb   Ready    <none>   14h   v1.32.2   172.23.103.249   <none>        Ubuntu 22.04.5 LTS   5.15.167.4-microsoft-standard-WSL2   containerd://1.6.36
````
Dashboard should be available in your **https://VM-ip:30080 port**, in our example https://172.23.103.249:30080

### 1.5 - Linux alias:
Optionally, you can add the following alias into .bashrc to ease command line interaction:
````
#aliases in Ubuntu WSL2
alias smk="sudo microk8s kubectl"
````

## 1.6 - Install Dapr with agents in Intel architecture
#### 1. **Install Dapr CLI**:
   To install the Dapr CLI, which will help manage Dapr deployments, follow the steps below:
   
   **For Linux/macOS**:
   ```bash
    wget https://github.com/dapr/cli/releases/download/v1.15.0/dapr_linux_amd64.tar.gz
    tar -xvzf dapr_linux_amd64.tar.gz
    sudo mv dapr /usr/local/bin/dapr
   ```
#### 2. **Initialize Dapr on MicroK8s**:
   Now that you have the Dapr CLI installed, you can initialize Dapr on your MicroK8s cluster.

   Run the following command to install Dapr in your MicroK8s Kubernetes cluster:
   ```bash
   dapr init --kubernetes --dev
   ```
   ⌛  Making the jump to hyperspace...
ℹ️  Note: To install Dapr using Helm, see here: https://docs.dapr.io/getting-started/install-dapr-kubernetes/#install-with-helm-advanced

ℹ️  Container images will be pulled from Docker Hub
✅  Deploying the Dapr control plane with latest version to your cluster...
✅  Deploying the Dapr dashboard with latest version to your cluster...
✅  Deploying the Dapr Redis with 17.14.5 version to your cluster...
✅  Deploying the Dapr Zipkin with latest version to your cluster...
ℹ️  Applying "statestore" component to Kubernetes "default" namespace.
ℹ️  Applying "pubsub" component to Kubernetes "default" namespace.
ℹ️  Applying "appconfig" zipkin configuration to Kubernetes "default" namespace.
✅  Success! Dapr has been installed to namespace dapr-system. To verify, run `dapr status -k' in your terminal. To get started, go here: https://docs.dapr.io/getting-started

#### 3. **Verify Dapr Installation**:
   After installation, you can verify that Dapr is running correctly using the following commands:
   
   Check the status of the Dapr pods:
   ```bash
   kubectl get pods -n dapr-system
   kubectl get pods -n default  
   ```

   Ensure that the Dapr control plane is up and running. The pods should look similar to:
   - `dapr-operator`
   - `dapr-placement`
   - `dapr-sidecar-injector`
   
   If everything is running smoothly, you’ll see the corresponding pods in the `Running` state.

#### 4. **Install AI Agent Components (Optional)**

See https://www.cncf.io/blog/2025/03/12/announcing-dapr-ai-agents/
See https://github.com/dapr/dapr-agents/blob/main/quickstarts/README.md
https://github.com/dapr/dapr-agents/tree/main/quickstarts/01-hello-world
see https://platform.openai.com/settings/organization/api-keys 5$ spents

Errors with dapr instalation

   If you are looking to use Dapr with **AI agents**, you might need to install specific AI components or integrate libraries such as **TensorFlow**, **PyTorch**, or **OpenAI GPT models**. However, Dapr itself doesn’t directly handle AI agents; rather, you can leverage Dapr's capabilities (like state management, pub/sub, and bindings) to interact with AI models running within your Kubernetes cluster.

   You would typically:
   - Deploy AI models as containers in your Kubernetes cluster.
   - Use Dapr’s pub/sub or state management to communicate with these AI services.
   
   For example, you could use **Dapr bindings** to connect to AI models or invoke services that leverage AI models via HTTP/gRPC.

#### 5. **Deploy an Example Dapr Application**:
   To test your Dapr setup, deploy a sample application that integrates with Dapr's capabilities, such as state management or pub/sub. Here's a simple example using a basic pub/sub model.

   First, create a `pubsub.yaml` file:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: pubsub-app
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: pubsub-app
     template:
       metadata:
         labels:
           app: pubsub-app
       spec:
         containers:
         - name: pubsub-app
           image: daprio/examples:pubsub
           env:
             - name: DAPR_HTTP_PORT
               value: "3500"
           ports:
             - containerPort: 3500
   ```

   Apply the deployment:
   ```bash
   kubectl apply -f pubsub.yaml
   ```

   Then, to check the logs and see if the app is running properly:
   ```bash
   kubectl logs -f <pod-name> -n default
   ```

#### 6. **Access Dapr Dashboard**:
   Dapr provides a dashboard to monitor and interact with the services running in the cluster. To access the dashboard, run:
   ```bash
   dapr dashboard -k -p 9999
   ```

   This will open the Dapr dashboard in your web browser, where you can view the state of your applications and interact with them.

   See http://localhost:9999/controlplane

## 6.1 - Zipkin trace analysis
  - k get services
  - kubectl port-forward svc/dapr-dev-zipkin 9411:9411 &
  - http://localhost:9411/zipkin/

## 6.2 - Redis access
  - k get secrects
  - k get secret dapr-dev-redis -o yaml
 
  Previous command retuns the redis-password encripted in base64 so we need to decrypt:
  - echo "xxx" | base64 -d 
  - k get pods
  - k exec -it pod/dapr-dev-redis-master-0 -- sh
  - $ redis-cli -a  "password"
  - 127.0.0.1:6379> keys *
    1) "nodeapp||order"
  - hgetall "nodeapp||order"
      1) "data"
      2) "{\"orderId\":16301}"
      3) "version"
      4) "16302"

## 6.3 - OpenTelemetry

See https://docs.dapr.io/operations/observability/tracing/otel-collector/open-telemetry-collector/

## 1.7 - Install Ollama choosing a small model in Intel architecture
cd 8-BigData-AI/Ollama
k apply namespace.yaml
k apply deployment.yaml
k apply service.yaml
kubectl -n ollama port-forward service/ollama 11434:80 &
k get pod -n ollama
k -n ollama exec -it pod/ollama-59476b6f4c-rmjkz -- sh
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "What is Kubernetes?",
  "stream": false,
  "raw": true
  }'


### 1.7.1 postgres pgvector
cd 8-BigData-AI/Ollama/pgVector
k apply -f namespace.yaml
k -n pgvector create secret generic pgvectorconfig --from-literal POSTGRES_USER=postgres --from-literal POSTGRES_PASSWORD=pgvector --from-literal POSTGRES_DB=pgvector --dry-run=client -o yaml > secret-pgvector.yaml
k apply -f secret-pgvector.yaml
k apply -f deployment.yaml
k aply -f service.yaml

k -n pgvector exec -it pod/pgvector-5bd69f6c84-b85pg -- sh

psql -U postgres -d pgvector -W

pgvector=# select * from pg_extension;
  oid  | extname | extowner | extnamespace | extrelocatable | extversion | extconfig | extcondition 
-------+---------+----------+--------------+----------------+------------+-----------+--------------
 13569 | plpgsql |       10 |           11 | f              | 1.0        |           | 
(1 row)

pgvector=# create extension vector;
CREATE EXTENSION
pgvector=# select * from pg_extension;
  oid  | extname | extowner | extnamespace | extrelocatable | extversion | extconfig | extcondition 
-------+---------+----------+--------------+----------------+------------+-----------+--------------
 13569 | plpgsql |       10 |           11 | f              | 1.0        |           | 
 16389 | vector  |       10 |         2200 | t              | 0.8.0      |           | 
(2 rows)

k -n pgvector port-forward service/pgvector 15432:5432 &
psql -U postgres -d pgvector -h localhost -p 15432 -W  < works>

cd microservice-k8s-flask/8-BigData-AI/pgDemo$ ls

for i in `ls *.dat`
do
k cp $i pgvector/pgvector-5bd69f6c84-b85pg:/tmp/
done
k cp restore.sql pgvector/pgvector-5bd69f6c84-b85pg:/tmp/

Connect to pod - change file permissions 666 and execute psql -U postgres -d pgvector -h localhost -p 15432 -W <  restore.sql


## 1.8 - Install Argo CD

## 2 -  Microk8s troubleshooting

error: timed out waiting for the condition on deployments/kubernetes-dashboard

https://microk8s.io/docs/troubleshooting

Solution: use proxy free connection/wifi during microk8s install
