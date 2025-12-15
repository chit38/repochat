# Repochat: RAG-Powered Chatbot for GitHub Repositories

## Overview

Repochat is an intelligent Retrieval Augmented Generation (RAG) chatbot system designed to allow users to interact conversationally with the codebase of GitHub repositories. It automates the process of ingesting, processing, and indexing repository content, making it searchable and queryable through a natural language interface. This project transforms raw code into a knowledge base, enabling developers and users to quickly understand, debug, or explore repositories without manually sifting through files.   

## Quick Guide 

### 1️⃣ Clone the Repository
```
git clone <your-repo-url>
cd <your-repo-name>
```

### 2️⃣ Create Virtual Environment (Recommended)
```
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate           # Windows
```

### 3️⃣ Install Dependencies
```
pip install -r requirements.txt
```

### 4️⃣ Environment Setup

Create a .env file in the project root:

```
GOOGLE_API_KEY=your_google_api_key_here
```

### 5️⃣ Configuration

Ensure `config.ini` contains the registry file path, embedding model name, correct gemini model name and model parameters

The registry keeps track of onboarded repositories and their corresponding vector stores.

### 6️⃣ Run the App

#### 6.1 Using Gradio App
```
python app_gradio.py
```

You should see output similar to:

`Running on local URL: http://127.0.0.1:7860`

Open the URL in your browser.

Using the Gradio App

* Select an existing repository from the dropdown OR Paste a GitHub repository URL to onboard a new repo

* Click “Onboard / Load Repo”

* Start chatting with the codebase using natural language

#### 6.2 Using CLI

*  Run the main script (`main.py`)
   ```
   python main.py
   ```
*  Provide a GitHub repository URL when prompted.
*  The system will then ingest, process, and index the repository.
*  Once processed, you can interact with the chatbot to query the repository's content.


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



**Example Processed Repositories:**
The system has been demonstrated to process repositories like:
*   `https://github.com/DLR-RM/stable-baselines3`
*   `https://github.com/psf/requests`


---

