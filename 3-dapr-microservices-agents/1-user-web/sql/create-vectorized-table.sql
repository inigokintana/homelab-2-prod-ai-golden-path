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
 */

CREATE EXTENSION IF NOT EXISTS ai CASCADE;


SELECT ai.create_vectorizer(     
    'good_answers'::regclass,     
    destination => 'good_answers_embeddings',     
    embedding => ai.embedding_ollama('all-minilm', 384),     
    chunking => ai.chunking_recursive_character_text_splitter('answer'));

-- Check the status of the vectorizer
  SELECT * FROM ai.vectorizer_status;
-- In case of error, you can drop the vectorizer and try again
-- SELECT ai.drop_vectorizer(1, drop_all=>true);