#################
# 1) Variables
#################
variable "sg_ip_cidr" {
  type    = string
  default = "88.10.73.108/32" # Your router's public IP
}

# sensitive and not default means it will ask for token at runtime
# token https://docs.hetzner.com/cloud/api/getting-started/generating-api-token/
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

# 3.1) Firewall
# Create a firewall allowing only SSH from your router IP
resource "hcloud_firewall" "ssh_only" {
  name = "ssh-only"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = [var.sg_ip_cidr] # Your router’s public IP
  }

}
# 3.2) Create the server
resource "hcloud_server" "ubuntu2204" {
  name        = "ubuntu2204-microk8s"
  server_type = "cax21" # cax21 (4 vCPU Ampere, 8 GB RAM) 
  image       = "ubuntu-22.04"
  location    = "fsn1" # Helsinki (hel1); other options: fsn1 (Falkestein Germany), nbg1 (Nuremberg Germany)
  user_data   = file("./userdata.sh") # You can gzip+base64 if you want, but plain works
  firewall_ids = [hcloud_firewall.ssh_only.id] # Attach the firewall to the server

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
