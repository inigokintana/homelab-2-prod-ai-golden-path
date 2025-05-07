---
license: apache-2.0
task_categories:
- question-answering
- text-retrieval
language:
- en
tags:
- vector search
- semantic search
- retrieval augmented generation
size_categories:
- 1M<n<10M
---

## Overview

This dataset is a chunked version of a subset of data in the [Cosmopedia](https://huggingface.co/datasets/HuggingFaceTB/cosmopedia) dataset curated by Hugging Face.

Specifically, we have only used a subset of Wikihow articles from the Cosmopedia dataset, and each article has been split into chunks containing no more than 2 paragraphs.

## Dataset Structure

Each record in the dataset represents a chunk of a larger article, and contains the following fields:
- `doc_id`: A unique identifier for the parent article
- `chunk_id`: A unique identifier for each chunk
- `text_token_length`: Number of tokens in the chunk text
- `textlines`: The raw text of the chunk

## Usage

This dataset can be useful for evaluating and testing:
- Performance of embedding models and RAG
- Retrieval quality of Semantic Search
- Question-Answering performance

## Ingest Data

### create database
SET client_encoding = 'UTF8';

CREATE DATABASE cosmopedia WITH TEMPLATE = template0 ENCODING = 'UTF8';

ALTER DATABASE cosmopedia OWNER TO postgres;
\connect cosmopedia;
create extension vector;
CREATE SEQUENCE public.cosmopedia_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.cosmopedia (
    id integer DEFAULT nextval('public.cosmopedia_id_seq'::regclass) NOT NULL,
    doc_id integer NOT NULL,
    chunk_id integer NOT NULL,
    text_token_length integer NOT NULL,
    textlines text NOT NULL,
    textlines_embedding vector(1024) NOT NULL
);

ALTER TABLE public.cosmopedia OWNER TO postgres;



###

### Load CSV file into Postgresql vector with python calculating the embedding

```
import psycopg2
from sentence_transformers import SentenceTransformer
import csv

# --- Database Connection Details ---
DB_HOST = "localhost"
DB_PORT = 15432  # Default PostgreSQL port
DB_NAME = "cosmopedia"
DB_USER = "postgres"
DB_PASSWORD = "pgvector"

# --- CSV File Path ---
CSV_FILE_PATH = "cosmopedia-wikihow-chunked.csv"  # Replace with the actual path to your CSV file
# --- Embedding Model ---
#EMBEDDING_MODEL_NAME = "sentence-transformers/uae-large-v1"
#model = SentenceTransformer("WhereIsAI/UAE-Large-V1")
EMBEDDING_MODEL_NAME = "WhereIsAI/UAE-Large-V1"

def calculate_embeddings(texts, model_name=EMBEDDING_MODEL_NAME):
    """Calculates embeddings for a list of texts using the specified model."""
    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts)
    return embeddings

def connect_to_db():
    """Connects to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        cur = conn.cursor()
        return conn, cur
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return None, None

def insert_data_with_embedding(cur, doc_id, chunk_id, text_token_length, textlines, embedding):
    """Inserts a single record with its embedding into the cosmopedia table."""
    try:
        insert_query = """
            INSERT INTO cosmopedia (doc_id, chunk_id, text_token_length, textlines, textlines_embedding)
            VALUES (%s, %s, %s, %s, %s);
        """
        cur.execute(insert_query, (doc_id, chunk_id, text_token_length, textlines, embedding.tolist()))
    except psycopg2.Error as e:
        print(f"Error inserting data: {e}")
        raise  # Re-raise the exception to be caught in the main function

def process_csv_in_chunks(csv_path, embedding_model_name, db_conn, db_cursor, chunk_size=100):
    """Processes the CSV file line by line, calculates embeddings in chunks, and inserts into the database."""
    model = SentenceTransformer(embedding_model_name)
    texts_buffer = []
    data_buffer = []
    line_count = 0

    with open(csv_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) == 4:
                try:
                    doc_id = int(row[0])
                    chunk_id = int(row[1])
                    text_token_length = int(row[2])
                    textlines = row[3]

                    texts_buffer.append(textlines)
                    data_buffer.append((doc_id, chunk_id, text_token_length, textlines))
                    line_count += 1

                    if len(texts_buffer) >= chunk_size:
                        embeddings = model.encode(texts_buffer)
                        for i in range(len(data_buffer)):
                            doc_id, chunk_id, text_token_length, textlines = data_buffer[i]
                            embedding = embeddings[i]
                            insert_data_with_embedding(db_cursor, doc_id, chunk_id, text_token_length, textlines, embedding)
                        db_conn.commit()
                        print(f"Processed and inserted {line_count} lines.")
                        texts_buffer = []
                        data_buffer = []

                except ValueError:
                    print(f"Skipping invalid row: {row}")
                except psycopg2.Error as db_error:
                    db_conn.rollback()
                    print(f"Database error at line {line_count}: {db_error}")
                    # Decide whether to continue or break the process
                    break # Or you might want to continue to the next CSV line
            else:
                print(f"Skipping row with incorrect number of columns: {row}")

    # Process any remaining data in the buffers
    if texts_buffer:
        embeddings = model.encode(texts_buffer)
        for i in range(len(data_buffer)):
            doc_id, chunk_id, text_token_length, textlines = data_buffer[i]
            embedding = embeddings[i]
            insert_data_with_embedding(db_cursor, doc_id, chunk_id, text_token_length, textlines, embedding)
        db_conn.commit()
        print(f"Processed and inserted remaining {len(texts_buffer)} lines.")

def main():
    """Main function to process the CSV in chunks, calculate embeddings, and insert into PostgreSQL."""
    conn, cur = connect_to_db()
    if conn and cur:
        process_csv_in_chunks(CSV_FILE_PATH, EMBEDDING_MODEL_NAME, conn, cur, chunk_size=100)  # Adjust chunk_size as needed
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
```
### creta dab index

ALTER TABLE ONLY public.cosmopedia
    ADD CONSTRAINT cosmopedia_pkey PRIMARY KEY (id, doc_id, chunk_id);


## Sample Document

Documents in Postgresql Vector should look as follows:

cosmopedia=# select * from cosmopedia where id=1;
id, doc_id, chunk_id, text_token_length, textlines, textlines_embedding 
Notice textlines_embedding are the numbers between []
```
1 |      0 |        0 |               180 | Title: How to Create and Maintain a Compost Pile                                                                  
                                                                                                                                                                
                         +| [-0.17497899,0.6248427,0.045868732,-0.20711757,-0.13894314,0.43049517,-0.28702098,0.8313135,1.3853307,0.5429467,0.
                         ....
87439,-0.94952166,0.9143801,0.20949179,0.1730188,0.6060755,-1.0356452,-0.16030023,0.05246705]
    |        |          |                   |                                                                                                                   
                                                                                                                                                                
                         +| 
    |        |          |                   | Introduction:                                                                                                     
                                                                                                                                                                
                         +| 
    |        |          |                   | Composting is an easy and environmentally friendly way to recycle organic materials and create nutrient-rich soil 
for your garden or plants. By following these steps, you can learn how to build and maintain a successful compost pile that will help reduce waste and improve t
he health of your plants.+| 
    |        |          |                   |                                                                                                                   
                                                                                                                                                                
                         +| 
    |        |          |                   | **Step 1: Choose a Location **                                                                                    
                                                                                                                                                                
                         +| 
    |        |          |                   | Select a well-draining spot in your backyard, away from your house or other structures, as compost piles can produ
ce odors. Ideally, locate the pile in partial shade or a location with morning sun only. This allows the pile to retain moisture while avoiding overheating duri
ng peak sunlight hours.  +| 
    |        |          |                   |                                                                                                                   
                                                                                                                                                                
                         +| 
    |        |          |                   | _Key tip:_ Aim for a minimum area of 3 x 3 feet (0.9m x 0.9m) for proper decomposition; smaller piles may not gene
rate enough heat for optimal breakdown of materials.                                                                                                            
                          | 
(1 row)
```