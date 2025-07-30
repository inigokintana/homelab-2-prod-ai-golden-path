As a platform engineer, IaC (Infrastructure as Code) and properly selected/curated OSS are key principles in order to easily rebuild the selected golden path from homelab into whatever PROD environment can be.

We are providing:

- **WSL2 Local**: steps to create WSL2 VM and shell script to create everything inside WSL2 Ubuntu 22.04.
- **AWS**: Opentofu code to provisión a VM on AWS and shell script to recreate everything inside Ubuntu 22.04 VM.
- **OVH**:  Opentofu code to provisión a VM on OVH and shell script to recreate everything inside Ubuntu 22.04 VM.. Europe is having geopolitical trouble with IT dominance from non European companies.
- **Hetzner**:  Opentofu code to provisión a VM on Hetzner and shell script to recreate everything inside Ubuntu 22.04 VM.. Europe is having geopolitical trouble with IT dominance from non European companies.


**Important NOTICE about IaC**: shell script does not properly manage the state so it is very basic IaC.  OpenTofu, on the other hand, is fully compliant IaC as it is built with State tracking, Idempotence (safe to re-run), Dependency graph, Rollback support, Plan before apply and is Modular & composable. Please, if you go to PROD consider migrating some steps of the shell script into OpenTofu, for example:
- Step 4 install Dapr with Helm with [OpenTofu Helm provider](https://search.opentofu.org/provider/opentofu/helm/latest)
- All the kubectl apply commands in steps 5 and 6, install them with [OpenTofu Kubectl Provider](https://search.opentofu.org/provider/opentofu/kubernetes/v2.0.0)


**Shell script content:**
- Updates the package lists 
- Install mandatory tools like docker, kubectl and git and clone the repoSnap.
- Installs MicroK8s  
- Install Dapr
- Install mandatory k8s services for this POC - Ollama, PostgreSQL, pg AI
- Install dapr microservices agents in K8s:data ingestor with scraper and Flask user-web
- Install optional tools: Opentofu, Kustomize and Visual Studio Code

Now, you can **go into any subfolder** of your convenience. Happy installation!!!