import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import subprocess
import sys
import time
from flask import Flask, render_template, request, jsonify # Import jsonify for API responses
# from openai import OpenAI
# --- DAPR SDK IMPORTS ---
from dapr.clients import DaprClient 
from dapr.clients.grpc._request import ConversationInput
# --- END DAPR SDK IMPORTS ---

app = Flask(__name__)

# --- LLM Configuration (from config map) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST","http://ollama.ollama.svc.cluster.local")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL","llama3.2:1b") 
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "all-minilm") # e.g., nomic-embed-text, for RAG embeddings

# --- DAPR BINDING & SECRET CONFIG (as defined in your YAMLs) ---
DAPR_BINDING_NAME = os.getenv("DAPR_BINDING_NAME", "pgdb-agents-connection")
DAPR_OPENAI_AI_COMPONENT_NAME = os.getenv("DAPR_OPENAI_AI_COMPONENT_NAME", "openai-llm-model")
DAPR_SECRET_STORE_NAME = os.getenv("DAPR_SECRET_STORE_NAME", "kubernetes") # Typically 'kubernetes' in K8s
DAPR_SECRET_NAME = os.getenv("DAPR_SECRET_NAME", "pg-secret-dapr")
DAPR_SECRET_KEY = os.getenv("DAPR_SECRET_KEY", "connectionString")
# --- END DAPR BINDING & SECRET CONFIG ---

# --- Initialize Dapr Client globally ---
# This client will be used for all Dapr building block interactions
dapr_client = DaprClient()
print("DaprClient initialized successfully for Dapr building block interactions.")


# --- Helper Functions for LLM Calls ---

def get_rag_context(user_prompt: str) -> str:
    """
    Retrieves relevant context from your RAG database using Dapr Bindings.
    Assumes the PostgreSQL binding component (pgdb-agents-connection) is configured
    to connect to your database and handle the connection string from a secret.

    Args:
        user_prompt (str): The user's query to embed and search for context.

    Returns:
        str: A concatenated string of relevant documents or an empty string if none found.
    """
    rag_context = []
    
    try:
        # Step 1: Get embedding for the user prompt
        embedding = None
        if OLLAMA_HOST and OLLAMA_EMBEDDING_MODEL:
            try:
                ollama_embedding_url = f"http://{OLLAMA_HOST}:11434/api/embeddings"
                ollama_payload = {
                    "model": OLLAMA_EMBEDDING_MODEL,
                    "prompt": user_prompt
                }
                response = requests.post(ollama_embedding_url, json=ollama_payload)
                response.raise_for_status()
                embedding = response.json()['embedding']
            except requests.exceptions.RequestException as e:
                print(f"Error getting embedding from Ollama: {e}")
        elif OPENAI_API_KEY: # Use OpenAI for embeddings if configured, via direct API call or Dapr AI if available for embeddings
            try:
                # For embeddings with Dapr AI building block, you'd need a specific Dapr AI component for embeddings.
                # If not, direct OpenAI API call for embeddings is still viable.
                # Here, we'll keep the direct OpenAI call for embeddings as it's common.
                # If you want to Dapr-ize embeddings, you'd need a 'ai.openai.embeddings' component.
                openai_embedding_client = OpenAI(api_key=OPENAI_API_KEY) # Temporary client for embeddings
                embedding_model = "text-embedding-3-small" # Or your preferred OpenAI embedding model
                embedding_response = openai_embedding_client.embeddings.create(input=user_prompt, model=embedding_model)
                embedding = embedding_response.data[0].embedding
            except Exception as e:
                print(f"Error getting embedding from OpenAI for RAG: {e}")

        if embedding:
            # Step 2: Query pgvector for similarity using Dapr Bindings
            # PostgreSQL uses $1, $2, etc. for parameters in SQL.
            # The Dapr PostgreSQL binding will handle the connection string from its component definition.
            sql_query = f"""
                SELECT content, title, uri
                FROM document
                ORDER BY content_embedding <=> $1::vector
                LIMIT 5;
            """
            # Parameters for the SQL query
            # The Dapr binding expects parameters as a list
            params = [json.dumps(embedding)] # Convert list to JSON string for vector input

            # Payload for Dapr invoke_binding operation 'query'
            # 'query' operation is for SELECT statements
            payload = {
                "sql": sql_query,
                "params": params
            }

            print(f"Invoking Dapr binding '{DAPR_BINDING_NAME}' with query...")
            resp = dapr_client.invoke_binding(
                binding_name=DAPR_BINDING_NAME,
                operation='query', # Use 'query' for SELECT statements
                data=json.dumps(payload).encode('utf-8')
            )

            if resp.status.ok:
                # Dapr binding 'query' operation returns results in the 'data' field as JSON
                query_results = json.loads(resp.data.decode('utf-8'))
                if 'result' in query_results and isinstance(query_results['result'], list):
                    for row in query_results['result']:
                        # Assuming 'result' contains dictionaries like {'content': '...', 'title': '...', 'uri': '...'}
                        rag_context.append(f"Title: {row.get('title', 'N/A')}\nURI: {row.get('uri', 'N/A')}\nContent:\n{row.get('content', 'N/A')}\n---")
                else:
                    print(f"Dapr binding query result format unexpected: {query_results}")
            else:
                print(f"Dapr binding query failed: {resp.status.message}")
        else:
            print("No embedding generated for RAG context.")

    except Exception as e:
        print(f"An unexpected error occurred during RAG context retrieval via Dapr binding: {e}")

    if rag_context:
        return "\n\n" + "\n\n".join(rag_context)
    return ""

def call_ollama(prompt: str, language: str) -> str:
    """Calls the local Ollama LLM."""
    if not (OLLAMA_HOST and OLLAMA_MODEL):
        return "Ollama host or model not configured."

    ollama_url = f"http://{OLLAMA_HOST}:11434/api/generate"
    final_prompt = f"Please answer the following question in {language}. User query: {prompt}"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": final_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(ollama_url, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()['response']
    except requests.exceptions.RequestException as e:
        return f"Error calling Ollama: {e}. Check Ollama server status and network."

def call_openai(prompt: str, language: str, use_rag: bool = False) -> str:
    """
    Calls OpenAI's Chat Completion API using Dapr's AI building block.
    Assumes a Dapr AI component named DAPR_OPENAI_AI_COMPONENT_NAME (e.g., 'openai-llm-model')
    is configured and points to OpenAI with the necessary API key.
    """
    #https://www.diagrid.io/blog/dapr-1-15-release-highlights
    # from dapr.clients import DaprClient
    # from dapr.clients.grpc._request import ConversationInput

    # with DaprClient() as d:
    #     inputs = [
    #         ConversationInput(content="What's Dapr?", role='user', scrub_pii=True),
    #         ConversationInput(content='Give a brief overview.', role='user', scrub_pii=True),
    #     ]

    #     metadata = {
    #         'model': 'foo',
    #         'key': 'authKey',
    #         'cacheTTL': '10m',
    #     }

    #     response = d.converse_alpha1(
    #         name='echo', inputs=inputs, temperature=0.7, context_id='chat-123', metadata=metadata
    #     )

    #     for output in response.outputs:
    #         print(f'Result: {output.result}')

    if not DAPR_OPENAI_AI_COMPONENT_NAME:
        return "Dapr OpenAI AI component name not configured."

    # The messages format is consistent with OpenAI's API, Dapr's AI building block
    # expects this structure.
    messages = [
        {"role": "system", "content": f"You are a helpful assistant. Please answer concisely in {language}."},
        {"role": "user", "content": prompt}
    ]

    try:
        print(f"Invoking Dapr AI model '{DAPR_OPENAI_AI_COMPONENT_NAME}' for OpenAI...")
        # Use invoke_ai_model for high-level AI building block interaction
        # The model_id here refers to the Dapr AI component's metadata.name
        # The prompt is the list of messages
        # The parameters can include scrubPII (boolean value to enable obfuscation of sensitive information returning from the LLM.), 
        # temperature, top_p, etc.
        resp = dapr_client.converse_alpha1(
            model_id=DAPR_OPENAI_AI_COMPONENT_NAME,
            prompt=messages,
            parameters={"scrubPII": "true","temperature": 0.0} # Pass other LLM parameters here
        )

        if resp.status.ok:
            # The response from invoke_ai_model contains the LLM's output
            # The structure is typically {'response': 'LLM generated text'}
            ai_response = json.loads(resp.data.decode('utf-8'))
            return ai_response.get('response', "No response from AI model.")
        else:
            return f"Error calling Dapr AI model: {resp.status.message}"
    except Exception as e:
        return f"An unexpected error occurred during Dapr AI model call: {e}. Check Dapr sidecar and AI component."

# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the initial form."""
    return render_template('index.html', 
                           user_prompt_value="", 
                           llm_source_value="ollama_local",
                           language_value="english",
                           llm_answer_value="")

@app.route('/process_llm_prompt', methods=['POST'])
def process_prompt():
    """Receives form data, calls LLM, and re-renders page with answer."""
    user_prompt = request.form['user_prompt']
    llm_source = request.form['llm_source']
    language = request.form['language']
    
    llm_answer = "Error: Could not get an answer from the LLM."
    
    rag_context = ""

    if llm_source == 'ollama_local':
        print(f"Calling Ollama with RAG context for prompt: {user_prompt[:50]}...")
        rag_context = get_rag_context(user_prompt)
        final_prompt = f"{rag_context}\n\nUser Query: {user_prompt}" if rag_context else user_prompt
        llm_answer = call_ollama(final_prompt, language)

    elif llm_source == 'openai_local':
        print(f"Calling OpenAI (RAG) for prompt: {user_prompt[:50]}...")
        rag_context = get_rag_context(user_prompt)
        final_prompt = f"{rag_context}\n\nUser Query: {user_prompt}" if rag_context else user_prompt
        llm_answer = call_openai(final_prompt, language, use_rag=True)

    elif llm_source == 'openai_external':
        print(f"Calling OpenAI (External) for prompt: {user_prompt[:50]}...")
        llm_answer = call_openai(user_prompt, language, use_rag=False)

    else:
        llm_answer = "Invalid LLM source selected."

    return render_template('index.html',
                           user_prompt_value=user_prompt,
                           llm_source_value=llm_source,
                           language_value=language,
                           llm_answer_value=llm_answer)

@app.route('/save_feedback', methods=['POST'])
def save_feedback():
    """
    New endpoint to save feedback for good answers (4 or 5 stars) using Dapr Bindings.
    """
    data = request.get_json()
    
    prompt = data.get('prompt')
    answer = data.get('answer')
    rating = int(data.get('rating'))
    llm_source = data.get('llm_source') # Get the LLM source from feedback

    if not all([prompt, answer, rating, llm_source]):
        return jsonify({"status": "error", "message": "Missing prompt, answer, rating, or LLM source."}), 400

    # Only save answers with 4 or 5 stars
    if rating >= 4:
        try:
            # Use Dapr Bindings to insert into the good_answers table
            # PostgreSQL uses $1, $2, etc. for parameters in SQL.
            sql_insert_cmd = """
            INSERT INTO good_answers (prompt, answer, llm_source, rating, timestamp)
            VALUES ($1, $2, $3, $4, $5);
            """
            # Parameters for the SQL insert
            # The Dapr binding expects parameters as a list
            params = [prompt, answer, llm_source, rating, datetime.now().isoformat()]

            # Payload for Dapr invoke_binding operation 'exec'
            # 'exec' operation is for DML (INSERT, UPDATE, DELETE) statements
            payload = {
                "sql": sql_insert_cmd,
                "params": params
            }

            print(f"Invoking Dapr binding '{DAPR_BINDING_NAME}' with insert command...")
            resp = dapr_client.invoke_binding(
                binding_name=DAPR_BINDING_NAME,
                operation='exec', # Use 'exec' for DML statements
                data=json.dumps(payload).encode('utf-8')
            )

            if resp.status.ok:
                return jsonify({"status": "success", "message": "Feedback saved successfully via Dapr!"}), 200
            else:
                print(f"Dapr binding insert failed: {resp.status.message}")
                return jsonify({"status": "error", "message": f"Dapr binding error: {resp.status.message}"}), 500
        except Exception as e:
            print(f"An unexpected error occurred during Dapr binding insert: {e}")
            return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500
    else:
        return jsonify({"status": "info", "message": "Feedback not saved (rating less than 4 stars)."}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
# For production, do not use app.run(debug=True). 
# Instead, use a WSGI server like Gunicorn (e.g., gunicorn -w 4 app:app -b 0.0.0.0:5000) and potentially an Nginx reverse proxy.

