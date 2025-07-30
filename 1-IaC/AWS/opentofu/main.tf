provider "aws" {
  region = "eu-south-2" # Spain, change it to you own convinience
}

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

variable "ec2_user_public_rsa" {
  type    = string
  default = "ssh-rsa MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA65SCWxubb5qi5iHcVq8e5DIDmkAGeYYtNvO2w2BywOoMiQprbzbBEnar9vGJbIZIAbYjW0e/rzvVSbu0e5mzOvRcm8nmsgr2dp53EW/KUJG/6GhBlIzJLjA5ItV92kDZRLYOuhSuurrpo8x/uycLixrsNp4BP66etPRsL3QgEQ1rVSbLRDxwzSYJB64fELTqZRkREqoTA/mfuE2/BLu6t2zV9Zo6a5G2ZyXQlCo/lG3/WngriB2D9FAZ6WvqYmip0AIdXTOrDxYtJe8KPEOiv0uGpjbwhKB1CsBkrq3bF7qZhBWQ6WZB3Q7XWPchSmgk2hgMIjY3aySWO4B0+qK8xwIDAQAB"
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
  instance_type = "t4g.xlarge" # (4 vCPU -16 GB RAM) change it to your own convinience
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
