# Spec 005: RAG Document Ingestion & Knowledge Retrieval

## Status: Baseline Implemented (Advanced Embeddings in Backlog)

## Overview
Allows ingesting reference documents into MongoDB, chunking text, and retrieving relevant snippets to ground the assistant's replies during chat conversations.

## Requirements
1. **Document Ingestion**:
   - Accepts title, raw text content, and optional metadata.
   - Splits text into overlapping chunks (~150 words per chunk with 25 words overlap).
   - Persists document structure in MongoDB `documents` collection.
2. **Context Retrieval**:
   - Evaluates search queries against chunked knowledge entries.
   - Returns top-$K$ scoring chunks.
3. **Prompt Augmentation**:
   - Injects retrieved text into LLM system prompt: `"Use the following knowledge context to answer:\n[Title]: Text..."`.

## API Contracts
- `POST /api/documents`:
  - Request: `{ title: string, content: string }`
  - Response: `{ status: "ingested", document: Document }`
