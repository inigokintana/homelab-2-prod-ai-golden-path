#################
# 1) Variables
#################
# We upload our SSH key OpenSS format in Hetzner Cloud, so we don't need to specify it here
# variable "ssh_key_name" {
#   type    = string
#   default = "AIpoc2" # The name for the SSH key in Hetzner
# }

# variable "ssh_public_key" {
#   type    = string 
#   #must be OpenSSH format 
#   default = "ssh-rsa AAA...orzH"
# }
variable "sg_ip_cidr" {
  type    = string
  default = "88.9.241.28/32" # Your router's public IP
}

# sensitive and not default means it will ask for token at runtime
variable "hcloud_token" {
  type      = string
  sensitive = true
}

#################
# 2) Provider
#################
# token https://docs.hetzner.com/cloud/api/getting-started/generating-api-token/
provider "hcloud" {
  token = var.hcloud_token
}

#################
# 3) Resources
#################

# Upload SSH key to Hetzner Cloud
# resource "hcloud_ssh_key" "default" {
#   name       = var.ssh_key_name
#   public_key = var.ssh_public_key
# }

# Create the server
resource "hcloud_server" "ubuntu2204" {
  name        = "ubuntu2204-microk8s"
  server_type = "cax21" # 1 vCPU, 2 GB RAM — upgrade to cx21/cx31 if needed
  image       = "ubuntu-22.04"
  location    = "fsn1" # Helsinki (hel1); other options: fsn1 (Falkestein Germany), nbg1 (Nuremberg Germany)
  #ssh_keys    = [hcloud_ssh_key.default.id]
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
