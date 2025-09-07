 /*
    Create vectorized table
    ------------------------
    This is the table that will be used to store the vectorized data.
    It is created with the `create_vectorizer` function from the `pgai` extension.
    The vectorizer will automatically vectorize the data in the `good_answers` table
    and store it in the `good_answers_embeddings` table.
    
    The vectorizer will use the `embedding_ollama` function to create embeddings
    using the `all-minilm` model with a dimension of 384.
    
    The chunking will be done using the `chunking_recursive_character_text_splitter`
    function, which will split the text into chunks based on characters.

    More info https://github.com/timescale/pgai

    See -- https://github.com/timescale/pgai/issues/858  --
    TimescaleDB images are released periodically and do not mantain pgAI version inside the image.
    Additionally,  before pgAI 0.10 we need to "CREATE EXTENSION IF NOT EXISTS ai CASCADE;" but 
    after pgAI 0.10 it is intalled outside the database with python.

    pgAI version > 0.10.0 was moved the vectorizer functionality out of the pgai postgres extension and into the pgai python library.
    This change allows the vectorizer to be used on more PostgreSQL cloud providers (AWS RDS, Supabase, etc.) and simplifies the installation and upgrade process.
    https://github.com/timescale/pgai/blob/main/docs/vectorizer/migrating-from-extension.md


 */

-- # https://github.com/timescale/pgai/blob/main/docs/vectorizer/document-embeddings.md
-- # https://github.com/timescale/pgai/tree/main/examples/embeddings_from_documents
-- # https://github.com/timescale/pgai/blob/main/docs/vectorizer/api-reference.md#ailoading_uri
-- # 
CREATE EXTENSION IF NOT EXISTS ai CASCADE;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;

-- File access
-- Verify PostgreSQL has read permissions for the document files. Ensure file paths are correct and accessible.
-- vectorizer table creation


SELECT ai.create_vectorizer( 
    'document_metadata'::regclass, 
    loading => ai.loading_uri(column_name => 'uri'), 
    parsing => ai.parsing_auto(), 
    chunking => ai.chunking_recursive_character_text_splitter( 
        chunk_size => 700, 
        separators => array[E'\n## ', E'\n### ', E'\n#### ', E'\n- ', E'\n1. ', E'\n\n', E'\n', '.', '?', '!', ' ', '', '|'] ), 
    embedding => ai.embedding_ollama('all-minilm', 384),
    destination => ai.destination_table('document_embeddings')
);
-- Check the status of the vectorizer
  SELECT * FROM ai.vectorizer_status;


-- advance query exxample
-- Find documents relevant to customers with pending support tickets 
-- SELECT c.name, d.title, e.chunk 
-- FROM customers c 
-- JOIN support_tickets t ON c.id = t.customer_id 
-- JOIN customer_documentation cd ON c.id = cd.customer_id 
-- JOIN document_embeddings e ON cd.document_id = e.id 
-- WHERE t.status = 'pending' 
-- ORDER BY e.embedding <=> <search_embedding> LIMIT 10;