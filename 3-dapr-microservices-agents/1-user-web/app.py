import os
import requests
import json # Import json for working with JSON data
import sys
from flask import Flask, render_template, request, jsonify # Import jsonify for API responses
from openai import OpenAI
import psycopg2
from dotenv import load_dotenv
from datetime import datetime # For timestamp

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- LLM Configuration (from environment variables) ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OLLAMA_HOST = os.getenv('OLLAMA_HOST')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL') # e.g., llama2, mistral
OLLAMA_EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text') # e.g., nomic-embed-text, for RAG embeddings

# --- RAG Database Configuration (from environment variables) ---
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# --- Initialize OpenAI Client ---
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client. Check OPENAI_API_KEY. Error: {e}")
        openai_client = None
else:
    print("Warning: OPENAI_API_KEY not set. OpenAI options will not work.")

# --- Helper Functions for LLM Calls ---

def get_rag_context(user_prompt: str) -> str:
    """
    Conceptual function to retrieve relevant context from your RAG database.
    This is where your pgvector/pgai logic would go.

    Args:
        user_prompt (str): The user's query to embed and search for context.

    Returns:
        str: A concatenated string of relevant documents or an empty string if none found.
    """
    if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT]):
        print("Warning: RAG DB credentials not fully set. Skipping RAG retrieval.")
        return ""

    rag_context = []
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        # Assuming pgvector is already registered or handled by your DB setup
        # For direct pgvector usage, you'd need: from pgvector.psycopg2 import register_vector; register_vector(conn)
        
        cur = conn.cursor()

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
        elif openai_client:
            try:
                embedding_model = "text-embedding-3-small" # Or your preferred OpenAI embedding model
                embedding_response = openai_client.embeddings.create(input=user_prompt, model=embedding_model)
                embedding = embedding_response.data[0].embedding
            except Exception as e:
                print(f"Error getting embedding from OpenAI: {e}")

        if embedding:
            embedding_str = json.dumps(embedding) 

            cur.execute(f"""
                SELECT content, title, uri
                FROM document
                ORDER BY content_embedding <=> %s::vector
                LIMIT 5;
            """, (embedding_str,))
            
            for row in cur.fetchall():
                rag_context.append(f"Title: {row[1]}\nURI: {row[2]}\nContent:\n{row[0]}\n---")
        else:
            print("No embedding generated for RAG context.")

    except psycopg2.Error as e:
        print(f"Database connection or query error during RAG retrieval: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during RAG context retrieval: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

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
    """Calls OpenAI's Chat Completion API."""
    if not openai_client:
        return "OpenAI API client not initialized. Check API key."

    messages = [
        {"role": "system", "content": f"You are a helpful assistant. Please answer concisely in {language}."},
        {"role": "user", "content": prompt}
    ]

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI API: {e}. Check API key and network."

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
    New endpoint to save feedback for good answers (4 or 5 stars).
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
        conn = None
        cur = None
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cur = conn.cursor()
            
            # Use a good_answers table for storing positive feedback
            # Make sure this table exists in your database:
            # CREATE TABLE good_answers (
            #     id SERIAL PRIMARY KEY,
            #     prompt TEXT NOT NULL,
            #     answer TEXT NOT NULL,
            #     llm_source VARCHAR(50),
            #     rating INT NOT NULL,
            #     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            # );
            
            cur.execute(
                """
                INSERT INTO good_answers (prompt, answer, llm_source, rating, timestamp)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (prompt, answer, llm_source, rating, datetime.now())
            )
            conn.commit()
            return jsonify({"status": "success", "message": "Feedback saved successfully!"}), 200
        except psycopg2.Error as e:
            print(f"Database error while saving feedback: {e}")
            return jsonify({"status": "error", "message": f"Database error: {e}"}), 500
        except Exception as e:
            print(f"An unexpected error occurred while saving feedback: {e}")
            return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    else:
        return jsonify({"status": "info", "message": "Feedback not saved (rating less than 4 stars)."}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
# For production, do not use app.run(debug=True). 
# Instead, use a WSGI server like Gunicorn (e.g., gunicorn -w 4 app:app -b 0.0.0.0:5000) and potentially an Nginx reverse proxy.