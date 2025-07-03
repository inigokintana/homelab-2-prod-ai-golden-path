CREATE TABLE good_answers (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    answer TEXT NOT NULL,
    llm_source VARCHAR(50), -- To store which LLM (ollama_local, openai_local, openai_external) provided the answer
    rating INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
