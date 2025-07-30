# 1 - Objective

We want to have the cheapest possible EC2 instance with Ubuntu 22.04 using OpenTofu (a fork of Terraform) to provision the needed cloud resources with IaC(infrastructure-as-code).

Unlike Kind or minikube, **mikroK8s** is intended for production workloads as an alternative to Openshifts. Of course you can go into cloud k8s with EKS, AKS or GKE.  MicroK8s simplifies developer work and can be run in a cluster:
  - [microk8s Ubuntu 22.04 install](https://help.clouding.io/hc/en-us/articles/13572430913180-How-to-Setup-Lightweight-Kubernetes-with-MicroK8s-and-Snap-on-Ubuntu-22-04)
  - [microk8s cluster](https://microk8s.io/docs/aws-user-guide)
  - [cluster upgrade](https://microk8s.io/docs/upgrade-cluster)

Additionally, we will have to execute previously mentioned shell script to configure the VM with all the required services inside VM.
 

# 2. System requirements
- OLLAMA's LLM inside requires quite a lot of run despite selecting being a SLM (Small Language Model). 
- We will need a t4g.large(2 vCPU - 8 GB RAM) or t4g.xlarge(4 vCPU -16 GB RAM) VM

# 3 - Opentofu - IaC
## 3.1 - AWS account & client & key pair requirements
You must have an AWS account and AWS credentials configured.
- Install AWS client, see [link](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Setup AWS client, see [link](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html)
- Create a Key pair if you want to connect via ssh to VM, see [link](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html)
```
cd ~/.ssh

# 1. Create the key pair and save the PEM file 
# - **key-name** must be same in OpenTofu main.tf
# - **tag-specifications** must be same in Opentofu  main.tf
# - **region** at your convenience 
aws ec2 create-key-pair \
    --key-name aipoc \
    --key-type rsa \
    --key-format pem \
    --tag-specifications 'ResourceType=key-pair,Tags=[{Key=Component,Value=opentofu}]' \
    --query "KeyMaterial" \
    --output text > aipoc.pem\
    --region eu-south-2

# 2. Set the permissions of your private key file 
chmod 400 aipoc.pem   

# 3. To just output the public part of a private key: 
openssl rsa -in aipoc.pem -pubout > aipoc.pub

# 4- copy aipoc.pub value into OpenTofu maint.tf variable
cat aipoc.pub
variable "ec2_user_public_rsa" 
```
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
   ```

   Confirm the action when prompted.

   Take care of instance private and public IPs in the output.

3. **Access the EC2 Instance**: After the EC2 instance is provisioned, you can connect with browser from AWS console EC2 or with SSH:

   ```bash
   ssh -i pocai.pem ubuntu@<instance_public_ip>
   ```

   You can also access the MicroK8s dashboard using its public IP and port `16443` (make sure to set up a password if required by MicroK8s).



## 3.4 - Check userdata shell script output and re-execute partially if needed

Once the EC2 instance has been initialized (all status checks are passed), you can verify what the user_data script did in the log file located at /var/log/cloud-init-output.log.

If something fails, you may re-execute it partially or totally if needed



# 4 - Breakdown of the Configuration chosen in Opentofu

1. **AWS Provider**: Specifies the AWS region where you want to provision your resources.
   
2. **Security Group**: This security group allows:
   - SSH (port 22)
   - Kubernetes API port (6443)
   - MicroK8s API port (16443)

3. **EC2 Instance**: This resource defines the EC2 instance:
   - **AMI ID**: The image ID for Ubuntu 22.04. The provided `ami-0dba2cb6798c5dbb7` is for the `us-east-1` region. You should replace it with the corresponding AMI for your AWS region.
   - **Instance Type**: It uses `t3.micro`, which is eligible for the AWS Free Tier. You can adjust this as per your needs.
   - **Key Name**: Replace `"your-ssh-key-name"` with the name of your SSH key for accessing the EC2 instance.

4. **User Data**: This section contains a bash script that:
   - Updates the package lists (`apt update`).
   - Installs `snapd` to allow installation of MicroK8s via Snap.
   - Installs MicroK8s with the `--classic` option.
   - Waits for MicroK8s to be ready.
   - Enables MicroK8s' DNS and dashboard services.

5. **Outputs**: The public and private IP addresses of the instance are outputted after the instance is created, which can be useful for connecting to the instance or accessing the MicroK8s dashboard.



### Notes
- **Security**: Ensure your security group is configured to allow only trusted IPs, especially for production environments.
- **AMI ID**: Always verify the Ubuntu 22.04 AMI ID for your region in the AWS console. You can find the most recent AMIs via AWS Marketplace or the EC2 console.
- **Instance Type**: Adjust the instance type to suit your needs, especially if you require more resources for Kubernetes workloads.

This configuration provides a simple and quick setup for provisioning an EC2 instance with Ubuntu 22.04 and installing MicroK8s automatically.


## 6 - Play with the config:

- Open ports
- not for PROD
- kubectl 6 helm
