# 1- Objective

We want to play with MCP architecture agent and Dapr.

To be able to provide an OSS stack we have chosen Dapr in our golden path (opinionated shortcut) and Dapr has its own MCP path:
 - Please see [Dapr Agents Framework and Roadmap](https://github.com/dapr/dapr-agents/blob/249ea5ec43f75825f662992e765cb09b5fd31695/README.md)
 - [See MCP Quickstarts](https://github.com/dapr/dapr-agents/blob/249ea5ec43f75825f662992e765cb09b5fd31695/quickstarts/README.md#mcp-agent-quickstarts)
 - We are using [this MCP postgreSQL server example but we have moved into K8s](https://github.com/dapr/dapr-agents/blob/249ea5ec43f75825f662992e765cb09b5fd31695/quickstarts/08-data-agent-mcp-chainlit/README.md). In this example Dapr agents works with OpenAI so you need an API KEY.
 - Dapr agents 1.16 will support Ollama, to be able to have a local LLM, is in preview still in sept 2025 - [That is why must be done later and not now](https://v1-16.docs.dapr.io/reference/components-reference/supported-conversation/ollama/)
 - The Dapr example we deploy in K8s, uses Chainlit to glue user interaction with LLM (conversational agent with OpenAI), Python (MCP client + some logic) and MCP Server interaction, see ![MCP Architecture](../../docs/MCP-architecture.png):
    - Chainlit is an open-source Python framework designed to help developers build and deploy conversational AI applications with a focus on ease of use and minimal front-end development. It's essentially a toolkit for creating user interfaces for large language models (LLMs) and AI agents, allowing developers to focus on the core logic of their AI application in Python without getting bogged down in web development complexities
    - Chainlit is running under Python code container in AI Agent part in the image -  see this line in Dockerfile: CMD ["chainlit", "run", "app.py", "-w", "--host", "127.0.0.1", "--port", "8001"]
    - MCP server is installed inside same POD as AI agent  but in a different container that is why we configure traffic under 127.0.0.1(localhost) IP and not 0.0.0.0 (all intefaces - too much opened). We could have configured it in another POD and namespace closer to a fully Remote Service style but you can do it as you wish.
    - **Redis is it being used** by dapr_agents? It seems not. The agent will NOT remember all the previous conversation if this is not working
    ````
        I have no name!@dapr-dev-redis-master-0:/$ redis-cli
        127.0.0.1:6379>  AUTH xxxxxx
        OK
        127.0.0.1:6379> KEYS *
        1) "nodeapp||order"
    ````

# 2 - How do we install it?

Check step 6) and specifically step 6.6) in:
- 1-IaC/AWS/opentofu/userdata.sh
- 1-IaC/OVH-Hetzner/userdata.sh
- 1-IaC/WSL2/install-in-WSL2.sh

Additionaly, to recreate an OpenAI API_KEY:
- change it in deployment.yaml and redeploy, remember is was created as a secret in step 6.4

# 3 - Project Structure
```
├── k8s                       # Kubernetes deployment
├── Dockerfile                # Docker build  
└── README.md
```
