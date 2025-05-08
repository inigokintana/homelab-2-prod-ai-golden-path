
# 1 - Why TimescaleDB?

This is something we have [mentioned before](https://github.com/inigokintana/homelab-2-prod-ai-golden-path/tree/main?tab=readme-ov-file#38---why-timescaledb).

**Note** if you do not want to use TimescaleDB and pgai Vectorizer you can install pgai [from soure in postgres](https://github.com/timescale/pgai/blob/released/docs/install/source.md) and [create the vectorizer task worker](https://github.com/timescale/pgai)


# 2 - Technical prerequisites
- K8s Ollama service deployed and preloaded with specific llama3.2:1b LLM and all-minilm preloaded  
- K8s Timescaledb service image deployed with persitent data volume and pgai extension installed
    - CREATE EXTENSION IF NOT EXISTS ai CASCADE;
- pgai vectorizer worker configured and installed with:
    - pg connection string pwd
    - OLLAMA_HOST value is set [in vectorizer] (https://github.com/timescale/pgai/blob/main/docs/vectorizer-quick-start.md?ref=timescale.ghost.io) vs OPENAI where variable has to be [in DB container](https://github.com/timescale/pgai/blob/released/docs/vectorizer/quick-start-openai.md)
- Pending: 
    - vectorizer-worker container -password was stored in secret - how to get it from there secretRef:name: pgvectorconfig? 
    ````
    name: OLLAMA_HOST
          value: http://ollama.ollama.svc.cluster.local
          What if we use Dapr name resolution?? We would have OTM tracing
    ````
    - Disks in k8s:
    ````
    mkdir /mnt/pgdata
    cd /mnt
    chown 1000:1000 pgdata # because k command alias k='kubectl' is run from inigokintana user - not root
    ````
# 3  - How to load wikimedia wikipedia data?
wiki https://github.com/timescale/pgai/blob/released/README.md

CREATE EXTENSION IF NOT EXISTS ai CASCADE;
CREATE TABLE wiki (    id      TEXT PRIMARY KEY,    url     TEXT,    title   TEXT,    text    TEXT);

SELECT ai.load_dataset('wikimedia/wikipedia', '20231101.en', table_name=>'wiki', batch_size=>1000, max_batches=>1, if_table_exists=>'append');

SELECT ai.create_vectorizer(     'wiki'::regclass,     destination => 'wiki_embeddings',     embedding => ai.embedding_ollama('all-minilm', 384),     chunking => ai.chunking_recursive_character_text_splitter('text'));

 SELECT ai.delete_vectorizer (destination => 'wiki_embeddings');

-- Get an overview of all vectorizers
SELECT * FROM ai.vectorizer_status;
-- SELECT ai.drop_vectorizer(1, drop_all=>true);
-- Get an overview of all vectorizers
SELECT * FROM ai.vectorizer_status;


SELECT title, chunk FROM wiki_embeddings ORDER BY embedding <=> ai.ollama_embed('all-minilm', 'properties of light')LIMIT 1;

select count(*) from wiki;

INSERT INTO wiki (id, url, title, text) VALUES (1001,'https://en.wikipedia.org/wiki/Pgai', 'pgai - Power your AI applications with PostgreSQL', 'pgai is a tool to make developing RAG and other AI applications easier. It makes it simple to give an LLM access to data in your PostgreSQL database by enabling semantic search on your data and using the results as part of the Retrieval Augmented Generation (RAG) pipeline. This allows the LLM to answer questions about your data without needing to being trained on your data.');
select * from ai.vectorizer_status;

select count(*) from wiki;
SELECT *FROM wiki_embeddings where id=1001;
\d wiki_embeddings;
SELECT * FROM wiki_embeddings where id='1001';
-- SELECT title, chunk FROM wiki_embeddings ORDER BY embedding <=> ai.ollama_embed('all-minilm', 'properties of light')LIMIT 1;
-- SELECT title, chunk FROM wiki_embeddings ORDER BY embedding <=> ai.ollama_embed('all-minilm', 'AI tools')LIMIT 1;
-- SELECT answer->>'response' as summary FROM ai.ollama_generate('tinyllama', 'Summarize the following and output the summary in a single sentence: '|| (SELECT text FROM wiki WHERE title like 'pgai%')) as answer;



# 4 - How to load documents from local or S3 into Pg
- [Documents](https://www.timescale.com/blog/pgai-vectorizer-now-works-with-any-postgres-database?utm_source=timescaledb&utm_medium=youtube&utm_campaign=yt-channel-2023&utm_content=timescale-blog)
 - [pgai API reference](https://github.com/timescale/pgai/blob/released/docs/vectorizer/api-reference.md)

