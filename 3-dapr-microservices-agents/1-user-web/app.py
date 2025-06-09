import os
import requests
from flask import Flask, render_template, request
from openai import OpenAI
import psycopg2 # For PostgreSQL connection (and pgvector if using)
from dotenv import load_dotenv # For loading environment variables from .env file

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
        # This part requires an embedding model. For Ollama, you can call its embeddings API.
        # For OpenAI, you'd use openai_client.embeddings.create.
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
                # Use OpenAI's embedding model if Ollama embedding is not available
                # (e.g., "text-embedding-3-small")
                embedding_model = "text-embedding-3-small"
                embedding_response = openai_client.embeddings.create(input=user_prompt, model=embedding_model)
                embedding = embedding_response.data[0].embedding
            except Exception as e:
                print(f"Error getting embedding from OpenAI: {e}")

        if embedding:
            # Step 2: Query pgvector for similarity
            # Ensure your 'document' table has a 'content_embedding' column of type 'vector(N)'
            # N must match your embedding model's dimension (e.g., 1536 for text-embedding-ada-002, 4096 for some Ollama)
            # You might need to cast embedding to text for psycopg2 then to vector in SQL
            embedding_str = json.dumps(embedding) # Convert list to JSON string for vector input

            # Example query (adjust table/column names as per your RAG setup)
            cur.execute(f"""
                SELECT content, title, uri
                FROM document
                ORDER BY content_embedding <=> %s::vector
                LIMIT 5;
            """, (embedding_str,))
            
            for row in cur.fetchall():
                # Assuming 'content' is the actual text, 'title' and 'uri' are metadata
                rag_context.append(f"Title: {row[1]}\nURI: {row[2]}\nContent:\n{row[0]}\n---")
        else:
            print("No embedding generated for RAG context.")

    except psycopg2.Error as e:
        print(f"Database connection or query error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during RAG context retrieval: {e}")
    finally:
        if conn:
            cur.close()
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
        "stream": False # Set to True for streaming responses
    }
    
    try:
        response = requests.post(ollama_url, json=payload, timeout=300) # Added timeout
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
            model="gpt-3.5-turbo", # You can change this to gpt-4 or other models
            messages=messages,
            temperature=0.7 # Adjust creativity
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
                           llm_source_value="ollama_local", # Default selection
                           language_value="english",         # Default selection
                           llm_answer_value="")

@app.route('/process_llm_prompt', methods=['POST'])
def process_prompt():
    """Receives form data, calls LLM, and re-renders page with answer."""
    user_prompt = request.form['user_prompt']
    llm_source = request.form['llm_source']
    language = request.form['language']
    
    llm_answer = "Error: Could not get an answer from the LLM."
    
    # Placeholder for RAG context
    rag_context = ""

    # --- Call LLM based on selection ---
    if llm_source == 'ollama_local':
        print(f"Calling Ollama with RAG context for prompt: {user_prompt[:50]}...")
        # Get RAG context if applicable
        rag_context = get_rag_context(user_prompt)
        final_prompt = f"{rag_context}\n\nUser Query: {user_prompt}" if rag_context else user_prompt
        llm_answer = call_ollama(final_prompt, language)

    elif llm_source == 'openai_local':
        print(f"Calling OpenAI (RAG) for prompt: {user_prompt[:50]}...")
        # Get RAG context if applicable
        rag_context = get_rag_context(user_prompt)
        final_prompt = f"{rag_context}\n\nUser Query: {user_prompt}" if rag_context else user_prompt
        llm_answer = call_openai(final_prompt, language, use_rag=True)

    elif llm_source == 'openai_external':
        print(f"Calling OpenAI (External) for prompt: {user_prompt[:50]}...")
        llm_answer = call_openai(user_prompt, language, use_rag=False)

    else:
        llm_answer = "Invalid LLM source selected."

    # Re-render the template with the answer and submitted values
    return render_template('index.html',
                           user_prompt_value=user_prompt,
                           llm_source_value=llm_source,
                           language_value=language,
                           llm_answer_value=llm_answer)

if __name__ == '__main__':
    # Run Flask app locally
    # For production, use a WSGI server like Gunicorn
    app.run(debug=True, host='0.0.0.0', port=5000)