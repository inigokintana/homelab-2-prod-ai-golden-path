import json
import psycopg2
import re

# --- CONFIG ---
#DB_URL = "postgresql+psycopg2://postgres:pgvector@localhost:15432/postgres"
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "pgvector",
    "host": "localhost",
    "port": 15432,
}

# pgai vectorizer can do the chunck splitig as well
#CHUNK_SIZE = 500  # word count

# --- LOAD DATA ---
with open("dapr_docs_web/dapr_docs_web.json", "r") as f:
    docs = json.load(f)

# def chunk_text(text, chunk_size=500):
#     words = text.split()
#     chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
#     return chunks

# --- DB CONNECTION ---
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

for doc in docs:
    url = doc["url"]
    text = doc["text"]
    # cleaning \n \t with spaces 
    cleaned_text = text.replace('\t', ' ').replace('\n', ' ')
    # cleaning spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    text = cleaned_text
    #chunks = chunk_text(text, CHUNK_SIZE)
    
    #for i, chunk in enumerate(chunks):
        # cursor.execute("""
        #     INSERT INTO dapr_doc_chunks (url, chunk_id, chunk, word_count, embedding)
        #     VALUES (%s, %s, %s, %s, pgai.embed('WhereIsAI/UAE-Large-V1', %s))
        # """, (url, i, chunk, len(chunk.split()), chunk))
    cursor.execute("""
        INSERT INTO dapr_web (url, text)
        VALUES (%s, %s)
    """, (url, text))

conn.commit()
cursor.close()
conn.close()
