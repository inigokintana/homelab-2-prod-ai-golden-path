
********
https://github.com/timescale/pgai


# Build on microk8s image register
microk8s enable registry
microk8s kubectl get pods -n container-registry
docker tag myapp:latest localhost:32000/myapp:latest
docker push localhost:32000/myapp:latest
or
microk8s.docker build -t localhost:32000/myapp:latest .
microk8s.docker push localhost:32000/myapp:latest


# Dockerfile
    scrapy startproject dapr_docs_web
    mv dapr_spider.py dapr_docs_web/dapr_docs_web/spiders/.
   

# crontab
    cd dapr_docs_web
    scrapy crawl dapr_docs_web -o dapr_docs_web.json
    # connect to DB and create table if not exist, truncate and create_vector if not exist
    # load using spider




CREATE TABLE IF NOT EXISTS dapr_web (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url TEXT,
    text TEXT
);

ALTER TABLE dapr_web ADD COLUMN lastupdate DATE;
update dapr_web  set lastupdate =  CURRENT_DATE - INTERVAL '8 days'; 
-> 2025-06-02

SELECT ai.create_vectorizer(     
    'dapr_web'::regclass,     
    destination => 'dapr_web_embeddings',     
    embedding => ai.embedding_ollama('all-minilm', 384),     
    chunking => ai.chunking_recursive_character_text_splitter('text'));

SELECT * FROM ai.vectorizer_status;
-- SELECT ai.drop_vectorizer(1, drop_all=>true);

-- All posibilities
SELECT ai.create_vectorizer(
    'dapr_web_chunks'::regclass,
    name => 'dapr_web_chunks_vectorizer',
    loading => ai.loading_column('contents'),
    embedding => ai.embedding_ollama('nomic-embed-text', 768),
    chunking => ai.chunking_character_text_splitter(128, 10),
    formatting => ai.formatting_python_template('title: $title published: $published $chunk'),
    grant_to => ai.grant_to('bob', 'alice'),
    destination => ai.destination_table(
        target_schema => 'postgres',
        target_table => 'dapr_web_embeddings_store',
        view_name => 'dapr_web_embeddings'
    )
);

load-into-db.py


*****
https://github.com/dapr/dapr no sitemap - we skip

****
kubectl apply -k k8s/overlays/dev
kubectl apply -k k8s/overlays/prod
*****
Pending use dapr to connect to postgresql

*****
cd k8s
kustomize build overlays/dev  > overlays/dev/output_dev.yaml
Adapt Tilfile in order to be able to execute overlays/dev/output_dev.yaml 
                                change  image: localhost:32000/my-scraper-image in overlays/dev/output_dev.yaml
                                tilt api https://docs.tilt.dev/api.html
                                Tiltfile example project https://github.com/tilt-dev/pixeltilt


tilt up


To convert it into dapr taking guess-wiki-question as example:
    - adapt requirements.txt 
    - :py import and logic
    - kubernetes resources - binding +  secret https://docs.dapr.io/operations/components/component-secrets/

*****
Alright, let's refactor your Python program to use the Dapr Python SDK (`dapr.clients.DaprClient`) for both the PostgreSQL binding and the secrets building block. This makes the Dapr integration more idiomatic for Python applications.

First, you'll need to make sure the Dapr Python SDK is installed in your Docker image:
`pip install dapr-client`

---

### 1) Updated Python Program: `dapr-sdk-insert-into-db.py`



---

### Key Changes and Dapr SDK Integration Explanation:

1.  **Dapr SDK Imports:**
    * `from dapr.clients import DaprClient`: This is the main import for interacting with Dapr via its SDK.
    * `from dapr.clients.grpc._gen.dapr_pb2 import InvokeBindingRequest`: (Optional, for stricter type hinting in some IDEs or for deeper understanding of the gRPC request structure, removed from the final version for simplicity, as `dapr.clients.DaprClient` handles it.)

2.  **`DaprClient()` Context Manager:**
    * The `with DaprClient() as d:` pattern is used to ensure the gRPC client connection to the Dapr sidecar is properly managed (opened and closed). This is the recommended way to use the SDK.

3.  **`get_db_date` Adaptation (using SDK):**
    * Instead of `requests.post` to the HTTP API, `d.invoke_binding()` is used.
    * `binding_name`: Set to `DAPR_BINDING_NAME` (e.g., "pgdb-agents-connection").
    * `operation`: Still "query".
    * `metadata`: Still a dictionary containing `{'sql': '...'}`.
    * **Response Handling:** The SDK returns a `InvokeBindingResponse` object. The actual data is in `resp.data`, which is `bytes`. You need to `decode('utf-8')` it and then `json.loads()` to parse the JSON response from the Dapr sidecar.

4.  **`load_into_db` Adaptation (using SDK):**
    * **Truncate/Delete:** `d.invoke_binding()` with `operation='exec'` is used. The SQL is in `metadata`.
    * **Insert Data:**
        * `d.invoke_binding()` with `operation='exec'` is used.
        * The SQL is in `metadata`.
        * The `payload` (containing `{"params": [...]}`) needs to be converted to JSON string and then `bytes` using `json.dumps(payload).encode('utf-8')` because the `data` argument of `invoke_binding` expects bytes.

5.  **Secrets Retrieval (`__main__` section) Adaptation (using SDK):**
    * `d.get_secret(DAPR_SECRET_STORE_NAME, DAPR_SECRET_NAME)` is the SDK method for retrieving secrets.
    * It returns a `GetSecretResponse` object. The actual secrets are in `secret_response.secret`, which is a dictionary. You access the specific key like `secret_response.secret.get(DAPR_SECRET_KEY)`.
    * Again, this `get_secret` call is mainly for demonstrating secret retrieval. The `pgsql-binding.yaml` already tells Dapr to use this secret for its connection.

6.  **Removed `DB_CONFIG`:** The `DB_CONFIG` dictionary is completely gone as the Dapr SDK facilitates interaction with the binding, which in turn manages the database connection via the Dapr component.

---

### 2) `pgsql-binding.yaml` (No changes needed)

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pgdb-agents-connection
  namespace: agents
spec:
  type: bindings.postgres
  version: v1
  metadata:
    - name: connectionString
      secretKeyRef:
        name: pg-secret
        key: connectionString
    - name: direction
      value: "input, output"
scopes:
  # This is crucial: the Dapr application ID of your scraper must be listed here.
  # If your CronJob's Dapr app-id is 'dapr-docs-scraper', it must be in scopes.
  - dapr-docs-scraper # Make sure this matches the dapr.io/app-id in your CronJob annotations
```

---

### Kubernetes CronJob Manifest (`dapr-sdk-cronjob.yaml`)

The CronJob manifest is essentially the same as before, as the Dapr SDK relies on the sidecar just like direct HTTP calls. The crucial part is the `dapr.io/enabled` annotation and `dapr.io/app-id`.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: dapr-docs-scraper-sdk-cron # Changed name to reflect SDK usage
  namespace: agents
spec:
  schedule: "0 * * * *"
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app: dapr-docs-scraper-sdk-job # Updated label
          annotations: # <<< DAPR ANNOTATIONS HERE
            dapr.io/enabled: "true"
            dapr.io/app-id: "dapr-docs-scraper" # Ensure this matches the 'scopes' in your binding YAML
            dapr.io/app-port: "80" # Your Python app doesn't have an HTTP server, but Dapr requires this.
                                  # Set it to any unused port.
            dapr.io/log-level: "info"
        spec:
          restartPolicy: OnFailure
          containers:
          - name: scraper
            image: my-scraper-image:latest  # Your Docker image must have 'dapr-client' installed and this new script.
            imagePullPolicy: IfNotPresent
            command: ["python", "dapr-sdk-insert-into-db.py"] # Point to your new SDK-based script
            envFrom:
            - configMapRef:
                name: dapr-scraper-config
            env: # Dapr SDK can pick these up, or rely on Dapr sidecar defaults.
                 # Explicitly setting is good for clarity/troubleshooting.
            - name: DAPR_HTTP_PORT
              value: "3500" # Default Dapr HTTP port
            - name: DAPR_GRPC_PORT # SDK uses gRPC by default, though it can fall back to HTTP
              value: "50001" # Default Dapr gRPC port
            - name: DAPR_BINDING_NAME
              value: "pgdb-agents-connection"
            - name: DAPR_SECRET_STORE_NAME
              value: "kubernetes"
            - name: DAPR_SECRET_NAME
              value: "pg-secret"
            - name: DAPR_SECRET_KEY
              value: "connectionString"
```

**Dockerfile update:**

Make sure your Dockerfile includes `dapr-client`:

```dockerfile
# Example Dockerfile snippet
FROM python:3.9-slim-buster

WORKDIR /app

# Install Dapr SDK
RUN pip install dapr-client requests lxml # lxml for ElementTree if not built-in, requests for sitemap fetching

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt # if you have a requirements.txt

COPY . . # Copy your entire project, including the scrapy directory and dapr-sdk-insert-into-db.py

# Set your scrapy project path if needed, or it's within the app dir
ENV SCRAPY_TARGET_PATH=dapr_docs_web 

CMD ["python", "dapr-sdk-insert-into-db.py"]
```

This setup fully leverages the Dapr Python SDK, making your Python code cleaner and more integrated with the Dapr ecosystem.

*****
kustomize build overlays/prod | kubectl apply -f -