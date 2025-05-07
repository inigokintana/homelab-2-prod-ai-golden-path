import psycopg
import random
import time
from pgvector.psycopg import register_vector
from typing import Optional, List, NamedTuple
from ollama import Client
from dataclasses import dataclass

@dataclass
class ChunkData:
    """Represents a chunk of text with its title and content."""
    title: str
    chunk: str

def create_db_connection() -> psycopg.Connection:
    """Create and return a database connection."""
    conn = psycopg.connect(
        # "postgres://postgres:postgres@localhost:5432/postgres"
        #"postgres://postgres:pgvector@localhost:15432/postgres"
        "postgres://postgres:pgvector@pgvector.pgvector.svc.cluster.local:5432/postgres"
        # Modify connection string as needed for your setup
    )
    register_vector(conn)
    return conn

def get_embedding(client: Client, text: str) -> list[float]:
    """Get embeddings using Ollama's all-minilm model."""
    response = client.embeddings(model='all-minilm', prompt=text)
    return response['embedding']

def get_relevant_chunks(cur: psycopg.Cursor, embedding: list[float], limit: int = 1) -> List[ChunkData]:
    """
    Retrieve the most relevant chunks based on vector similarity.
    
    Args:
        cur: Database cursor
        embedding: Query embedding vector
        limit: Number of chunks to retrieve
    
    Returns:
        List of ChunkData objects containing relevant chunks
    """
    query = """
    SELECT title, chunk
    FROM wiki_embeddings 
    ORDER BY embedding <=> %s::vector
    LIMIT %s
    """
    
    cur.execute(query, (embedding, limit))
    return [ChunkData(title=row[0], chunk=row[1]) for row in cur.fetchall()]

def format_context(chunks: List[ChunkData]) -> str:
    """
    Format the chunks into a single context string.
    
    Args:
        chunks: List of ChunkData objects
    
    Returns:
        Formatted context string
    """
    return "\n\n".join(f"{chunk.title}:\n{chunk.chunk}" for chunk in chunks)

def generate_rag_response(query_text: str) -> Optional[str]:
    """
    Generate a RAG response using pgai, Ollama embeddings, and database content.
    
    Args:
        query_text: The question or query to answer
    
    Returns:
        str: The generated response from the LLM
    """
    try:
        # Initialize Ollama client
        # client = Client(host='http://localhost:11434')
        
        
        client = Client(host='http://ollama.ollama.svc.cluster.local')

        with create_db_connection() as conn:
            with conn.cursor() as cur:
                # Get embeddings for the query using Ollama SDK
                query_embedding = get_embedding(client, query_text)
                
                # Get relevant chunks
                relevant_chunks = get_relevant_chunks(cur, query_embedding)
                
                # Format context
                context = format_context(relevant_chunks)
                
                # Print context for debugging (optional)
                print("Context provided to LLM:")
                print("------------------------")
                print(context)
                print("------------------------")
                
                # Construct prompt with context
                prompt = f"""Question: {query_text}

Please use the following context to provide an accurate response:

{context}

Answer:"""
                
                # Generate response using Ollama SDK
                response = client.generate(
                    #model='tinyllama',
                    model = 'llama3.2:1b',
                    prompt=prompt,
                    stream=False
                )
                
                return response['response']
                
    except Exception as e:
        print(f"Error generating RAG response: {e}")
        return None

def main():
    # Example usage
    questions = [
        "What can I use pgai for?",
        "What can I use AI for?",
        "What can I use postgres for?",
        "What can I use Dapr for?",
        "What can I use microk8s for?",
        "What can I use Ollama for?",
        "What can I use Python for?",
        "What can I use Timescale DB for?",
    ]
    
    while True:
        # Get a random question from the list
        question = random.choice(questions)
        
        # Print the question
        print("\n" + "="*50)
        print(f"Question: {question}")
        print("-"*50)
        
        # Generate and print the response
        response = generate_rag_response(question)
        if response:
            print("\nResponse:")
            print(response)
        else:
            print("Failed to generate response")
        # Wait for a while before the next question
        time.sleep(25)

if __name__ == "__main__":
    main()

