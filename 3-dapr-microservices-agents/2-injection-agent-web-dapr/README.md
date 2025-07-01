# 1- Objective

We want to load the Dapr official documentation and any documentation updates into local pgvector database where pgai vectorizer will automatically create a semantic content to ease LLM answers about any Dapr topic once every day.


# 2 - Project Structure

```
.
├── sql/                      # SQL scripts for table creation
├── k8s/
│   ├── base/                 # Base Kubernetes manifests
│   └── overlays/
│       ├── dev/              # DEV environment overlays
│       └── prod/             # PROD environment overlays
├── Dockerfile                # Docker build for the scraper
├── load-into-db-dapr.py      # Python scraper and logic
├── Tilfile                   # Tilt environment setup to sync python code directly into k8s container
└── README.md
```

# 3 - How we do this?
- Prerequsites: 
  - Ollama & pgvector & pgai must be installed as part of 2-mandatory-k8s-services section.
  - Install Kustomize: Kustomize introduces a template-free way to customize application configuration that simplifies the use of off-the-shelf applications, [see link](https://kustomize.io/). [Install Kustomize by downloading precompiled binaries](https://kubectl.docs.kubernetes.io/installation/kustomize/binaries/)
  - Tilt: Tilt powers microservice development and makes sure they behave! Run tilt up to work in a complete dev environment configured for your team, [see link](https://docs.tilt.dev/install.html#linux) and [this for MicroK8s](https://docs.tilt.dev/choosing_clusters.html#microk8s)

- In this section:
  - Create DB table: see sql/create-table.sql
  - Create vectorized table with semantic data: see sql/create-vectorized-table.sql
  - K8S in k8s/base directory:
    - binding-postgresql.yaml,  Dapr binding so we can easily access database using Dapr
    - configmap.yaml, with all the configuration variables
    - deployment.yaml, with a cronjob launching Docker/python logic once everyday
    - secret-binding.yaml, K8S secret with database connection string
    - secret-reader-role.yaml & secret-reader-rolebinding.yaml, role and role binding so python program can access secret
    - We use kustomize under k8s directory in order to be able to produce different customized values in DEV and PROD environmemts
      - DEV:
        - cd k8s
        - Edit overlays/dev/kustomization.yaml and overlays/dev/patch-deployment.yaml with your custom values
        - Exec: kustomize build overlays/dev  > overlays/dev/output_dev.yaml
        - kubectl apply -f k8s/overlays/dev/overlays/dev/output_dev.yaml or config Tilfile in order to be able to execute overlays/dev/output_dev.yaml file
      - PROD:
        - cd k8s
        - Edit overlays/prod/kustomization.yaml and overlays/prod/patch-deployment.yaml with your custom values
        - Exec: kustomize build overlays/prod  > overlays/rod/output_prod.yaml
        - kubectl apply -f k8s/overlays/prod/overlays/prod/output_prod.yaml or use argocd for gitops

  - Inside Dockerfile:
    - python:3.12-alpine
    - Scraper to be able to scrap Dapr web documentation
    - We create the scraper project inside Dockerfile
    - Dapr python sdk to read secrets and connect to postgresql binding - This makes application ease to migrate to other K8S environments with for example AWS secrets and other database

  - Inside Python logic:
    - 0) Wait for 30 seconds before running the pods logic
    - 1) Check we can get connection string via Dapr Secrets Building Block using SDK - Although not directly used by the binding invocation, it is a good practice to ensure the secret is available.
    - 2) Get the first 'lastmod' last modification date from the sitemap in Dapr documentation URL https://docs.dapr.io/en/sitemap.xml
    - 3) Check if sitemap.xml date data is more recent than the date in the database or there is no date in database table. In both cases, we delete table date and load all the documentation setting a database date. Any other case, do nothing.
    - 4) Dapr sidecar MUST shutdown after the cronjob has finished successfully, [see link](https://docs.dapr.io/operations/hosting/kubernetes/kubernetes-job/)
    
  - Tilt development environment: to sync directly python code from my IDE into k8s DEV environment, see [tilt api](https://docs.tilt.dev/api.html) and [example project](https://github.com/tilt-dev/pixeltilt):
    - Tiltfile:  
      - Adapt k8s_yaml inside Tilfile in order to be able to execute overlays/dev/output_dev.yaml 
      - adpat docker_build inside Tiltfile in order to rebuild images inside local registry of MikroK8s
    - Exec: "tilt up" to activate syncronization between your code and k8s containers

# 4 - Troubleshooting

- **Dapr sidecar does not shut down:**  
  Ensure your job sends a shutdown signal as described in the [Dapr docs](https://docs.dapr.io/operations/hosting/kubernetes/kubernetes-job/).

- **Cannot access secrets:**  
  Make sure the `secret-reader-role` and `secret-reader-rolebinding` are correctly applied in your namespace.

- **How to check cronjob -> job execution:**
```
k -n agents get cronjobs
NAME                    SCHEDULE    TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
dapr-sdk-docs-scraper   * 9 * * *   <none>     False     0        6h1m            23h


k -n agents get jobs
NAME                             STATUS     COMPLETIONS   DURATION   AGE
dapr-sdk-docs-scraper-29189259   Complete   1/1           35s        6h2m
dapr-sdk-docs-scraper-29189260   Complete   1/1           34s        6h1m


k -n agents logs -f jobs/dapr-sdk-docs-scraper-29189260 -c scraper
Waiting for 5 min before running the pods logic...
Finished waiting.
Attempting to retrieve secret 'pg-secret-dapr' from store 'kubernetes' using key 'connectionString' via Dapr SDK...
Successfully retrieved database connection string via Dapr SDK Secrets (though not directly used by the binding invocation).
The 'lastmod' date from the first URL in the sitemap is: 2025-06-26T02:05:41+01:00
SELECT lastupdate FROM dapr_web ORDER BY lastupdate DESC LIMIT 1;
<dapr.clients.grpc._response.BindingResponse object at 0x7ff71a4e2600>
Selected DB result: [['2025-06-30T00:00:00Z']]
Selected DB result date: 2025-06-30T00:00:00Z
-----------------
The most recent 'lastupdate' date from the database is: 2025-06-30T00:00:00Z
Original string with timezone: 2025-06-26T02:05:41+01:00
Parsed datetime with timezone: 2025-06-26 02:05:41+01:00 (Type: <class 'datetime.datetime'>)
Original PostgreSQL date string: 2025-06-30T00:00:00Z
Parsed PostgreSQL date: 2025-06-30 00:00:00+00:00 (Type: <class 'datetime.datetime'>)

Date part from string with timezone: 2025-06-26

Date part from PostgreSQL date string: 2025-06-30
Result: 2025-06-26 is BEFORE 2025-06-30
The sitemap date is not more recent than the database date, no action taken.
Shutting down Dapr sidecar gracefully...
Dapr sidecar shutdown requested successfully.
```