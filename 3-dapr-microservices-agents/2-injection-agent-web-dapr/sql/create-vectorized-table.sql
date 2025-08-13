 /*
    Create vectorized table
    ------------------------
    This is the table that will be used to store the vectorized data.
    It is created with the `create_vectorizer` function from the `pgai` extension.
    The vectorizer will automatically vectorize the data in the `dapr_web` table
    and store it in the `dapr_web_embeddings` table.
    
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
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;
-- CREATE EXTENSION IF NOT EXISTS ai CASCADE;

-- Create the vectorizer for the dapr_web table in pgAI 0.9.0 and earlier
/*
  SELECT ai.create_vectorizer(     
    'dapr_web'::regclass,     
    destination => 'dapr_web_embeddings',     
    embedding => ai.embedding_ollama('all-minilm', 384),     
    chunking => ai.chunking_recursive_character_text_splitter('text',chunk_size => 300,chunk_overlap => 50));
*/
-- Create the vectorizer for the dapr_web table in pgAI 0.10.0 and later
SELECT ai.create_vectorizer(     
    'dapr_web'::regclass, 
    loading => ai.loading_column('text'),
    destination => ai.destination_table (target_table => 'dapr_web_embeddings_store', 
                     view_name => 'dapr_web_embeddings'),     
    embedding => ai.embedding_ollama('all-minilm', 384),     
    chunking => ai.chunking_recursive_character_text_splitter(800));

-- Check the status of the vectorizer
  SELECT * FROM ai.vectorizer_status;
-- In case of error, you can drop the vectorizer and try again
-- SELECT ai.drop_vectorizer(1, drop_all=>true);


/* -- Example of creating a vectorizer with more options
  -- https://github.com/timescale/pgai/blob/main/docs/vectorizer/api-reference.md#install-or-upgrade-the-database-objects-necessary-for-vectorizer
*/
