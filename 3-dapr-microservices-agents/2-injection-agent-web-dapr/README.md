
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

```python
import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import subprocess
import sys
import time

# --- DAPR SDK IMPORTS ---
from dapr.clients import DaprClient
from dapr.clients.grpc._gen.dapr_pb2 import InvokeBindingRequest # Optional, for type hinting if desired
# --- END DAPR SDK IMPORTS ---

# --- CONFIG ---
DB_TABLE = os.getenv("DB_TABLE", "dapr_web") # Table to insert data into
SITEMAP_URL = os.getenv("SITEMAP_URL", "https://docs.dapr.io/en/sitemap.xml") # URL of the sitemap to check for updates
JSON_FILE = os.getenv("JSON_FILE", "dapr_docs_web.json") # Path to the JSON file to load into the database
SCRAPY_TARGET_PATH = os.getenv("SCRAPY_TARGET_PATH", "dapr_docs_web") # Path to the Scrapy project directory

# --- DAPR BINDING & SECRET CONFIG (as defined in your YAMLs) ---
DAPR_BINDING_NAME = os.getenv("DAPR_BINDING_NAME", "pgdb-agents-connection")
DAPR_SECRET_STORE_NAME = os.getenv("DAPR_SECRET_STORE_NAME", "kubernetes") # Typically 'kubernetes' in K8s
DAPR_SECRET_NAME = os.getenv("DAPR_SECRET_NAME", "pg-secret")
DAPR_SECRET_KEY = os.getenv("DAPR_SECRET_KEY", "connectionString")
# --- END DAPR BINDING & SECRET CONFIG ---

# --- ORIGINAL FUNCTIONS (ADAPTED FOR DAPR SDK) ---

def get_first_sitemap_date(sitemap_url):
    """
    Fetches an XML sitemap and extracts the 'lastmod' date from the first <url> entry.
    (This function remains unchanged as it doesn't interact with Dapr)
    """
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()

        xml_content = response.content
        root = ET.fromstring(xml_content)
        
        namespaces = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        first_url_element = root.find('s:url', namespaces)

        if first_url_element is not None:
            lastmod_element = first_url_element.find('s:lastmod', namespaces)
            if lastmod_element is not None:
                return lastmod_element.text
            else:
                print("No <lastmod> element found within the first <url>.")
                return None
        else:
            print("No <url> element found in the sitemap.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the sitemap: {e}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing the XML content: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_db_date(db_table):
    """
    Fetches the most recent 'lastupdate' date from the specified database table using Dapr SDK binding.
    """
    try:
        with DaprClient() as d:
            # For query operations with bindings, the SQL goes into the metadata.
            # Dapr's PostgreSQL binding typically returns results in a 'result' key.
            # The Dapr SDK's invoke_binding method expects `data` as bytes or dict,
            # and `metadata` as a dictionary.
            resp = d.invoke_binding(
                binding_name=DAPR_BINDING_NAME,
                operation='query',
                metadata={'sql': f"SELECT lastupdate FROM {db_table} ORDER BY lastupdate DESC LIMIT 1;"}
            )
            
            # The response data from Dapr SDK is bytes, so decode it and parse JSON
            result_data = json.loads(resp.data.decode('utf-8'))

            if result_data and 'result' in result_data and len(result_data['result']) > 0:
                return result_data['result'][0]['lastupdate']
            else:
                print("No 'lastupdate' date found in the database.")
                return None

    except Exception as e:
        print(f"An error occurred while fetching the date from the database via Dapr SDK: {e}", file=sys.stderr)
        sys.exit(1) # Critical error, exit
    
def date_comparison(sitemap_date, db_date):
    # This function remains unchanged
    dt_with_tz = datetime.fromisoformat(sitemap_date)
    dt_pg_date = datetime.strptime(str(db_date), "%Y-%m-%d").date()

    print(f"Original string with timezone: {sitemap_date}")
    print(f"Parsed datetime with timezone: {dt_with_tz} (Type: {type(dt_with_tz)})")
    print(f"Original PostgreSQL date string: {db_date}")
    print(f"Parsed PostgreSQL date: {dt_pg_date} (Type: {type(dt_pg_date)})")

    date_from_tz_string = dt_with_tz.date()

    print(f"\nDate part from string with timezone: {date_from_tz_string}")
    print(f"Date part from PostgreSQL date string: {dt_pg_date}")

    if date_from_tz_string > dt_pg_date:
        print(f"Result: {date_from_tz_string} is AFTER {dt_pg_date}")
        return True
    elif date_from_tz_string < dt_pg_date:
        print(f"Result: {date_from_tz_string} is BEFORE {dt_pg_date}")
        return False
    else:
        print(f"Result: {date_from_tz_string} is the SAME DAY as {dt_pg_date}")
        return False
  
def load_into_db(db_table, JSON_FILE, SCRAPY_TARGET_PATH):
    """
    Function to load data from downloaded json into the database using Dapr SDK binding.
    """
    crawled_json_file = os.path.join(SCRAPY_TARGET_PATH, JSON_FILE)
    
    with open(crawled_json_file, "r") as f:
        docs = json.load(f)

    with DaprClient() as d:
        # TRUNCATE TABLE using Dapr "exec" operation
        print(f"Deleting all records from table '{db_table}' via Dapr SDK...")
        d.invoke_binding(
            binding_name=DAPR_BINDING_NAME,
            operation='exec',
            metadata={'sql': f"DELETE FROM {db_table};"}
        )
        print("Database table deleted successfully via Dapr SDK.")

        today = date.today()

        print("Inserting data into the database via Dapr SDK...")
        for doc in docs:
            url = doc["url"]
            text = doc["text"]
            
            cleaned_text = text.replace('\t', ' ').replace('\n', ' ')
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            text = cleaned_text

            # INSERT using Dapr "exec" operation with parameters
            # The 'payload' needs to be a dictionary with a 'params' key holding the list of values.
            # Dapr SDK requires data to be JSON-serializable if not bytes.
            payload = {
                "params": [url, text, str(today)] # Convert date to string for Dapr
            }
            
            d.invoke_binding(
                binding_name=DAPR_BINDING_NAME,
                operation='exec',
                metadata={'sql': f"""
                    INSERT INTO {db_table} (url, text, lastupdate)
                    VALUES ($1, $2, $3)
                """},
                data=json.dumps(payload).encode('utf-8') # SDK expects bytes for 'data'
            )
        print("Data loaded into the database successfully via Dapr SDK.")

def exec_scrapy_crawler():
    """
    Function to execute the Scrapy crawl command.
    (This function remains unchanged as it doesn't interact with Dapr)
    """
    try:
        initial_cwd = os.getcwd()

        os.chdir(SCRAPY_TARGET_PATH)
        print(f"Changed current working directory to: {os.getcwd()}")
        
        if os.path.exists(JSON_FILE):
            os.remove(JSON_FILE)
            print(f"Removed existing JSON file: {JSON_FILE}")
        else:
            print(f"JSON file does not exist, will create a new one: {JSON_FILE}")

        subprocess.run(["scrapy", "crawl", "dapr_docs_web", "-o", JSON_FILE], check=True)
        print("Scrapy crawl executed successfully.")

        os.chdir(initial_cwd)
        
    except OSError as e:
        print(f"Error changing directory to '{SCRAPY_TARGET_PATH}': {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing Scrapy crawl: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # 0) Wait for 5 minutes before running the pods logic
    WAIT_FOR_PODS = os.getenv("WAIT_FOR_PODS", "True").lower() == "true"
    if WAIT_FOR_PODS:
        print("Waiting for 5 min before running the pods logic...")
        time.sleep(300)
        print("Finished waiting.")

    # Get connection string via Dapr Secrets Building Block using SDK
    try:
        print(f"Attempting to retrieve secret '{DAPR_SECRET_NAME}' from store '{DAPR_SECRET_STORE_NAME}' using key '{DAPR_SECRET_KEY}' via Dapr SDK...")
        with DaprClient() as d:
            secret_response = d.get_secret(DAPR_SECRET_STORE_NAME, DAPR_SECRET_NAME)
            conn_str = secret_response.secret.get(DAPR_SECRET_KEY)
            if conn_str:
                print("Successfully retrieved database connection string via Dapr SDK Secrets (though not directly used by the binding invocation).")
            else:
                print(f"Secret key '{DAPR_SECRET_KEY}' not found in secret '{DAPR_SECRET_NAME}'. Available keys: {secret_response.secret.keys()}", file=sys.stderr)
                sys.exit(1) # Critical error if secret key is missing
    except Exception as e:
        print(f"Failed to retrieve database connection string via Dapr SDK Secrets: {e}", file=sys.stderr)
        sys.exit(1) # Critical error, exit

    # 1) Get the first 'lastmod' date from the sitemap
    sitemap_date = get_first_sitemap_date(SITEMAP_URL)
    if sitemap_date:
        print(f"The 'lastmod' date from the first URL in the sitemap is: {sitemap_date}")
    else:
        print("Could not retrieve the first date from the sitemap.")
        sys.exit(1) # Use sys.exit for consistency
    
    # 2) Check if sitemap.xml date data is more recent or there is no data in table
    # if database date data is older -> do nothing
    db_date = get_db_date(DB_TABLE)
    if db_date:
        print(f"The most recent 'lastupdate' date from the database is: {db_date}")
        if date_comparison(sitemap_date, db_date):
            print("The sitemap date is more recent than the database date, reloading data into the database.")
            exec_scrapy_crawler()
            load_into_db(DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH)
        else:
            print("The sitemap date is not more recent than the database date, no action taken.")
    else:
        print("Could not retrieve the date from the database, so it is empty (no rows).")
        exec_scrapy_crawler()
        load_into_db(DB_TABLE, JSON_FILE, SCRAPY_TARGET_PATH)

```

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