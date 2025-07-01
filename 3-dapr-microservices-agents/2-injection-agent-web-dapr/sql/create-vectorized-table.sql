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
 */

  SELECT ai.create_vectorizer(     
    'dapr_web'::regclass,     
    destination => 'dapr_web_embeddings',     
    embedding => ai.embedding_ollama('all-minilm', 384),     
    chunking => ai.chunking_recursive_character_text_splitter('text'));

-- Check the status of the vectorizer
  SELECT * FROM ai.vectorizer_status;
-- In case of error, you can drop the vectorizer and try again
-- SELECT ai.drop_vectorizer(1, drop_all=>true);


/* -- Example of creating a vectorizer with more options
  -- This is an example of how to create a vectorizer with more options.
  -- It includes loading, embedding, chunking, formatting, and destination options.
  -- The `grant_to` option is used to grant access to specific users.
  -- The `destination_table` option is used to specify the target schema and table for the vectorized data.
  -- More info https://github.com/timescale/pgai

  SELECT ai.create_vectorizer(
    'dapr_web'::regclass,
    name => 'dapr_web_embeddings',
    loading => ai.loading_column('contents'),
    embedding => ai.embedding_ollama('nomic-embed-text', 768),
    chunking => ai.chunking_character_text_splitter(128, 10),
    formatting => ai.formatting_python_template('title: $title published: $published $chunk'),
    grant_to => ai.grant_to('bob', 'alice'),
    destination => ai.destination_table(
        target_schema => 'postgres',
        target_table => 'dapr_web_embeddings_store',
        view_name => 'dapr_web_embeddings'
    )
  );
*/
