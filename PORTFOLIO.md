# Atlas: document search with inspectable evidence

## Case study

**Problem.** Documents scattered across PDFs, websites, and Notion are difficult to search together. A generated answer without visible evidence is hard to trust.

**Implementation.** Atlas normalizes these sources into overlapping text chunks, embeds them locally, stores vectors and source metadata in Qdrant, and retrieves context for an LLM. The FastAPI service streams tokens to a browser interface that links numeric citations to exact evidence excerpts and PDF page numbers. Source selection narrows the search space.

**Engineering decisions.** Local embeddings avoid a per-request embedding API dependency. One container serves UI and API to simplify deployment. Stable content IDs make identical uploads idempotent. Owner-only ingestion and visibility filtering keep private uploads separate from public sample data. Streaming makes progress visible; empty retrieval produces an explicit insufficient-evidence answer. Source text is rendered without HTML interpretation.

**Tradeoffs.** This is a single-owner MVP with production-oriented controls. A production deployment still needs durable ingestion jobs, isolated PDF parsing, hardened network egress, stronger identity and abuse controls, automated backups, and broader quality evaluation. Citations enable inspection; they do not establish correctness by themselves.

## LinkedIn draft

I built Atlas, a RAG document chatbot that connects PDFs, websites, and Notion pages to searchable evidence.

The pipeline: extraction → overlapping chunks → local embeddings → Qdrant vector search → streamed LLM answers with inline citations.

The feature I focused on most is inspectability: you can open a citation and see the exact excerpt and PDF page behind an answer.

I also implemented source filtering, idempotent ingestion, private document access, request limits, and integration tests. Building it highlighted the gap between a working RAG demo and a production system: durable jobs, evaluation, isolation, and cost controls matter just as much as the model.

Tech: Python, FastAPI, Qdrant, FastEmbed, Docker, JavaScript, and an OpenAI-compatible LLM endpoint.

Live app: https://atlas-rag-kjkq.onrender.com
Source: https://github.com/adhilmohamed24/atlas-rag

The free hosting plan sleeps when idle, so the first visit can take a minute or more. Public demo answers use a shared daily quota; uploading documents requires owner access.

#AI #RAG #Python #MachineLearning #BuildInPublic

## Resume bullets

- Built a RAG application ingesting PDFs, web pages, and Notion into Qdrant using local text embeddings, source filtering, and page-aware metadata.
- Implemented FastAPI streaming responses with inline citations and an evidence viewer, plus access controls and idempotent document indexing.
- Added automated integration checks for retrieval visibility, authorization, ingestion boundaries, and streaming behavior; packaged the app for Docker deployment.

The public deployment uses Render, Qdrant Cloud, and Groq. Be ready to explain every stage, tradeoff, and test; this implementation was built with AI assistance. Notion ingestion requires a configured integration and shared page; live Notion verification is pending.
