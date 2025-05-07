# 1 - Context
- By Apr 2025, Darp Conversation API building block is in alpha state and it seems not to support local LLM calls, see [link](https://docs.dapr.io/reference/api/conversation_api/).
- We can install Ollama locally in Kubernetes and select and small OSS LLM model and encoding for our lab/dev environment
    - Selected LLM: Llama3.2:1b
    - Selected embedding: all-minilm
- With the Darp annotations we sidecar Ollama container in the POD during its creation
- We can use Darp invokation building block (both http and darp sdk) to call the Llama3.2:1b LLM in Ollama from custom python scripts
- We can create a postgress database with some demo data to simulate different local data sources to play with the selected LLM
    - Postgres pgvector extension support vectors in the selected embedding format to be used in a semantic search by LLM
    - dvdrental is a relational database with dvdrental demo data, see [link]()
    - cosmopedia is a curated sintetic data set, see [link](https://huggingface.co/datasets/MongoDB/cosmopedia-wikihow-chunked?clone=true)
- We can create some PDF & DOCx files with different demo data to simulate local sources to play with the selected LLM

So, we are going to create some python demo projects:
- **guess-poems** - simple python to interact directly  with local LLM sending a prompt
- **guess-films** - we create an agent that reads local postgresql dvdrental database film description data into a prompt and asks local LLM to guess the film tittle. The LLM has no reference data and will not search the internet for you (common misconception). We will see how many times the LLM is right.
- **guess-wiki-questions** -  we create an agent that retrieves the most relevant results from the cosmopedia knowledge base loaded in local postgresql using RAG and local LLM. Image below is from www.mongodb.com blog  see [link](https://www.mongodb.com/developer/products/atlas/choose-embedding-model-rag/).![RAG-LLM](../../RAG-LLM.png). This time the LLM will hace actual data to provide the right answer. So, LLMs are great with good quality data provided by agents, otherwise it will not work as expected. In the above pipeline, we see a common approach used for retrieval in genAI applications — i.e., semantic search. In this technique, an embedding model is used to create vector representations of the user query and of information in the knowledge base. This way, given a user query and its embedding, we can retrieve the most relevant source documents from the knowledge base based on how similar their embeddings are to the query embedding. The retrieved documents, user query, and any user prompts are then passed as context to an LLM, to generate an answer to the user’s question.
- More demos to come ...

# 2 - Why Llama3.2:1b LLM & all-minilm embedding?

To sum up, Llama3.2:1b LLM & all-minilm embedding can work effectively together in Intel/AMD & ARM CPUs with low memory requirements.

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


## 2.1 - Can llama3.2:1b LLM work with all-minilm embeddings?
- Yes, LLaMA 3.2 1B and all-MiniLM work great together in a RAG setup.
The embedding model finds relevant info, the LLM generates great answers from that info. 
- all-MiniLM is used for creating the semantic representations of text, and Llama 3.2:1B is used for understanding and generating text based on the retrieved information