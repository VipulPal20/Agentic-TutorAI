# pgvector Similarity Search

pgvector is a PostgreSQL extension that stores embedding vectors and computes
similarity directly in the database. It adds a `vector` column type and distance
operators, including cosine distance written as `<=>`.

For fast approximate nearest-neighbour search, pgvector supports HNSW indexes.
An HNSW index built with `vector_cosine_ops` accelerates queries that order rows
by cosine distance, which is ideal for semantic retrieval where each document is
represented by an embedding produced by a model such as Gemini text-embedding-004.
