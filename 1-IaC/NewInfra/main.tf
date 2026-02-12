terraform {
	required_version = ">= 1.3.0"
	required_providers {
		aws = {
			source  = "hashicorp/aws"
			version = ">= 4.0"
		}
	}
}

provider "aws" {
	region = var.region
}

variable "region" {
	description = "AWS region to create resources in"
	type        = string
	default     = "us-east-1"
}

variable "instance_type" {
	description = "EC2 instance type"
	type        = string
	default     = "t3.micro"
}

variable "key_name" {
	description = "Name of an existing EC2 KeyPair to enable SSH access (leave empty to skip)"
	type        = string
	default     = ""
}

variable "ssh_cidr" {
	description = "CIDR range allowed to SSH to the instance (change to your IP for safety)"
	type        = string
	default     = "0.0.0.0/0"
}

variable "instance_name" {
	description = "Name tag for the EC2 instance"
	type        = string
	default     = "ec2-from-terraform"
}

data "aws_ami" "amazon_linux_2" {
	most_recent = true
	owners      = ["amazon"]
	filter {
		name   = "name"
		values = ["amzn2-ami-hvm-*-x86_64-gp2"]
	}
}

data "aws_vpc" "default" {
	default = true
}

data "aws_subnet_ids" "default" {
	vpc_id = data.aws_vpc.default.id
}

resource "aws_security_group" "ssh" {
	name        = "allow_ssh"
	description = "Allow SSH access"
	vpc_id      = data.aws_vpc.default.id

	ingress {
		description = "SSH"
		from_port   = 22
		to_port     = 22
		protocol    = "tcp"
		cidr_blocks = [var.ssh_cidr]
	}

	egress {
		from_port   = 0
		to_port     = 0
		protocol    = "-1"
		cidr_blocks = ["0.0.0.0/0"]
	}

	tags = {
		Name = "allow_ssh"
	}
}

resource "aws_instance" "this" {
	ami                    = data.aws_ami.amazon_linux_2.id
	instance_type          = var.instance_type
	subnet_id              = element(data.aws_subnet_ids.default.ids, 0)
	vpc_security_group_ids = [aws_security_group.ssh.id]

	# key_name is optional - leave as empty string to skip attaching a key
	key_name = var.key_name != "" ? var.key_name : null

	tags = {
		Name = var.instance_name
	}
}

output "instance_id" {
	description = "ID of the created EC2 instance"
	value       = aws_instance.this.id
}

output "public_ip" {
	description = "Public IP of the created EC2 instance (if available)"
	value       = aws_instance.this.public_ip
}

output "instance_az" {
	description = "Availability Zone of the instance"
	value       = aws_instance.this.availability_zone
}

