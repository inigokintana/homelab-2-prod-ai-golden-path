import os
import psycopg2
from datetime import datetime
import hashlib # For content hashing, to detect actual content changes

# --- Configuration ---
DOCS_FOLDER = '/apps/docs'  # Make sure this path is correct relative to your script, or use an absolute path
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "pgvector"
DB_HOST = "localhost" # Or your database host
DB_PORT = "15432"      # Your database port

# --- Database Connection ---
def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Successfully connected to the database.")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

# --- Helper Functions ---
def calculate_file_hash(filepath):
    """Calculates the SHA256 hash of a file's content."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(8192) # Read in 8KB chunks
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def get_file_metadata(filepath):
    """Extracts basic metadata from a file."""
    stat_info = os.stat(filepath)
    filename = os.path.basename(filepath)
    # You might want to parse content_type more intelligently based on file extension
    # For simplicity, we'll infer it here
    content_type_map = {
    '.pdf': 'application/pdf',
    '.md': 'text/markdown',
    '.html': 'text/html',
    '.txt': 'text/plain',
    '.rtf': 'application/rtf', 
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.odt': 'application/vnd.oasis.opendocument.text',
    '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
    '.odp': 'application/vnd.oasis.opendocument.presentation',
    # Add more mappings as needed
    }
    file_extension = os.path.splitext(filename)[1].lower()
    content_type = content_type_map.get(file_extension, 'application/octet-stream') # Default if not found

    # Using file's modification time as a proxy for update detection,
    # and creation time for initial record.
    # We'll also calculate a content hash for more robust change detection.
    return {
        'uri': os.path.abspath(filepath), # Using absolute path as URI for local files
        'title': os.path.splitext(filename)[0], # Filename without extension as title
        'content_type': content_type,
        'created_at_fs': datetime.fromtimestamp(stat_info.st_ctime), # Creation time from filesystem
        'updated_at_fs': datetime.fromtimestamp(stat_info.st_mtime), # Last modification time from filesystem
        'content_hash': calculate_file_hash(filepath)
    }

# --- Main Sync Logic ---
def sync_docs_folder_with_db():
    """
    Scans the DOCS_FOLDER, compares files with database entries,
    and performs inserts/updates.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # 1. Get all current files in DOCS_FOLDER
        current_files_in_folder = {}
        for root, _, files in os.walk(DOCS_FOLDER):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    file_metadata = get_file_metadata(filepath)
                    current_files_in_folder[file_metadata['uri']] = file_metadata
                except Exception as e:
                    print(f"Warning: Could not get metadata for {filepath}: {e}")
                    continue

        # 2. Get all existing documents from the database
        db_documents = {}
        cur.execute("SELECT uri, updated_at, content_hash FROM document_metadata;")
        for uri, updated_at_db, content_hash_db in cur.fetchall():
            db_documents[uri] = {
                'updated_at_db': updated_at_db,
                'content_hash_db': content_hash_db
            }

        # 3. Process files (Insert/Update)
        for uri, folder_meta in current_files_in_folder.items():
            if uri not in db_documents:
                # File is new, insert it
                print(f"Inserting new document: {folder_meta['title']}")
                insert_query = """
                    INSERT INTO document_metadata (title, uri, content_type, created_at, updated_at, content_hash)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """
                cur.execute(insert_query, (
                    folder_meta['title'],
                    folder_meta['uri'],
                    folder_meta['content_type'],
                    folder_meta['created_at_fs'], # Use file system created_at
                    folder_meta['updated_at_fs'], # Use file system updated_at
                    folder_meta['content_hash']
                ))
            else:
                # File exists, check if updated
                db_meta = db_documents[uri]
                # Compare content hash first for robust detection, then fallback to modification time
                if folder_meta['content_hash'] != db_meta['content_hash_db']:
                    print(f"Updating document (content hash changed): {folder_meta['title']}")
                    update_query = """
                        UPDATE document_metadata
                        SET updated_at = %s, content_type = %s, content_hash = %s
                        WHERE uri = %s;
                    """
                    cur.execute(update_query, (
                        folder_meta['updated_at_fs'], # Update with file system modification time
                        folder_meta['content_type'],
                        folder_meta['content_hash'],
                        uri
                    ))
                elif folder_meta['updated_at_fs'] > db_meta['updated_at_db'].replace(tzinfo=None):
                    # Fallback check if filesystem mtime is newer, but hash is same (e.g., metadata change, or hash collision)
                    print(f"Updating document (mtime changed): {folder_meta['title']}")
                    update_query = """
                        UPDATE document_metadata
                        SET updated_at = %s, content_type = %s, content_hash = %s
                        WHERE uri = %s;
                    """
                    cur.execute(update_query, (
                        folder_meta['updated_at_fs'],
                        folder_meta['content_type'],
                        folder_meta['content_hash'],
                        uri
                    ))


        # 4. (Optional) Detect and handle deleted files
        # This part requires careful consideration as files might be temporarily moved or access denied.
        # It's safer to run this as a separate, less frequent cleanup if needed.
        # For now, we'll just print them.
        deleted_uris = set(db_documents.keys()) - set(current_files_in_folder.keys())
        if deleted_uris:
            print("\nDocuments found in DB but not in folder (potentially deleted/moved):")
            for uri in deleted_uris:
                print(f"  - {uri}")
                # Example: To delete them from DB (uncomment with caution!)
                delete_query = "DELETE FROM document_metadata WHERE uri = %s;"
                cur.execute(delete_query, (uri,))
                print(f"  - Deleted from DB: {uri}")


        conn.commit()
        print("Synchronization complete.")

    except Exception as e:
        conn.rollback() # Rollback on error to maintain data integrity
        print(f"An error occurred during synchronization: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("Database connection closed.")

# --- Main execution ---
if __name__ == "__main__":
    # Create the DOCS folder if it doesn't exist for testing purposes
    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)
        print(f"Created DOCS folder at: {DOCS_FOLDER}")

    # You might want to run this sync periodically (e.g., using a scheduler like `cron` or `systemd.timer`)
    # For a simple run:
    sync_docs_folder_with_db()

    # To demonstrate updates:
    # 1. Create a file in DOCS/test.txt
    # 2. Run script
    # 3. Modify DOCS/test.txt content (or just its modification time)
    # 4. Run script again to see it updated