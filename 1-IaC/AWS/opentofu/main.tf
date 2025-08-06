# 1) Variables
#################
# public ssh RSA to include in AWS EC2 to be able to connect
# Not needed as we reference key pair in resource Ec2 Instance in OpenTofu
# variable "ec2_user_public_rsa" {
#   type    = string
#   default = "ssh-rsa MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA65SCWxubb5qi5iHcVq8e5DIDmkAGeYYtNvO2w2BywOoMiQprbzbBEnar9vGJbIZIAbYjW0e/rzvVSbu0e5mzOvRcm8nmsgr2dp53EW/KUJG/6GhBlIzJLjA5ItV92kDZRLYOuhSuurrpo8x/uycLixrsNp4BP66etPRsL3QgEQ1rVSbLRDxwzSYJB64fELTqZRkREqoTA/mfuE2/BLu6t2zV9Zo6a5G2ZyXQlCo/lG3/WngriB2D9FAZ6WvqYmip0AIdXTOrDxYtJe8KPEOiv0uGpjbwhKB1CsBkrq3bF7qZhBWQ6WZB3Q7XWPchSmgk2hgMIjY3aySWO4B0+qK8xwIDAQAB"
# }

# IPs allowed to cross the instace security group
# For security reasons, you should put your router public IP x.y.x.y/32 here
# instead of 0.0.0.0/0 <-anywhere 
variable "sg_ip_cidr" {
  type    = string
  #default = "0.0.0.0/0" # anywhere 
  default ="88.9.66.149/32" # my router public dinamyc IP, change it to your own convinience
}

# 2) Provider
#################
provider "aws" {
  region = "eu-south-2" # Spain, change it to you own convinience
}

# 3) Resources: getting data
#################
# Fetch the default VPC
data "aws_vpc" "default" {
  default = true
}

# Fetch the first available subnet in the default VPC
data "aws_subnet" "default_subnet" {
  vpc_id = data.aws_vpc.default.id
  availability_zone = "eu-south-2a"  # Spain - Choose the AZ where you want to create the instance
}

# get manually created key pair in order to create the ec2 instance
data "aws_key_pair" "tf" {
  #key_name = var.ec2_key_name
  # key pair created manually in AWS console or with AWS CLI
  key_name = "aipoc"
  filter {
    name   = "tag:Component"
    values = ["opentofu"]
  }
}

# 4) Resources: provisioning resources
#################
# Define the security group to allow SSH, Kubernetes ports and some other services
resource "aws_security_group" "allow_ssh_k8s" {
  name        = "allow_ssh_k8s"
  description = "Allow SSH, Kubernetes ports and additional services"
  
  # ssh
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    #cidr_blocks = ["0.0.0.0/0"] #anywhere - you should put your router public IP x.y.x.y/32 here for improved security
    cidr_blocks = [var.sg_ip_cidr]
  }
  
  # microk8s dashboard-proxy  port
  # you could comment this and use ssh tunnel: ssh -L 10443:localhost:10443 ubuntu@instance_public_ip
  ingress {
    from_port   = 10443
    to_port     = 10443
    protocol    = "tcp"
    cidr_blocks = [var.sg_ip_cidr]
  }

  # Ollama and the LLM&SLM inside
  # you could comment this and use ssh tunnel: ssh -L 11434:localhost:11434 ubuntu@instance_public_ip
  ingress {
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = [var.sg_ip_cidr]
  }

  # Postgres port for TimescaleDB and Vectorizer
  # you could comment this and use ssh tunnel: ssh -L 15432:localhost:1154321434 ubuntu@instance_public_ip
  ingress {
    from_port   = 15432
    to_port     = 15432
    protocol    = "tcp"
    cidr_blocks = [var.sg_ip_cidr]
  }

  # Dapr dashboard port
  # you could comment this and use ssh tunnel: ssh -L 9999:localhost:9999 ubuntu@instance_public_ip
  ingress {
    from_port   = 9999
    to_port     = 9999
    protocol    = "tcp"
    cidr_blocks = [var.sg_ip_cidr]
  }

  # Flask user web app port
  # you could comment this and use ssh tunnel: ssh -L 5000:localhost:5000 ubuntu@instance_public_ip
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [var.sg_ip_cidr]
  }

  # Tilt port
  # you could comment this and use ssh tunnel: ssh -L 10350:localhost:10350 ubuntu@instance_public_ip
  ingress {
    from_port   = 10350
    to_port     = 10350
    protocol    = "tcp"
    cidr_blocks = [var.sg_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = -1 # all protocols tcp/udp/http/smtp ...
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "ubuntu2204" {
  ami           = "ami-0586af70ffaea9a74" # ARM 64b - you must find the AMIO ID for your region, this is for eu-south-2 (Spain)
  instance_type = "t4g.xlarge" # (4 vCPU -16 GB RAM) change it to your own convinience
  #subnet_id     = data.aws_subnet.default_subnet.id
  key_name      =  data.aws_key_pair.tf.key_name # got above
  security_groups = [aws_security_group.allow_ssh_k8s.name]
  root_block_device {
    volume_size = 50
    volume_type = "gp2"
  }
  user_data = base64gzip(file("./userdata.sh"))
  tags = {
    Name = "ubuntu2204-microk8s"
    Opentofu   = "true"
    Env = "playground"
  }
}

# 5) Outputs
#################
output "instance_public_ip" {
  value = aws_instance.ubuntu2204.public_ip
}

output "instance_private_ip" {
  value = aws_instance.ubuntu2204.private_ip
}
