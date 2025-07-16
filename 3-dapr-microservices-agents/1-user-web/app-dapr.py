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
OLLAMA_DAPR_SERVICE_NAME = os.getenv("OLLAMA_DAPR_SERVICE_NAME","ollama-llm-dapr.ollama")
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
        sqlCmd = ("SELECT  text,embedding <=> ai.ollama_embed('all-minilm', '{user_prompt}') FROM dapr_web_embeddings ORDER BY embedding LIMIT 5;".format(user_prompt=user_prompt))
        payload = {'sql': sqlCmd}
        print(payload, flush=True)
        print(f"Invoking Dapr binding '{DAPR_BINDING_NAME}' with query...")
        resp = dapr_client.invoke_binding(
            binding_name=DAPR_BINDING_NAME,
            operation='query', # Use 'query' for SELECT statements
            binding_metadata=payload # Deprecated but often still needed for binding specific context
            )
        
        #print(resp, flush=True)
        #print(resp.text(), flush=True)
        if resp.data:
        #if resp.text():
            # print(resp.data, flush=True)
            # #Dapr binding 'query' operation returns results in the 'data' field as JSON
            query_results = json.loads(resp.data.decode('utf-8'))
            print("Dapr binding query result:", query_results, flush=True)
            if query_results:
                for row in query_results:
                    # Assuming 'result' contains dictionaries like {'content': '...', 'title': '...', 'uri': '...'}
                    rag_context.append(f"Content:\n{row}\n---")
            else:
                print(f"Dapr binding query result format unexpected: {query_results}")
        else:
            print(f"Dapr binding query failed or returned no data.")
    except Exception as e:
        print(f"An unexpected error occurred during RAG context retrieval via Dapr binding: {e}")
    
    if rag_context:
        return "\n\n" + "\n\n".join(rag_context)
    return ""

def call_ollama(prompt: str, language: str) -> str:
    """Calls the local Ollama LLM."""
    if not (OLLAMA_HOST and OLLAMA_MODEL):
        return "Ollama host or model not configured."
    # ollama_url = f"http://{OLLAMA_HOST}:11434/api/generate"
    final_prompt = f"Please answer the following question in {language}. User query: {prompt}"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": final_prompt,
        "stream": False
    }
    
    try:
        # Define the Dapr service invocation endpoint
        response = dapr_client.invoke_method(
            app_id=OLLAMA_DAPR_SERVICE_NAME,
            method_name='api/generate',
            data=json.dumps(payload),
            http_verb='POST',
            timeout=600 # Timeout in seconds, we have a small LLM and low memory, so it requires some time to generate a response
        )
        # Print the response
        # print(resp.content_type, flush=True)
        # print(resp.text(), flush=True)
        # print(str(resp.status_code), flush=True)
        time.sleep(2)
        return response.text()

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

    if not DAPR_OPENAI_AI_COMPONENT_NAME:
        return "Dapr OpenAI AI component name not configured."

    inputs = [
        ConversationInput(content=prompt, role='user', scrub_pii=True),
        # ConversationInput(content='Give a brief overview.', role='user', scrub_pii=True),
    ]

    metadata = {
        'model': 'GPT4',  # This should match the model configured in your Dapr AI component
        'key': 'authKey',
        'cacheTTL': '10m',
    }

    try:
        print(f"Invoking Dapr AI model '{DAPR_OPENAI_AI_COMPONENT_NAME}' for OpenAI...")
        # Use invoke_ai_model for high-level AI building block interaction
        # The model_id here refers to the Dapr AI component's metadata.name
        # The prompt is the list of messages
        # The parameters can include scrubPII (boolean value to enable obfuscation of sensitive information returning from the LLM.), 
        # temperature, top_p, etc.
        # see python SDK https://www.diagrid.io/blog/dapr-1-15-release-highlights
        # https://www.diagrid.io/blog/dapr-1-15-release-highlights
        # resp = dapr_client.converse_alpha1(
        #     name="OpenAi",
        #     model_id=DAPR_OPENAI_AI_COMPONENT_NAME, # type: ignore
        #     prompt=messages,
        #     parameters={"scrubPII": "true","temperature": 0.0} # Pass other LLM parameters here
        # )
        resp = dapr_client.converse_alpha1(
            name=DAPR_OPENAI_AI_COMPONENT_NAME,
            inputs=inputs,
            temperature=0.7,  # Adjust temperature as needed
            # context_id='chat-123',  # Optional context ID for conversation tracking
            metadata=metadata  # Additional metadata for the AI model
        )

        # Check if outputs are present in the response
        if hasattr(resp, "outputs") and resp.outputs:
            # Return the result from the first output
            return resp.outputs[0].result
        else:
            return "Error: No response from Dapr AI model."
    except Exception as e:
        return f"An unexpected error occurred during Dapr AI model call: {e}. Check Dapr sidecar and AI component."


#######################
# --- Flask Routes ---
#######################
@app.route('/healthz')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

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
        print(f"Calling Ollama with RAG context for prompt: {user_prompt[:50]}...", flush=True)
        rag_context = get_rag_context(user_prompt)
        final_prompt = f"{rag_context}\n\nUser Query: {user_prompt}" if rag_context else user_prompt
        print(f"Final prompt for Ollama: {final_prompt[:500]}...", flush=True)
        llm_answer = call_ollama(final_prompt, language)
        print(f"Calling Ollama with RAG context for prompt: {llm_answer[:500]}...", flush=True)

    elif llm_source == 'openai_local':
        print(f"Calling OpenAI (RAG) for prompt: {user_prompt[:50]}...")
        rag_context = get_rag_context(user_prompt)
        final_prompt = f"{rag_context}\n\nUser Query: {user_prompt}" if rag_context else user_prompt
        llm_answer = call_openai(final_prompt, language, use_rag=True)

    # elif llm_source == 'openai_external':
    #     print(f"Calling OpenAI (External) for prompt: {user_prompt[:50]}...")
    #     llm_answer = call_openai(user_prompt, language, use_rag=False)

    else:
        llm_answer = "Invalid LLM source selected."

    llm_answer_dict = json.loads(llm_answer)
    return render_template('index.html',
                           user_prompt_value=user_prompt,
                           llm_source_value=llm_source,
                           language_value=language,
                           llm_answer_value=llm_answer_dict["response"] if "response" in llm_answer_dict else llm_answer_dict.get("result", "No response from LLM."))

@app.route('/save_feedback', methods=['POST'])
def save_feedback():
    """
    New endpoint to save feedback for good answers only (4 or 5 stars) using Dapr Bindings.
    """
    data = request.get_json()
    print(data, flush=True)
    prompt = data.get('prompt')
    print(prompt, flush=True)
    answer = data.get('answer')
    print(answer, flush=True)
    rating = int(data.get('rating'))
    print(rating, flush=True)
    language = data.get('language') # Get the LLM source from feedback
    print(language, flush=True)

    if not all([prompt, answer, rating, language]):
        return jsonify({"status": "error", "message": "Missing prompt, answer, rating, or language."}), 400

    # Only save answers with 4 or 5 stars
    if rating >= 4:
        try:
            # Use Dapr Bindings to insert into the good_answers table
            # PostgreSQL uses $1, $2, etc. for parameters in SQL.
            sql_insert_cmd = """
            INSERT INTO good_answers (prompt, answer, rating, timestamp, language)
            VALUES ($1, $2, $3, $4, $5);
            """
            # Parameters for the SQL insert
            # The Dapr binding expects parameters as a list
            params = [prompt, answer, rating, datetime.now().isoformat(), language]

            # Payload for Dapr invoke_binding operation 'exec'
            # 'exec' operation is for DML (INSERT, UPDATE, DELETE) statements
            payload = {
                "sql": sql_insert_cmd,
                "params": params
            }

            print(f"Invoking Dapr binding '{DAPR_BINDING_NAME}' with insert command...")
            dapr_client.invoke_binding(
                binding_name=DAPR_BINDING_NAME,
                operation='exec', # Use 'exec' for DML statements
                data=json.dumps(payload).encode('utf-8'),
                binding_metadata={'sql': sql_insert_cmd, 'params': json.dumps(params)} # Deprecated but often still needed for binding specific context
            )

            # If no exception was raised, assume success
            return jsonify({"status": "success", "message": "Feedback saved successfully via Dapr!"}), 200
        except Exception as e:
            print(f"An unexpected error occurred during Dapr binding insert: {e}")
            return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500
    else:
        return jsonify({"status": "info", "message": "Feedback not saved (rating less than 4 stars)."}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
# For production, do not use app.run(debug=True). 
# Instead, use a WSGI server like Gunicorn (e.g., gunicorn -w 4 app:app -b 0.0.0.0:5000) and potentially an Nginx reverse proxy.

