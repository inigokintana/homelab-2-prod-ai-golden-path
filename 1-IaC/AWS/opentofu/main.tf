# 1) Variables
#################
# IPs allowed to cross the instace security group
# For security reasons, you should put your router public IP x.y.x.y/32 here
# instead of 0.0.0.0/0 <-anywhere 
variable "sg_ip_cidr" {
  type    = string
  #default = "0.0.0.0/0" # anywhere 
  default ="88.10.70.184/32" # my router public dinamyc IP, change it to your own convinience
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
  description = "Allow SSH only from restricted ip"
  
  # ssh
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    #cidr_blocks = ["0.0.0.0/0"] #anywhere - you should put your router public IP x.y.x.y/32 in the var.sg_ip_cidr variable for improved security
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
  user_data_base64 = base64gzip(file("./userdata.sh"))
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
