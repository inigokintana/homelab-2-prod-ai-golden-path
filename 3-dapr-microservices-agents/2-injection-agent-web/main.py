import scrapera
import requests
import hashlib
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, LargeBinary, MetaData
#import torch
#from transformers import AutoTokenizer, AutoModel
#import numpy as np

# --- CONFIGURATION ---
BASE_URL = "https://docs.dapr.io/"
DB_URL = "postgresql+psycopg2://postgres:pgvector@localhost:15432/postgres"
TABLE_NAME = "web"
CHUNK_SIZE_CONFIG = 500  # Number of words per chunk

# --- EMBEDDING SETUP --- #pgai will be used to generate embeddings
#tokenizer = AutoTokenizer.from_pretrained("WhereIsAI/UAE-Large-V1")
#model = AutoModel.from_pretrained("WhereIsAI/UAE-Large-V1")

# def embed_text(text):
#     inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
#     with torch.no_grad():
#         outputs = model(**inputs)
#         embeddings = outputs.last_hidden_state[:, 0, :]
#     return embeddings.squeeze().numpy()

# --- CHUNKING ---
def chunk_text(text, chunk_size=CHUNK_SIZE_CONFIG):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# --- SCRAPING ---
def scrape_docs(base_url):
    docs = scrapera.scrape(base_url, recursive=True)
    return [(doc.url, doc.text_content()) for doc in docs if doc.text_content()]

# --- DB SETUP ---
engine = create_engine(DB_URL)
metadata = MetaData()

docs_table = Table(
    TABLE_NAME, metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("url", String, nullable=False),
    Column("chunk_hash", String, nullable=False),
    Column("text", Text, nullable=False),
#    Column("embedding", LargeBinary, nullable=False),
)

metadata.create_all(engine)

# --- SAVE CHUNK TO DB ---
def save_chunk_to_db(conn, url, text_chunk):
    #embedding = embed_text(text_chunk)
    chunk_hash = hashlib.sha256(text_chunk.encode()).hexdigest()
    conn.execute(docs_table.insert().values(
        url=url,
        chunk_hash=chunk_hash,
        text=text_chunk #,
        #embedding=embedding.tobytes()
    ))

# --- MAIN PIPELINE ---
def main():
    print("Scraping web...")
    all_docs = scrape_docs(BASE_URL)

    with engine.begin() as conn:
        for url, text in all_docs:
            chunks = chunk_text(text)
            for chunk in chunks:
                save_chunk_to_db(conn, url, chunk)
            print(f"Saved {len(chunks)} chunks from {url}")

if __name__ == "__main__":
    main()
