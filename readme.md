# Repochat: RAG-Powered Chatbot for GitHub Repositories

## Overview

Repochat is an intelligent Retrieval Augmented Generation (RAG) chatbot system designed to allow users to interact conversationally with the codebase of GitHub repositories. It automates the process of ingesting, processing, and indexing repository content, making it searchable and queryable through a natural language interface. This project transforms raw code into a knowledge base, enabling developers and users to quickly understand, debug, or explore repositories without manually sifting through files.   

## Features

### 1. Repository Onboarding & Ingestion
*   **Seamless Cloning:** Automatically clones specified GitHub repositories to a local directory.
*   **File Scanning:** Recursively scans the cloned repository to identify all relevant files.
*   **Comprehensive Metadata Extraction:** For each file, it extracts and saves detailed metadata, including:
    *   `filename`
    *   `path` (relative to the repository root)
    *   `sha256` hash
    *   `is_binary` flag
    *   `language` (inferred from file extension)
    *   `line_count`
    *   This metadata is stored in a `metadata.json` file for easy access.
*   **Registry Management:** Maintains a `processed_repos.json` registry to keep track of repositories that have already been ingested and processed, preventing redundant work. This registry stores the repository URL, local path, collection name, processing date, and status.

### 2. Intelligent Content Processing & Chunking
*   **Universal Chunker:** Employs a `UniversalChunker` to break down file content into smaller, semantically meaningful chunks, optimized for retrieval.
*   **Configurable Chunk Size:** Chunks are generated with a `max_tokens` limit to ensure they are suitable for embedding models and LLM context windows.
*   **Smart File Skipping:** Efficiently skips irrelevant files and directories (e.g., `node_modules`, `.git`, `dist`, `build`, `__pycache__`, `venv`, common image/archive extensions) to focus on valuable source code and documentation.
*   **Content-Aware Chunking Strategies:** Applies different chunking logic based on file type for optimal results:
    *   **Python (`.py`):** Uses `chunk_python_code` for structured code parsing.
    *   **Markdown (`.md`, `.markdown`):** Uses `chunk_markdown` to respect document structure.
    *   **JSON (`.json`):** Uses `chunk_json` for structured data.
    *   **Plain Text/Logs (`.txt`, `.log`, `.rst`):** Uses `chunk_text`.
    *   **Other Code Files (`.js`, `.ts`, `.java`, `.go`, `.rs`, `.rb`, `.php`, `.c`, `.cpp`, `.h`):** Defaults to `chunk_by_lines` as a robust fallback (with potential for future Tree-sitter integration).
    *   **General Fallback:** `chunk_text` for any unhandled file types.
*   **Chunk Enrichment:** Each generated chunk is enriched with contextual metadata, including `file_path`, `file_name`, `file_extension`, `language`, and the original file's metadata (`og_meta`), enhancing retrieval accuracy.

### 3. Vector Embedding & Storage
*   **Vector Store Integration:** Utilizes a `VectorStore` (likely built on ChromaDB) to store the processed chunks and their vector embeddings.
*   **Embedding Model Support:** Configurable to use various embedding models (e.g., `sentence-transformers/all-mpnet-base-v2`) to convert text chunks into numerical representations.

### 4. RAG Chatbot Interaction
*   **Conversational Interface:** Once a repository is processed, a `RAGChatbot` can be initialized, allowing users to ask questions about the codebase in natural language.
*   **Intelligent Retrieval:** Queries are used to retrieve the most relevant code chunks from the vector store.
*   **LLM Integration:** The retrieved chunks, along with the user's query, are fed into a large language model (configured via `GOOGLE_API_KEY` and `LLM_MODEL`) to generate accurate and contextually relevant answers.

## How It Works (High-Level Flow)

1.  **User Input:** The user provides a GitHub repository URL.
2.  **Onboarding Check:** The system checks if the repository has been processed before.
3.  **Ingestion:** If new, the repository is cloned, and file metadata is extracted and saved.
4.  **Processing:** The `UniversalChunker` scans the cloned files, intelligently chunks their content based on file type, skips irrelevant files, and enriches each chunk with metadata.
5.  **Embedding & Indexing:** The enriched chunks are then converted into vector embeddings using a specified model and stored in a vector database (e.g., ChromaDB).      
6.  **Chatbot Initialization:** A `RAGChatbot` is set up, pointing to the processed repository's vector collection.
7.  **Query & Response:** When a user asks a question, the chatbot retrieves relevant chunks from the vector store and uses an LLM to formulate an answer based on those chunks.

## Technologies Used (Implied)

*   **Python:** Core programming language.
*   **GitPython:** For cloning repositories.
*   **ChromaDB:** Likely used as the vector database for storing embeddings.
*   **Sentence Transformers:** For generating text embeddings.
*   **Google API / Gemini:** For the Large Language Model (LLM) integration.
*   **ConfigParser:** For managing configuration settings.
*   **os, json, datetime, Path:** Standard Python libraries for file system operations, data serialization, and date handling.

## Usage

To use Repochat, you would typically:

1.  Run the main script (`main.py` or `onboarding.py` if run directly).
2.  Provide a GitHub repository URL when prompted.
3.  The system will then ingest, process, and index the repository.
4.  Once processed, you can interact with the `RAGChatbot` to query the repository's content.

**Example Processed Repositories:**
The system has been demonstrated to process repositories like:
*   `https://github.com/DLR-RM/stable-baselines3`
*   `https://github.com/psf/requests`

---