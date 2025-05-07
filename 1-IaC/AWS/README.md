# 1 - Objective

We want to have the cheapest possible EC2 instance with Ubuntu 22.04 and MicroK8s installed using OpenTofu (a fork of Terraform) to provision the needed cloud resources with IaC(infrastructure-as-code).

Unlike Kind or minikube, **mikroK8s** is intended for production workloads as an alternative to Openshifts. MicroK8s simplifies developer work and can be run in a cluster:
  - [microk8s Ubuntu 22.04 install](https://help.clouding.io/hc/en-us/articles/13572430913180-How-to-Setup-Lightweight-Kubernetes-with-MicroK8s-and-Snap-on-Ubuntu-22-04)
  - [microk8s cluster](https://microk8s.io/docs/aws-user-guide)
  - [cluster upgrade](https://microk8s.io/docs/upgrade-cluster)
 

# 2. System requirements
- Microk8S requirements 540Mb to 4GB memory and 20GB disk space - [link](https://microk8s.io/docs/getting-started)
- Cheaper & more poweful AWS instance with Ubuntu 22.04 to instal should be t4G(ARM) family 
- Microk8s can run with AMD cheaper chips so we choose t4g.small - 2 vCPU and 2 GB RAM instance
- Is t4g.small FREE tier eligible? Yes, the t4g.small instance type is eligible for a free trial until December 31, 2025. This means you can use t4g.small instances without incurring charges up to 750 hours per month during this period, see [link](https://aws.amazon.com/ec2/faqs/#t4g-instances)

# 3 - Opentofu - IaC
You must have an AWS account and AWS credential. In our case we are using a playground account under AWS Organizations configured with SSO login, but this  configuration is far from the scope of this article/project.

Install AWS client, see [link](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Setup AWS client, see [link](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html)

aws organization create lab env for  free tier

Basic
https://medium.com/@netopschic/provisioning-an-ec2-instance-using-opentofu-47aade14956a
Detail
https://4sysops.com/archives/opentofu-example-terraform-fork-create-an-ec2-instance-in-aws/
microks
https://alabekir1975.medium.com/installing-microk8s-on-aws-on-ubuntu20-04-server-e362091fb5ee

Install OpenTofu
Install AWS CLi
Default VPC or not
Others

Find needed ami - # https://documentation.ubuntu.com/aws/en/latest/aws-how-to/instances/find-ubuntu-images/
# https://cloud-images.ubuntu.com/locator/ec2/

 aws ssm get-parameters --names /aws/service/canonical/ubuntu/server/22.04/stable/current/arm64/hvm/ebs-gp2/ami-id --profile 127214162
577_AdministratorAccess --region eu-south-2


"Name": "/aws/service/canonical/ubuntu/server/22.04/stable/current/arm64/hvm/ebs-gp2/ami-id",
            "Type": "String",
            "Value": "ami-0586af70ffaea9a74",
            "Version": 40,
            "LastModifiedDate": 1739941837.655,
            "ARN": "arn:aws:ssm:eu-south-2::parameter/aws/service/canonical/ubuntu/server/22.04/stable/current/arm64/hvm/ebs-gp2/ami-id",
            "DataType": "aws:ec2:image"

aws ec2 describe-images --image-ids ami-0586af70ffaea9a74 --profile 127214162577_AdministratorAccess --region eu-south-2           
### Example OpenTofu Configuration

```hcl
provider "aws" {
  region = "us-east-1"  # Change to your desired region
}

# Define the security group to allow SSH and Kubernetes ports
resource "aws_security_group" "allow_ssh_k8s" {
  name        = "allow_ssh_k8s"
  description = "Allow SSH and Kubernetes ports"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 16443
    to_port     = 16443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Define the EC2 instance with Ubuntu 22.04 image
resource "aws_instance" "microk8s_instance" {
  ami           = "ami-0dba2cb6798c5dbb7"  # Ubuntu 22.04 AMI ID, adjust for your region
  instance_type = "t3.micro"               # Choose appropriate EC2 instance type  -  20G of disk space and 4G of memory https://microk8s.io/docs/getting-started 
  # AMD CPU 
  # https://aws.amazon.com/ec2/instance-types/t3/?nc1=h_ls
  key_name      = "your-ssh-key-name"      # Replace with your SSH key name
  security_groups = [aws_security_group.allow_ssh_k8s.name]
  tags = {
    Name = "MicroK8s-EC2"
  }

  # User data script to install MicroK8s
  user_data = <<-EOF
              #!/bin/bash
              apt update
              apt install -y snapd
              snap install microk8s --classic
              microk8s status --wait-ready
              microk8s enable dns dashboard
              EOF
}

output "instance_public_ip" {
  value = aws_instance.microk8s_instance.public_ip
}

output "instance_private_ip" {
  value = aws_instance.microk8s_instance.private_ip
}
```

### Breakdown of the Configuration

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

### Running the Configuration

1. **Initialize OpenTofu**: In your terminal, navigate to the directory where the `.tf` file is located and run:

   ```bash
   opentofu init
   ```

2. **Apply the Configuration**: To create the resources, run:

   ```bash
   opentofu apply
   ```

   Confirm the action when prompted.

3. **Access the EC2 Instance**: After the EC2 instance is provisioned, you can SSH into it using:

   ```bash
   ssh -i your-ssh-key.pem ubuntu@<instance_public_ip>
   ```

   You can also access the MicroK8s dashboard using its public IP and port `16443` (make sure to set up a password if required by MicroK8s).

### Notes
- **Security**: Ensure your security group is configured to allow only trusted IPs, especially for production environments.
- **AMI ID**: Always verify the Ubuntu 22.04 AMI ID for your region in the AWS console. You can find the most recent AMIs via AWS Marketplace or the EC2 console.
- **Instance Type**: Adjust the instance type to suit your needs, especially if you require more resources for Kubernetes workloads.

This configuration provides a simple and quick setup for provisioning an EC2 instance with Ubuntu 22.04 and installing MicroK8s automatically.
