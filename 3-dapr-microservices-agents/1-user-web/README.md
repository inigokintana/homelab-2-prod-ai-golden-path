# 1- Objective

We want this to happen in several steps:
- 1) User ask a question about Dapr.
- 2) The SLM inside OLLAMA to embed the user prompt.RAG database has SAME encoding all-minilm in vectorizer 
We can not use OpenAI to create prompt embedding with our RAG database because OpenAI does not support all-minilm encoding.
- 3) Make a semantic search in pgAI vectorized database.
- 4) Give the result back to Ollama SLM to get a proper answer based on our own data. Alternatively, we can choose OpenAI to make the step 4) but requires you to recreate the fake OpenAI API_KEY.
- 5) If user says answer is good enough we save it in good_answers table that can be used to improve future semantic search. We could save  prompts, embedded, answers, timestamps and user.

![Applications](../../docs/applications-view.png)

# 2 - How do we install it?

Check step 6) and specifically step 6.4) in:
- 1-IaC/AWS/opentofu/userdata.sh
- 1-IaC/OVH-Hetzner/userdata.sh
- 1-IaC/WSL2/install-in-WSL2.sh

Additionaly, to recreate an OpenAI API_KEY:
- To delete existing fake one: k -n agents delete secret generic openai-api-key
- To create a new one with valid OpenAI API_KEY: k -n agents create secret generic openai-api-key --from-literal=dapr=**test-change-it**
- Pod restart: k -n agents rollout restart deployment user-web-dapr

# 3 - Project Structure

```
.
├── sql/                      # SQL scripts for table creation
├── k8s/
│   ├── base/                 # Base Kubernetes manifests
│   └── overlays/
│       ├── dev/              # DEV environment overlays
│       └── prod/             # PROD environment overlays - TODO not really implemented
├── Dockerfile                # Docker build for the scraper
├── app-dapr.py               # Flask with HTML template and Python logic
├── Tilfile                   # Tilt environment setup to sync python code directly into k8s container
└── README.md
```

# 4 - How do we do this?
- Prerequsites: 
  - Ollama & pgvector & pgai must be installed as part of 2-mandatory-k8s-services section.
  - 3-dapr-microservices-agents/2-injection-agent-web-dapr injection agent must have inserted some data in dapr_web table.
  - Install Kustomize: Kustomize introduces a template-free way to customize application configuration that simplifies the use of off-the-shelf applications, [see link](https://kustomize.io/).
  - Tilt: Tilt powers microservice development and makes sure they behave! Run tilt up to work in a complete dev environment configured for your team, [see link](https://docs.tilt.dev/install.html#linux) and [this for MicroK8s](https://docs.tilt.dev/choosing_clusters.html#microk8s)

- In this section:
  - Create DB table: see sql/create-table.sql
  - Create vectorized table with semantic data: see sql/create-vectorized-table.sql
  - K8S in k8s/base directory:
    - binding-postgresql.yaml,  Dapr binding so we can easily access database using Dapr
    - configmap.yaml, with all the configuration variables
    - deployment.yaml, Flask/python web logic  
    - service.yaml - The k8s service in fromt of deployment
    - secret-binding.yaml, K8S secret with database connection string
    - secret-reader-role.yaml & secret-reader-rolebinding.yaml, role and role binding so python program can access secret
    - openai-llm-model.yaml - Dapr alplha state componet to talk to OpenAI - In the near future Dapr will have one to talk to Ollama
    - We use kustomize under k8s directory in order to be able to produce different customized values in DEV and PROD environmemts
      - DEV:
        - cd k8s
        - Edit overlays/dev/kustomization.yaml and overlays/dev/patch-deployment.yaml with your custom values
        - Exec: kustomize build overlays/dev  > overlays/dev/output_dev.yaml
        - kubectl apply -f k8s/overlays/dev/overlays/dev/output_dev.yaml or config Tilfile in order to be able to execute overlays/dev/output_dev.yaml file
      - PROD: - TODO not really implemented
        - cd k8s
        - Edit overlays/prod/kustomization.yaml and overlays/prod/patch-deployment.yaml with your custom values
        - Exec: kustomize build overlays/prod  > overlays/rod/output_prod.yaml
        - kubectl apply -f k8s/overlays/prod/overlays/prod/output_prod.yaml or use argocd for gitops

  - Inside Dockerfile:
    - python:3.12-alpine
    - Scraper to be able to scrap Dapr web documentation
    - We create the scraper project inside Dockerfile
    - Dapr python sdk to read secrets and connect to postgresql binding - This makes application ease to migrate to other K8S environments with for example AWS secrets and other database. Also Dapr alplha state componet to talk to OpenAI - In the near future Dapr will have one to talk to Ollama
    
  - Inside Python logic:
    - 1) User promt ask a question about Dapr.
    - 2) The SLM inside OLLAMA to embed the user prompt. RAG database has SAME encoding all-minilm in vectorizer 
We can not use OpenAI to create prompt embedding with our RAG database because OpenAI does not support all-minilm encoding.
    - 3) Make a semantic search in pgAI vectorized database.
    - 4) Give the result back to Ollama SLM to get a proper answer based on our own data. Alternatively, we can choose OpenAI to make the step 4) but requires you to recreate the fake OpenAI API_KEY.
    - 5) If user says answer is good enough we save it in good_answers table that can be used to improve future semantic search. We could save  prompts, embedded, answers, timestamps and user.


  - Tilt development environment: to sync directly python code from my IDE into k8s DEV environment, see [tilt api](https://docs.tilt.dev/api.html) and [example project](https://github.com/tilt-dev/pixeltilt):
    - Tiltfile:  
      - Adapt k8s_yaml inside Tilfile in order to be able to execute overlays/dev/output_dev.yaml 
      - adpat docker_build inside Tiltfile in order to rebuild images inside local registry of MikroK8s
    - Exec: "tilt up" to activate syncronization between your code and k8s containers

# 5 - Troubleshooting

- **Dapr sidecar does not shut down:**  
  Ensure your job sends a shutdown signal as described in the [Dapr docs](https://docs.dapr.io/operations/hosting/kubernetes/kubernetes-job/).

- **Cannot access secrets:**  
  Make sure the `secret-reader-role` and `secret-reader-rolebinding` are correctly applied in your namespace.

  Additionaly, to recreate an OpenAI API_KEY secret check in section 2) in this readme.

- **How to check Flask messages:**
```
k -n agents get pods
NAME                                   READY   STATUS      RESTARTS          AGE
user-web-dapr-5dc54b6c74-8k7t5         2/2     Running     127 (4h28m ago)   15d

k -n agents logs -f pods/user-web-dapr-5dc54b6c74-8k7t5  -c user-web-dapr

```

# 6 - Future enhancements - to do:
My local LLM answers with the following  dictionary structure. For the User point of view,  it should be enough to show the response part but we can use the other parts to give a better service. See how:
```
{
 "model":"llama3.2:1b",
 "created_at":"2025-07-16T06:46:20.465278525Z",
 "response":"Based on the provided information, here is what I know about .",
 "done":true,
 "done_reason":"stop",
 "context":[128006,...13],
 "total_duration":105933024287,
 "load_duration":24196466182,
 "prompt_eval_count":1168,
 "prompt_eval_duration":46930555244,
 "eval_count":224,
 "eval_duration":34771308893
 }
```
While the `response` field is what your users directly see, the other fields provide valuable metadata that professional services can absolutely utilize to enhance their offerings, improve user experience, and optimize their systems.

Here's a breakdown of how professional services might use each part of that dictionary structure:

* **`model`**: `"llama3.2:1b"`
    * **Professional Use:**
        * **A/B Testing & Model Comparison:** Service providers often experiment with different LLM models (or different versions/sizes of the same model). This field allows them to track which model generated a particular response, enabling them to compare performance, quality, and efficiency across various models.
        * **Cost Management:** If different models have different inference costs (even for local LLMs, resource consumption varies), this helps track and attribute resource usage.
        * **Troubleshooting & Debugging:** If a user reports an issue with a response, knowing the specific model used can help developers narrow down potential causes.
        * **Transparency (Internal):** For internal audits or compliance, knowing the model used for specific interactions can be crucial.

* **`created_at`**: `"2025-07-16T06:46:20.465278525Z"`
    * **Professional Use:**
        * **Performance Monitoring:** Track the exact time a response was generated. This is vital for calculating latency (how long it took from request to response), identifying performance bottlenecks, and ensuring SLAs (Service Level Agreements) are met.
        * **Auditing & Logging:** Essential for maintaining a complete log of interactions. This is critical for customer support, debugging, and compliance.
        * **Caching Strategies:** Helps in implementing intelligent caching mechanisms. If a similar query comes in shortly after, the `created_at` timestamp can inform whether a cached response is still fresh enough to serve.
        * **Session Reconstruction:** For complex, multi-turn conversations, this timestamp helps reconstruct the exact sequence of events.

* **`response`**: `"Based on the provided information, here is what I know about ."`
    * **Professional Use:**
        * **Direct User Display:** As you mentioned, this is the primary content presented to the end-user.
        * **Content Moderation & Filtering:** Automated systems can analyze the response content for inappropriate or harmful language before it's displayed to the user.
        * **Response Quality Evaluation:** Used in conjunction with user feedback mechanisms (e.g., "thumbs up/down" buttons) to assess the quality and relevance of the LLM's output.
        * **Follow-up Actions:** The content can trigger subsequent actions, such as presenting related articles, suggesting next steps, or escalating to human support if the LLM couldn't provide a satisfactory answer.

* **`done`**: `true`
    * **Professional Use:**
        * **Stream Management:** When streaming responses (character by character or word by word), this boolean indicates the completion of the entire response. This allows the client-side application to know when to stop waiting for more data, close connections, or disable loading indicators.
        * **Error Handling:** If `done` is `false` but no more data is received, it could indicate a network issue or an LLM error, prompting error handling routines.
        * **UI Updates:** Triggering final UI updates, like enabling input fields again or showing a "response complete" message.

* **`done_reason`**: `"stop"`
    * **Professional Use:**
        * **Understanding LLM Behavior:** Provides insight into *why* the LLM stopped generating. Common reasons include:
            * `"stop"`: The LLM completed its thought or reached a natural end.
            * `"length"`: The LLM hit its maximum token limit. This is crucial for prompt engineering – if `length` is frequent, prompts might need to be shorter or the max token setting increased.
            * `"user_canceled"`: The user interrupted the generation.
            * `"error"`: An internal error occurred during generation.
        * **Prompt Engineering & Optimization:** If many responses are `done_reason: "length"`, it signals that the model isn't able to fully answer within the given constraints, leading to incomplete answers and potentially frustrated users.
        * **User Experience Feedback:** In cases of `length`, the UI could inform the user that the response was truncated and suggest rephrasing or a follow-up query.
        * **Automated Retries:** For certain `done_reason` values (like `error`), a professional service might automatically retry the request.

* **`context`**: `[128006,...13]`
    * **Professional Use:**
        * **State Management & Multi-Turn Conversations:** This is a numerical representation of the conversation history or "state" that the LLM uses internally. For professional services building conversational AI, this `context` array is vital.
        * **Session Continuity:** When a user continues a conversation, this `context` can be sent back to the LLM to maintain the conversational flow and memory. Without it, each turn would be treated as a new, unrelated query.
        * **Debugging & Reproducibility:** If a user reports an issue with a particular conversation, having the `context` allows developers to replay the conversation and debug why the LLM responded in a certain way.
        * **Cost Optimization (Advanced):** In some LLM architectures, re-using context can be more efficient than sending the entire conversational history with each turn.

* **`total_duration`**: `105933024287` (nanoseconds)
    * **Professional Use:**
        * **Performance Metrics & Monitoring:** This is a key metric for understanding the overall latency of the service. High `total_duration` indicates slow responses, leading to poor user experience.
        * **SLA Compliance:** Essential for ensuring the service meets its defined performance agreements.
        * **Resource Allocation:** Helps identify if more computing resources are needed to handle the load effectively.
        * **Cost Analysis:** Directly relates to the computational resources consumed, allowing for more accurate cost attribution.

* **`load_duration`**: `24196466182` (nanoseconds)
    * **Professional Use:**
        * **Cold Start Optimization:** This specifically measures the time it takes for the model to be loaded into memory and ready for inference. A high `load_duration` often indicates "cold start" issues, where the model isn't actively running.
        * **Infrastructure Scaling:** If `load_duration` is consistently high, it might indicate that the infrastructure needs to pre-load models or scale up more quickly.
        * **System Responsiveness:** Helps differentiate between general processing time and the time spent just getting the model ready.

* **`prompt_eval_count`**: `1168`
    * **Professional Use:**
        * **Prompt Complexity & Token Count Tracking:** This indicates the number of tokens (or parts of words) in the input prompt that the LLM had to process.
        * **Cost Estimation (API-based LLMs):** For commercial APIs, token count directly translates to cost. Even for local LLMs, it correlates with computational effort.
        * **Prompt Engineering Optimization:** Large `prompt_eval_count` can indicate overly verbose prompts, which can be optimized for efficiency and cost.
        * **Input Validation:** Helps identify unusually long or complex prompts that might need specific handling.

* **`prompt_eval_duration`**: `46930555244` (nanoseconds)
    * **Professional Use:**
        * **Input Processing Performance:** Measures how long it takes the LLM to process the input prompt. High values here could indicate issues with input tokenization or the initial processing stage.
        * **Bottleneck Identification:** Helps pinpoint if the "thinking" part of the LLM (processing the prompt) is taking longer than the "generating" part (creating the response).

* **`eval_count`**: `224`
    * **Professional Use:**
        * **Output Token Count:** This indicates the number of tokens in the generated response.
        * **Response Verbosity Analysis:** Helps understand how verbose the LLM is being. Services might want to limit this to keep responses concise or to manage bandwidth.
        * **Cost Estimation (API-based LLMs):** Again, directly related to cost for commercial APIs.

* **`eval_duration`**: `34771308893` (nanoseconds)
    * **Professional Use:**
        * **Output Generation Performance:** Measures the time taken to generate the actual response tokens. This is a direct indicator of the LLM's inference speed.
        * **Streaming Performance:** For streaming applications, this duration is critical for understanding the "time to first token" and the overall flow of the streamed content.
        * **Hardware Sizing:** Helps determine if the current hardware can handle the desired generation speed.

By analyzing these additional fields, professional services can:

1.  **Improve User Experience:** By optimizing for speed, responsiveness, and completeness of answers.
2.  **Optimize Costs:** By identifying inefficiencies in model usage, prompt design, and resource allocation.
3.  **Enhance Reliability:** By monitoring for errors, tracking performance deviations, and quickly debugging issues.
4.  **Drive Product Development:** By understanding how different models and prompt strategies perform, informing future feature development and improvements.
5.  **Ensure Compliance & Auditing:** By maintaining detailed logs of interactions and their characteristics.

In essence, these "other parts" transform a simple LLM response into a rich data point for analytics, monitoring, and operational excellence.