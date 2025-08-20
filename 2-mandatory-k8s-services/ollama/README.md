# 1- Why Ollama
This is something we have [mentioned before](https://github.com/inigokintana/homelab-2-prod-ai-golden-path/tree/main?tab=readme-ov-file#34---why-ollama).

# 2 - How to install it  
Check step 5.1) in:
- 1-IaC/AWS/opentofu/userdata.sh
- 1-IaC/OVH-Hetzner/userdata.sh
- 1-IaC/WSL2/install-in-WSL2.sh

Be aware of different RAM & CPU requirements depending on the LLM/SLM you load into Ollama. RAG database must have SAME encoding all-minilm in vectorizer, so we have to activate it in Ollama.

Llama 3.2:1B can indeed be considered a Small Language Model (SLM) based on its minimum memory and CPU requirements. Here's why¹ ²:
- Memory Requirements: Llama 3.2:1B requires only 4 GB of VRAM and 8 GB of system RAM, which is relatively low compared to larger models. This makes it suitable for edge devices, mobile, and embedded systems.
- CPU Requirements: Given its small size, Llama 3.2:1B can run effortlessly on almost any modern computer, even without a dedicated GPU. This flexibility makes it an excellent choice for developers working with limited resources.
- Model Size: With only 1 billion parameters, Llama 3.2:1B is significantly smaller than larger models like Llama 3.1 405B, which has 405 billion parameters. This smaller size contributes to its reduced computational requirements.
