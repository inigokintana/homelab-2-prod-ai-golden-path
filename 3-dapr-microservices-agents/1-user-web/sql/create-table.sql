CREATE TABLE good_answers (
    id SERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating INT NOT NULL,
    timestamp TEXT NOT NULL, -- To store the timestamp of when the answer was saved
    language VARCHAR(10) NOT NULL -- To store the language of the answer
);
