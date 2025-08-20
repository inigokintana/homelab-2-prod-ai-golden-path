# 1 - Why TimescaleDB?

This is something we have [mentioned before](https://github.com/inigokintana/homelab-2-prod-ai-golden-path/tree/main?tab=readme-ov-file#38---why-timescaledb).

**Note 1:** if you do not want to use TimescaleDB still you can install pgAI Vectorizer [into any postgres db](https://www.timescale.com/blog/pgai-vectorizer-now-works-with-any-postgres-database?utm_source=timescaledb&utm_medium=youtube&utm_campaign=yt-channel-2023&utm_content=timescale-blog), [here how](https://github.com/timescale/pgai/blob/released/docs/install/source.md) and [create the vectorizer worker](https://github.com/timescale/pgai). 

**Note 2:**
pgAI above 0.10.0 made a determined step forward to be installed in any database for example in AWS RDS separating pgAI from postgreSQL extension, see [link](https://github.com/timescale/pgai/blob/main/docs/vectorizer/migrating-from-extension.md) and pgAI must be installed using [Python](https://github.com/timescale/pgai/blob/main/docs/vectorizer/python-integration.md).

**Note 3:**
Be aware that TimescaleDB new images are released periodically and having rour own container registry may be a good idea.

# 2 - Technical prerequisites
- K8s Ollama service deployed and preloaded with specific llama3.2:1b LLM and all-minilm preloaded  
- K8s Timescaledb service image deployed with persistent data volume 
- pgai vectorizer worker configured and installed with:
    - pg connection string pwd
    - OLLAMA_HOST value is set [in vectorizer] (https://github.com/timescale/pgai/blob/main/docs/vectorizer-quick-start.md?ref=timescale.ghost.io) vs OPENAI where variable has to be [in DB container](https://github.com/timescale/pgai/blob/released/docs/vectorizer/quick-start-openai.md)
    - Pending: vectorizer-worker container - password was stored in secret - how to get it from there secretRef:name: pgvectorconfig? See this [example step 6](https://docs.tigerdata.com/self-hosted/latest/install/installation-kubernetes/).

# 3  - How to create vectorize data?

API has changed above pgAI 0.10.0 so be carefull to reference the update one, see [link](https://github.com/timescale/pgai/blob/main/docs/vectorizer/api-reference.md#install-or-upgrade-the-database-objects-necessary-for-vectorizer) for example this [wiki](https://github.com/timescale/pgai/blob/released/README.md) is outdated.

Check the SQL subfolder in:
- 3-dapr-microservices-agents/1-user-web/sql/create-vectorized-table.sql
- 3-dapr-microservices-agents/2-injection-agent-web-dapr/sql/create-vectorized-table.sql

# 4 - How to install it?

Check step 5.2) in:
- 1-IaC/AWS/opentofu/userdata.sh
- 1-IaC/OVH-Hetzner/userdata.sh
- 1-IaC/WSL2/install-in-WSL2.sh
