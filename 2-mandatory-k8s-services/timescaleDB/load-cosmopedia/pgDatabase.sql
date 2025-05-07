SET client_encoding = 'UTF8';

CREATE DATABASE cosmopedia WITH TEMPLATE = template0 ENCODING = 'UTF8';

ALTER DATABASE cosmopedia OWNER TO postgres;
\connect cosmopedia;
create extension vector;
CREATE SEQUENCE public.cosmopedia_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.cosmopedia (
    id integer DEFAULT nextval('public.cosmopedia_id_seq'::regclass) NOT NULL,
    doc_id integer NOT NULL,
    chunk_id integer NOT NULL,
    text_token_length integer NOT NULL,
    textlines text NOT NULL,
    textlines_embedding vector(1024) NOT NULL
);
ALTER TABLE ONLY public.cosmopedia
    ADD CONSTRAINT cosmopedia_pkey PRIMARY KEY (id, doc_id, chunk_id);

--CREATE INDEX idx_cosmopedia_doc_id ON public.cosmopedia USING btree (id);

ALTER TABLE public.cosmopedia OWNER TO postgres;