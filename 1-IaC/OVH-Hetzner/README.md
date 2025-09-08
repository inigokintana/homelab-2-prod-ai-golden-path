# 0 - Context
Europe is having geopolitical trouble with IT dominance from non European companies.

This is why, in this section, we try to install all these OSS projects in an European public Cloud provider as OVH or Hetzner using OpenTofu.

OpenTofu has also an OpenNebula, helm and kubectl providers. Openebula & Virt8era is another Europe sovereing cloud initiative, see [link1](https://opennebula.io/innovation/virt8ra/) and [link2](https://www.youtube.com/watch?v=PGpCeoqtHWg).

Finally, we pick Hetzner Cloud.

# 1 - Objective

We want to have the cheapest possible Hetzner instance with root 22.04 using OpenTofu (a fork of Terraform) to provision the needed cloud resources with IaC(infrastructure-as-code).

Unlike Kind or minikube, **mikroK8s** is intended for production workloads as an alternative to Openshifts. Of course you can go into cloud k8s with EKS, AKS or GKE.  MicroK8s simplifies developer work and can be run in a cluster:
  - [microk8s root 22.04 install](https://help.clouding.io/hc/en-us/articles/13572430913180-How-to-Setup-Lightweight-Kubernetes-with-MicroK8s-and-Snap-on-root-22-04)
  - [microk8s cluster](https://microk8s.io/docs/Hetzner-user-guide)
  - [cluster upgrade](https://microk8s.io/docs/upgrade-cluster)

Additionally, we will have to execute previously mentioned shell script to configure the VM with all the required services inside VM.
 
# 2. System requirements
- OLLAMA's LLM inside requires quite a lot of run despite selecting being a SLM (Small Language Model). 
- We will need a shared server cax21 (4 vCPU Ampere, 8 GB RAM) VM

# 3 - Opentofu - IaC
## 3.1 - Hetzner account & client & key pair requirements
You must have an Hetzner account and Hetzner API credentials configured.
- Activate Hetzner account 
- Load ssh pub key in OpenSSHformat in Hetzner - This ssh key will be included in the server
- Activate APY token, see [link](https://docs.hetzner.com/cloud/api/getting-started/generating-api-token/)
- Unlike in other providers, in Hetzner root user is activate inside root and userdata.sh will be executed 1st with root user.
- Change root user later, see [link](https://community.hetzner.com/tutorials/howto-initial-setup-root)


## 3.2 - Install OpenTofu in your environment:
```
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
sudo apt-get update
sudo apt-get install -y tofu
# Verify
tofu version
```
## 3.3 - Execute Opentofu:
1. **Initialize OpenTofu**: In your terminal, navigate to the directory where the `.tf` file is located and run:

   ```bash
   cd opentofu
   tofu init
   ```

2. **Apply the Configuration**: To create the resources, run:

   ```bash
   tofu apply
    var.hcloud_token
        Enter a value: <- put in here the token API activated in step 3.1
   ```

   Confirm the action when prompted.

   Take care of instance private and public IPs in the output.

   Remember to destroy resources:
   ```bash
   tofu destroy
    var.hcloud_token
        Enter a value: <- put in here the token API activated in step 3.1
   ```

3. **Access the Hetzner Instance**: After the Hetzner instance is provisioned, you can connect with browser from Hetzner console or with SSH:

   As soon as the server is created, Hetzner will write to your e-mail providing the root password. You will be forced to change it after 1st login. Do it as fast as possible.
   
   ```bash
   ssh  root@<instance_public_ip>

   # microk8s dashboard-proxy port 10443
   # use ssh tunnel: ssh -L 10443:localhost:10443 root@instance_public_i

   # Ollama and the LLM&SLM inside port 11434
   # use ssh tunnel: ssh  -L 11434:localhost:11434 root@instance_public_ip
   # port forward must be running inside Hetzner: k -n ollama port-forward service/ollama 11434:80 &

   # Postgres port for TimescaleDB and Vectorizer port 15432
   # use ssh tunnel: ssh  -L 15432:localhost:15432 root@instance_public_ip
   # port forward must be running inside Hetzner: k -n pgvector port-forward service/pgvector 15432:5432 &

   # Dapr dashboard port 9999
   # use ssh tunnel: ssh  -L 9999:localhost:9999 root@instance_public_ip

   # Flask user web app port 5000
   # use ssh tunnel: ssh  -L 5000:localhost:5000 root@instance_public_ip
   # port forward must be running inside Hetzner: k -n agents port-forward service/user-web-dapr 5000:80 &

   # MCP: http://localhost:8001 - k -n agents port-forward service/mcp-svc 8001:8001 & 
   # use ssh tunnel: ssh -i aipoc.pem  -L 8001:localhost:8001 root@instance_public_ip

   # Tilt port 10350
   # use ssh tunnel: ssh  -L 10350:localhost:10350 root@instance_public_ip

   # Zipkin port 9411 :
   # use ssh tunnel: ssh  -L 9411:localhost:9411 root@instance_public_ip
   #port forward must be running inside Hetzner: k -n default port-forward service/dapr-dev-zipkin 9411:9411 &

   # Prometheus port 9090 :
   # use ssh tunnel: ssh  -L 9090:localhost:9090 root@instance_public_ip
   # port forward must be running inside Hetzner: k port-forward svc/dapr-prom-prometheus-server 9090:80 -n dapr-monitoring &
   
   
   # Prometheus Alertmanager 9093
   # use ssh tunnel: ssh  -L 9093:localhost:9093 root@instance_public_ip
   # port forward must be running inside Hetzner: k port-forward svc/dapr-prom-alertmanager 9093:9093 -n dapr-monitoring &

   # Grafana 8080
   # use ssh tunnel: ssh  -L 8080:localhost:8080 root@instance_public_ip
   # port forward must be running inside Hetzner: k port-forward svc/grafana 8080:80 -n dapr-monitoring &

   # All together in one ssh tunnel
   
   ssh \
   -L 15432:localhost:15432 \
   -L 9999:localhost:9999 \
   -L 5000:localhost:5000 \
   -L 8001:localhost:8001 \
   -L 10350:localhost:10350 \
   -L 9411:localhost:9411 \
   -L 9090:localhost:9090 \
   -L 9093:localhost:9093 \
   -L 8080:localhost:8080 \
   root@instance_public_ip

   ```

## 3.4 - Check userdata shell script output and re-execute partially if needed

While the Hetzner instance is been initialized or after (all status checks are passed), you can verify what the userdata script did in the log file located at "tail -f /var/log/cloud-init-output.log".

If something fails, you may re-execute it partially or totally if needed, userdata.sh file is in this git repo but you can also see it inside Hetzner instance with "sudo cat /var/lib/cloud/instance/user-data.txt"

# 4 - Breakdown of the Configuration chosen in Opentofu

1. **Variables**: gettin router public IP
2. **Hetzner Provider**: Specifies the Hetzner region where you want to provision your resources.
3. **Resources: getting data**: getting vpc and key pair data.
4. **Resources: provisioning resources**
   - **Hetzner Instance**: This resource defines the Hetzner instance:
      - **AMI ID**: The image ID for root 22.04. The provided `ami-0586af70ffaea9a74` is for the `eu-south-2 (Spain)` region. You should replace it with the corresponding AMI for your Hetzner region.
      - **Instance Type**: It uses "t4g.xlarge" # (4 vCPU -16 GB RAM). You can adjust this as per your needs.
      - **Key pair**: SSH key for accessing the Hetzner instance.
   - **Security Group**: This security group allows:
      - SSH (port 22)
      - Microk8s dashboard-proxy (port 10443)- you could comment this and use ssh tunnel: ssh -L 10443:localhost:10443 root@instance_public_ip
      - Ollama and the LLM&SLM inside (port 11434) -  you could comment this and use ssh tunnel: ssh -L 11434:localhost:11434 root@instance_public_ip
      - Postgres port for TimescaleDB and Vectorizer (port 15432) you could comment this and use ssh tunnel: ssh -L 15432:localhost:1154321434 root@instance_public_ip
      - Dapr dashboard (port 9999)
      - you could comment this and use ssh tunnel: ssh -L 9999:localhost:9999 root@instance_public_ip
      - Flask user web app (port 5000) - you could comment this and use ssh tunnel: ssh -L 5000:localhost:5000 root@instance_public_ip
      - Tilt (port 10350) - you could comment this and use ssh tunnel: ssh -L 10350:localhost:10350 root@instance_public_ip
   - **User Data**: This section contains a bash script that:
      - 1) Updates the package lists 
      - 2) Install mandatory tools like docker, kubectl and git and clone the repoSnap.
      - 3) Installs MicroK8s  
      - 4) Install Dapr
      - 5) Install mandatory k8s services for this POC - Ollama, PostgreSQL, pg AI
      - 6) Install dapr microservices agents in K8s:data ingestor with scraper and Flask user-web
      - 7) Install optional tools: Opentofu, Kustomize and Visual Studio Code

5. **Outputs**: The public and private IP addresses of the instance are outputted after the instance is created, which can be useful for connecting to the instance or accessing the MicroK8s dashboard.


## 5 - Play with the config:

- As mentioned before, adapt Opentofu script to include shell scripts steps 4), 5) and 6) to use kubectl & helm providers.

**Important NOTICE about IaC**: shell script does not properly manage the state so it is very basic IaC.  OpenTofu, on the other hand, is fully compliant IaC as it is built with State tracking, Idempotence (safe to re-run), Dependency graph, Rollback support, Plan before apply and is Modular & composable. Please, if you go to PROD consider migrating some steps of the shell script into OpenTofu, for example:
- Step 4 install Dapr with Helm with [OpenTofu Helm provider](https://search.opentofu.org/provider/opentofu/helm/latest)
- All the kubectl apply commands in steps 5 and 6, install them with [OpenTofu Kubectl Provider](https://search.opentofu.org/provider/opentofu/kubernetes/v2.0.0)


# 6 - Final notes
- **Security**: Ensure your security group is configured to allow only trusted IPs, especially for production environments.
- **AMI ID**: Always verify the ubuntu 22.04 AMI ID for your region in the Hetzner console. You can find the most recent AMIs via Hetzner Marketplace or the Hetzner console.
- **Instance Type**: Adjust the instance type to suit your needs, especially if you require more resources for Kubernetes workloads.

This configuration provides a simple and quick setup for provisioning an Hetzner instance with Ubuntu 22.04 and installing MicroK8s automatically.