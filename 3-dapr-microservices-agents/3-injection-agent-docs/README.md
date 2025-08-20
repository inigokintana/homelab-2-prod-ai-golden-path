
**WIP**
We se there are several options to implement this:
- 1) pgAI is designed to read documents from for example S3, HTTP files or local files and store docuuments embedding in RAG database for semantic search. Here how [example 1](https://github.com/timescale/pgai/blob/main/docs/vectorizer/document-embeddings.md) and [example2](https://github.com/timescale/pgai/tree/main/examples/embeddings_from_documents).
- 2) dapr agent getting PDFs from expecific sites(https://github.com/dapr/dapr-agents/blob/249ea5ec43f75825f662992e765cb09b5fd31695/docs/concepts/arxiv_fetcher.md)
- 3) Custom programming using Dapr building blocks or not . You can see a raw inmplementation here but we are not installing it automatically in K8S/shell script.

Still valuing the pros and cons of options 1) and 2) that seems more interesting than option 3). 

**WIP**