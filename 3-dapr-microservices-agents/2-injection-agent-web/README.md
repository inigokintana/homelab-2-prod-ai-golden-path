
********
https://github.com/timescale/pgai


# Build on microk8s image register
microk8s enable registry
microk8s kubectl get pods -n container-registry
docker tag myapp:latest localhost:32000/myapp:latest
docker push localhost:32000/myapp:latest
or
microk8s.docker build -t localhost:32000/myapp:latest .
microk8s.docker push localhost:32000/myapp:latest


# Dockerfile
    scrapy startproject dapr_docs_web
    mv dapr_spider.py dapr_docs_web/dapr_docs_web/spiders/.
   

# crontab
    cd dapr_docs_web
    scrapy crawl dapr_docs_web -o dapr_docs_web.json
    # connect to DB and create table if not exist, truncate and create_vector if not exist
    # load using spider




CREATE TABLE IF NOT EXISTS dapr_web (
    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url TEXT,
    text TEXT
);

ALTER TABLE dapr_web ADD COLUMN lastupdate DATE;
update dapr_web  set lastupdate =  CURRENT_DATE - INTERVAL '8 days'; 
-> 2025-06-02

SELECT ai.create_vectorizer(     
    'dapr_web'::regclass,     
    destination => 'dapr_web_embeddings',     
    embedding => ai.embedding_ollama('all-minilm', 384),     
    chunking => ai.chunking_recursive_character_text_splitter('text'));

SELECT * FROM ai.vectorizer_status;
-- SELECT ai.drop_vectorizer(1, drop_all=>true);

-- All posibilities
SELECT ai.create_vectorizer(
    'dapr_web_chunks'::regclass,
    name => 'dapr_web_chunks_vectorizer',
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

load-into-db.py


*****
https://github.com/dapr/dapr no sitemap - we skip

****
kubectl apply -k k8s/overlays/dev
kubectl apply -k k8s/overlays/prod
*****
Pending use dapr to connect to postgresql

*****
cd k8s
kustomize build overlays/dev  > overlays/dev/output_dev.yaml
Adapt Tilfile in order to be able to execute overlays/dev/output_dev.yaml
                                change  image: localhost:32000/my-scraper-image in overlays/dev/output_dev.yaml
                                tilt api https://docs.tilt.dev/api.html
                                Tiltfile example project https://github.com/tilt-dev/pixeltilt


tilt up


To convert it into dapr database bulding block taking guess-films as example:
    - adapt requirements.txt 
    - :py import and logic
    - kubernetes resources - binding +  secret

kustomize build overlays/prod | kubectl apply -f -