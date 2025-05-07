provider "aws" {
  region = "eu-south-2"
}

# resource "aws_vpc" "myvpc" {
#   cidr_block = "10.0.0.0/16"
#   tags = {
#     Name = "myvpc"
#   }
# }
# resource "aws_subnet" "mysubnet" {
#   vpc_id     = aws_vpc.myvpc.id
#   cidr_block = "10.0.1.0/24"
#   tags = {
#     Name = "mysubnet"
#   }
# }

# Fetch the default VPC
data "aws_vpc" "default" {
  default = true
}

# Fetch the first available subnet in the default VPC
data "aws_subnet" "default_subnet" {
  vpc_id = data.aws_vpc.default.id
  availability_zone = "eu-south-2a"  # Choose the AZ where you want to create the instance
}

# get manually created key pair in order to create the ec2 instance
data "aws_key_pair" "tf" {
  #key_name = var.ec2_key_name
  # key pair created manually in AWS console
  #  To just output the public part of a private key: openssl rsa -in mykey.pem -pubout > mykey.pub
  key_name = "mk8u22"
  filter {
    name   = "tag:Component"
    values = ["opentofu"]
  }
}

variable "ec2_user_public_rsa" {
  type    = string
  default = "ssh-rsa MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA6UpJ9oCiyS+3cK+1s0pV1gHkfAcIH9cxnXmMtC0Uf4+DiRJliZ0VPFlRqLVDhewoSytyC63mkZL5RCkZZ1Lg1FgabdSDljjIeBQxFq2FNwmVktRqoToFkTb/Qy/yYXApg4EHT8hBc2NaILOjPuX+Cx4/e7JSe6JVn9X6qSbVPI1hnva746UQFcVHhe4zV3gsJ60gEkGrFex26DTMnmDsXt/+501P1bV8cAAyo6x4T+ZW5RIS3jKPUdqaptXnmoat5w3tFqy9EhJUC4rcPXCdfsvDwfCPConazN2lv3Xiqiv2zPQp3sq4eiEL6G+I5F7Arwo4Aq4VEKbGCfiArSMMVwIDAQAB"
}


# Define the security group to allow SSH and Kubernetes ports
resource "aws_security_group" "allow_ssh_k8s" {
  name        = "allow_ssh_k8s"
  description = "Allow SSH and Kubernetes ports"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #anywhere
  }
  
  # microk8s dashboard-proxy  port
  ingress {
    from_port   = 10443
    to_port     = 10443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #anywhere
  }

  # Task manager API
  ingress {
    from_port   = 30008
    to_port     = 30008
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] #anywhere
  }


  egress {
    from_port   = 0
    to_port     = 0
    protocol    = -1 # all protocols tcp/udp/http/smtp ...
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "ubuntu2204" {
  ami           = "ami-0586af70ffaea9a74" # ARM 64b
  instance_type = "t4g.small"
  #subnet_id     = data.aws_subnet.default_subnet.id
  key_name      =  data.aws_key_pair.tf.key_name # got above
  security_groups = [aws_security_group.allow_ssh_k8s.name]
  root_block_device {
    volume_size = 50
    volume_type = "gp2"
  }
  user_data = file("./userdata.sh")
  tags = {
    Name = "ubuntu2204-microk8s"
    Opentofu   = "true"
    Env = "playground"
  }
}


output "instance_public_ip" {
  value = aws_instance.ubuntu2204.public_ip
}

output "instance_private_ip" {
  value = aws_instance.ubuntu2204.private_ip
}
