# 1 - Context
- By Apr 2025, Darp Conversation API building block is in alpha state and it seems not to support local LLM calls with Ollama, see [link](https://docs.dapr.io/reference/api/conversation_api/).
- We can install Ollama locally in Kubernetes and select and small OSS LLM model and encoding for our lab/dev environment
    - Selected LLM: Llama3.2:1b not fully OSS as LlamaIndex but it has better text verbosity
    - Selected embedding: all-minilm
- With the Darp annotations we sidecar Ollama container in the POD during its creation
- We can use Darp invokation building block (both http and darp sdk) to call the Llama3.2:1b LLM in Ollama from custom python scripts
- We can create a postgress database with some demo data to simulate different local data sources to play with the selected LLM
    - Postgres pgvector extension support vectors in the selected embedding format to be used in a semantic search by LLM
    - We take Dpar offical documentation as a source because the answers about question about questions around Dapr are quite inaccurate.
    - We can create some PDF & DOCx files with different demo data to simulate local sources to play with the selected LLM

So, we are going to create some python demo projects:
- **2-injection-agent-web-dapr** - simple python using scraper that loads updated dapr documentation into a postgreSQL table that will be vectorized inmediatly thanks to pgAI. We use Dpar building blocks.
- **1-user-web**: flask web page where user can ask questions, we use daor building blocks.
    - previously, the question is embbeded by Ollama and done a semantic search inside PostgreSQL RAG database
    - Then all is sent back to Ollama LLM/SLM and optionally to OpenAI 
    - Ollama or OpenAI answer is given to the user
    - **Note**: for OpenAI usage you must install your API KEY. You must install it in a secret as explained in install script.
- More demos to come ...

# How to install it
Check step 6) in:
- 1-IaC/AWS/opentofu/userdata.sh
- 1-IaC/WSL2/install-in-WSL2.sh


# Note: Why Llama3.2:1b SLM & all-minilm embedding?

To sum up, Llama3.2:1b SLM (Small Language Model) & all-minilm embedding can work effectively together in Intel/AMD & ARM CPUs with low memory requirements.

all-minilm embedding is directly available in the standard Ollama library and can work in any CPU and all all-MiniLM embedding models are open-source.

- **Llama3.2:1b LLM**: 
    - The Llama 3.2 family includes four models: 1B, 3B, 11B, and 90B. The 1B and 3B models are lightweight, text-only models designed for on-device applications. While they are primarily text-based, they can be effectively used in Retrieval-Augmented Generation (RAG) pipelines.
    - Context Window: Llama 3.2 1B supports a context window of 128,000 tokens, allowing it to process and understand a substantial amount of retrieved information

- **all-minilm**: all-MiniLM-L6-v2 is 100% open-source, lightweight, and perfect for many RAG and semantic search use cases.

**License:**
- **Llama3.2:1b LLM**:  by Meta is released under the Llama 3.2 Community License Agreement. This license permits use, reproduction, distribution, and modification of the Llama materials, provided that users adhere to the terms specified in the agreement. Notably, the license includes an Acceptable Use Policy that outlines restrictions to ensure responsible use of the model, see [link](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE). Notice, if your products or services using Llama 3.2 have more than 700 million monthly active users (on the Llama 3.2 version release date), you need to request a commercial license from Meta.
- **all-minilm**: the popular sentence-transformers/all-MiniLM-L6-v2 model, which is widely used, is released under the Apache 2.0 license.
This permissive license allows for both personal and commercial use of the model in accordance with the terms of the Apache 2.0 license.
You can find the license file directly in the Hugging Face repository for the all-MiniLM-L6-v2 model., see link [Hugging Face page](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).


## Can llama3.2:1b LLM work with all-minilm embeddings?
- Yes, LLaMA 3.2 1B and all-MiniLM work great together in a RAG setup.
The embedding model finds relevant info, the LLM generates great answers from that info. 
- all-MiniLM is used for creating the semantic representations of text, and Llama 3.2:1B is used for understanding and generating text based on the retrieved information