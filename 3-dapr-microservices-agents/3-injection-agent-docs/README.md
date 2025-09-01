
# 1 - Context/Objective
We see there are several options to implement this:

- 1) pgAI is designed to read documents from for example S3, HTTP files or local files and store documents embedding in RAG database for semantic search. Here how [example 1](https://github.com/timescale/pgai/blob/main/docs/vectorizer/document-embeddings.md) and [example2](https://github.com/timescale/pgai/tree/main/examples/embeddings_from_documents).
- 2) dapr agent getting PDFs from expecific [sites](https://github.com/dapr/dapr-agents/blob/249ea5ec43f75825f662992e765cb09b5fd31695/docs/concepts/arxiv_fetcher.md)
- 3) Custom programming using Dapr building blocks or not .


We take a mix solution between options 1 and and 3:
- Custom programming: 
     - We use a shell script with inotify in and infinite loop that detects changes CRUD in a local filesystem /mnt/docs. We could have done it with S3 but it seems that in Opentofu there is no Hetzner support to provision Hetzner S3 type objects and we want to work both in AWS, Hetzner and WSL2. So, that is why we took local directory approach.
     - All the files are CRUD  in a database table using Python with metadata
     - **Pending**:
        - Use DAPR in this custom programming Python part
        - Forward Python log into Docker/K8S log
        - Use kustomize to have a single YAML deployment file
        - No Tilt use
        - Modify user-web development adding UNION Select from this vectorized **table document_embeddings_store** to allow user promt to search in this table for more accurate answers
- We use pgAI to automatically generate the vectorizer embedding of any change in the documents table but **MUST** have accest to the local file system
- Requirements: In K8S it is not possible to share a fileystem between vectorizer and the custom programming POD unless you configure a NFS or you put both PODS in the same namespace. That it why we moved and deployed this agent into **pgvector** namespace.


# 2 - How do we install it?

Check step 6) and specifically step 6.5) in:
- 1-IaC/AWS/opentofu/userdata.sh
- 1-IaC/OVH-Hetzner/userdata.sh
- 1-IaC/WSL2/install-in-WSL2.sh

# 3 - Project Structure

```
.
├── sql/                      # SQL scripts for table creation
├── k8s/
│   ├── base/                 # Base Kubernetes manifests
├── Dockerfile                # Docker build for the scraper
├── monitor_docs.sh           # Shell scripts monitoring CRUD files are in directory - it calls to load-files-to-db.py
├── load-files-to-db.py       # Python scraper and logic
├── load-files-to-db-dapr.py  # Pending to be adjust to Dapr SDK
└── README.md
```
