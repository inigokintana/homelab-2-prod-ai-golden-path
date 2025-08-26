
**WIP**
We se there are several options to implement this:

- 1) pgAI is designed to read documents from for example S3, HTTP files or local files and store documents embedding in RAG database for semantic search. Here how [example 1](https://github.com/timescale/pgai/blob/main/docs/vectorizer/document-embeddings.md) and [example2](https://github.com/timescale/pgai/tree/main/examples/embeddings_from_documents).
- 2) dapr agent getting PDFs from expecific [sites](https://github.com/dapr/dapr-agents/blob/249ea5ec43f75825f662992e765cb09b5fd31695/docs/concepts/arxiv_fetcher.md)
- 3) Custom programming using Dapr building blocks or not . You can see a raw inmplementation here but we are not installing it automatically in K8S/shell script.

Still valuing the pros and cons of options 1) and 2) that seems more interesting than option 3) partly implemented here. 

**WIP**
https://github.com/timescale/pgai/blob/main/docs/vectorizer/api-reference.md#loading-configuration
Environment configuration
You just need to ensure the vectorizer worker has the correct credentials to access the file, such as in environment variables. Here is an example for AWS S3:

export AWS_ACCESS_KEY_ID='your_access_key'
export AWS_SECRET_ACCESS_KEY='your_secret_key'
export AWS_REGION='your_region'  # optional

- sql 3-dapr-microservices-agents/3-injection-agent-docs/sql/create-table.sql
- sql 3-dapr-microservices-agents/3-injection-agent-docs/sql/create-vectorized-table.sql
- sudo mkdir /mnt/docs
- keep same permisons as in /mnt/pgata directory - sudo chown 
- sudo docker build --no-cache -t localhost:32000/docs-sync:latest .
- sudo docker push localhost:32000/docs-sync:latest
- k apply -f 3-dapr-microservices-agents/3-injection-agent-docs/k8s/base/pv.yaml
- k apply -f 3-dapr-microservices-agents/3-injection-agent-docs/k8s/base/pvc.yaml
- k apply -f 3-dapr-microservices-agents/3-injection-agent-docs/k8s/base/configmap.yaml
- all yaml
- 