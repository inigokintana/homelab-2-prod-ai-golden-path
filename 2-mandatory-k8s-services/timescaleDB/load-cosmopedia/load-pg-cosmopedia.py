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