https://github.com/timescale/pgai/blob/main/docs/vectorizer/document-embeddings.md
https://github.com/timescale/pgai/tree/main/examples/embeddings_from_documents


# table
CREATE TABLE document (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    uri TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content_type TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER,
    access_level TEXT,
    tags TEXT[]
);

-- Example with rich metadata
INSERT INTO document (title, uri, content_type, owner_id, access_level, tags) VALUES
    ('Product Manual', 's3://my-bucket/documents/product-manual.pdf', 'application/pdf', 12, 'internal', ARRAY['product', 'reference']),
    ('API Reference', 's3://my-bucket/documents/api-reference.md', 'text/markdown', 8, 'public', ARRAY['api', 'developer']);

# vectorizer
SELECT ai.create_vectorizer(
    'document'::regclass,
    loading => ai.loading_uri(column_name => 'uri'),
    parsing => ai.parsing_auto(), -- Optional: auto-detects parser, this is the default and can also be omitted
    chunking => ai.chunking_recursive_character_text_splitter(
        chunk_size => 700,
        separators => array[E'\n## ', E'\n### ', E'\n#### ', E'\n- ', E'\n1. ', E'\n\n', E'\n', '.', '?', '!', ' ', '', '|']
    ),
    -- embedding => ai.embedding_openai('text-embedding-3-small', 768),
    -- embedding => ai.embedding_ollama('nomic-embed-text', 768, base_url => 'http://ollama:11434')
    embedding => ai.embedding_ollama('nomic-embed-text', 768)
    destination => ai.destination_table('document_embeddings')

# advance query
-- Find documents relevant to customers with pending support tickets
SELECT c.name, d.title, e.chunk 
FROM customers c
JOIN support_tickets t ON c.id = t.customer_id
JOIN customer_documentation cd ON c.id = cd.customer_id
JOIN document_embeddings e ON cd.document_id = e.id
WHERE t.status = 'pending'
ORDER BY e.embedding <=> <search_embedding>
LIMIT 10;