#################
# 1) Variables
#################
variable "ssh_key_name" {
  type    = string
  default = "aipoc" # The name for the SSH key in Hetzner
}

variable "ssh_public_key" {
  type    = string
  default = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..." # Replace with your real public key
}

variable "sg_ip_cidr" {
  type    = string
  default = "88.10.70.27/32" # Your router's public IP
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

#################
# 2) Provider
#################
provider "hcloud" {
  token = var.hcloud_token
}

#################
# 3) Resources
#################

# Upload SSH key to Hetzner Cloud
resource "hcloud_ssh_key" "default" {
  name       = var.ssh_key_name
  public_key = var.ssh_public_key
}

# Create the server
resource "hcloud_server" "ubuntu2204" {
  name        = "ubuntu2204-microk8s"
  server_type = "cax11" # 1 vCPU, 2 GB RAM — upgrade to cx21/cx31 if needed
  image       = "ubuntu-22.04"
  location    = "fsn1" # Helsinki (hel1); other options: fsn1 (Germany), nbg1 (Germany)
  ssh_keys    = [hcloud_ssh_key.default.id]
  user_data   = file("./userdata.sh") # You can gzip+base64 if you want, but plain works
}

#################
# 4) Outputs
#################
output "server_ipv4" {
  value = hcloud_server.ubuntu2204.ipv4_address
}

output "server_ipv6" {
  value = hcloud_server.ubuntu2204.ipv6_address
}
