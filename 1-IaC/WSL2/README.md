## 1 - Install WSL2  
Follow steps in the link [WSL2 install](https://documentation.ubuntu.com/wsl/latest/howto/install-ubuntu-wsl2/)
 - wsl --install Ubuntu-22.04

### 1.1 - Additionally, consider this in case you are behind company proxy
```
wsl --update --web-download 
wsl -l -v
wsl --install -d Ubuntu-22.04
```
### 1.2 - WSL2 VM resources parameters in .wslconfig
This are the values in my c:\users\<myuser>\.wslconfig
```
[wsl2]
# RAM memory 10GB
memory=10GB
processors=4      # Uses 4 virtual processors
swap=2GB          # Allocates 2 GB swap file

# Set the maximum size of the virtual hard disk
# This value is in gigabytes (GB).
# For 80GB, use 80.
size=80
```

# 2 - Execute shell script

Login into WSL2 Ubuntu-22.04, [download this shell script](https://github.com/inigokintana/homelab-2-prod-ai-golden-path/blob/main/1-IaC/WSL2/install-in-WSL2.sh) and execute it:
- The shell script is self explainatory and fully commented, take a look to it
- Download: wget https://github.com/inigokintana/homelab-2-prod-ai-golden-path/blob/main/1-IaC/WSL2/install-in-WSL2.sh
- Change permission: chmod 744 install-in-WSL2.sh
- Execute: ./install-in-WSL2.sh
