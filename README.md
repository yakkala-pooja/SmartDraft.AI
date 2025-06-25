# SmartDraft.AI

A project for processing, embedding, and searching WikiHow articles for semantic search and text generation.

## Project Structure

- `process_and_chunk_wikihow.py`: Processes and chunks WikiHow articles from the original dataset
- `embed_and_index.py`: Generates embeddings and builds a FAISS index for similarity search
- `search_wikihow.py`: Command-line tool for searching the WikiHow corpus
- `search_wikihow_lite.py`: Lightweight version of the search tool for systems with limited memory
- `smart_draft.py`: Document generation tool that uses semantic search and local LLMs
- `web_interface.py`: Flask web application for document generation with auto-save and export features
- `wikihow_data/`: Directory containing the original WikiHow dataset
- `wikihow_processed/`: Directory containing processed and chunked WikiHow articles
- `wikihow_index/`: Directory containing the FAISS index and metadata
- `output/`: Directory for generated documents and session data
- `evaluation/`: Directory for evaluation metrics and feedback
- `templates/`: HTML templates for the web interface

## Data Processing Pipeline

1. **Processing and Chunking**: The `process_and_chunk_wikihow.py` script processes the raw WikiHow dataset, extracts relevant fields, cleans the text, and chunks articles into 150-300 word segments while preserving sentence boundaries.

2. **Embedding and Indexing**: The `embed_and_index.py` script generates dense embeddings for each chunk using the `all-MiniLM-L6-v2` sentence transformer model and builds a FAISS index for fast similarity search.

3. **Searching**: The `search_wikihow.py` script provides a command-line interface for searching the WikiHow corpus using semantic similarity.

4. **Document Generation**: The `smart_draft.py` script combines semantic search with local LLMs to generate structured documents based on user prompts.

## Installation

```bash
pip install -r requirements.txt
```

For document generation, you'll also need to install [Ollama](https://ollama.ai/) and download at least one of the supported models:

```bash
# After installing Ollama, download a model:
ollama pull phi
```

## Usage

### 1. Process and Chunk WikiHow Articles

```bash
python process_and_chunk_wikihow.py
```

This script will:
- Load the WikiHow dataset from `wikihow_data/WikiHow-Final.json`
- Extract relevant fields (prompt, text, title, format)
- Clean the text content
- Chunk articles into 150-300 word segments
- Save the processed chunks to `wikihow_processed/` directory

### 2. Generate Embeddings and Build Index

```bash
python embed_and_index.py
```

This script will:
- Load the processed chunks from `wikihow_processed/`
- Generate embeddings using the `all-MiniLM-L6-v2` model
- Build a FAISS index (HNSW by default) for fast similarity search
- Save the index and metadata to `wikihow_index/` directory

### 3. Search the WikiHow Corpus

For systems with ample memory (8GB+ RAM):
```bash
# Search with a query
python search_wikihow.py "How to grow tomatoes"

# Interactive mode
python search_wikihow.py --interactive

# Show example queries
python search_wikihow.py
```

For systems with limited memory:
```bash
# Search with a query using the lightweight version
python search_wikihow_lite.py "How to grow tomatoes"

# Interactive mode with lightweight version
python search_wikihow_lite.py --interactive
```

The lite version uses the sample data (100 articles) for displaying results, but still searches the full index for accurate semantic matching.

### 4. Generate Structured Documents (CLI)

SmartDraft.AI can generate structured documents using semantic search and local language models:

```bash
# Generate a document with a specific prompt
python smart_draft.py "How to start a vegetable garden" --model phi --output garden_guide.md

# Interactive mode for multiple document generation
python smart_draft.py --interactive

# Specify number of content chunks to retrieve
python smart_draft.py "How to learn piano" --chunks 5

# Enable evaluation metrics collection
python smart_draft.py --interactive --evaluate
```

Supported local models (via Ollama):
- phi
- tinyllama
- mistral
- llama2

Each generated document includes:
- Summary
- Key Insights (2-4 bullet points)
- Conclusion

### 5. Web Interface

SmartDraft.AI includes a web interface for document generation with auto-save and export features:

```bash
# Start the web server
python web_interface.py
```

Then open your browser and navigate to: http://localhost:5000

The web interface provides:
- Document generation with model selection
- Markdown editor for refining generated content
- Auto-save functionality
- Export to Markdown
- Document history management
- Evaluation metrics collection

## Features

### Document Generation
- Semantic search to find relevant content
- Local LLM processing for document creation
- Structured output with summary, insights, and conclusion
- Markdown formatting

### User Experience
- Command-line interface for quick document generation
- Web interface for interactive document creation
- Auto-save drafts to prevent data loss
- Export to Markdown format
- Document history and retrieval

### Evaluation
- Relevance rating system (1-5 scale)
- Time-saving metrics collection
- Performance benchmarking tools

## Configuration

You can modify the following configuration parameters in the scripts:

- `process_and_chunk_wikihow.py`:
  - `MIN_CHUNK_SIZE`: Minimum chunk size in words (default: 150)
  - `MAX_CHUNK_SIZE`: Maximum chunk size in words (default: 300)

- `embed_and_index.py`:
  - `MODEL_NAME`: Sentence transformer model to use (default: 'all-MiniLM-L6-v2')
  - `BATCH_SIZE`: Batch size for embedding generation (default: 1000)
  - `USE_HNSW`: Whether to use HNSW index or FlatL2 index (default: True)

- `search_wikihow.py` and `search_wikihow_lite.py`:
  - `MODEL_NAME`: Sentence transformer model to use (default: 'all-MiniLM-L6-v2')
  - `--top` or `-k`: Number of results to return (default: 5)
  
- `smart_draft.py`:
  - `DEFAULT_MODEL`: Default local LLM to use (default: 'phi')
  - `AVAILABLE_MODELS`: Supported models list
  - `--chunks` or `-c`: Number of content chunks to retrieve (default: 3)
  - `--no-markdown`: Disable markdown formatting
  - `--evaluate` or `-e`: Enable evaluation metrics collection

- `web_interface.py`:
  - Default port: 5000
  - Default host: 0.0.0.0 (accessible from other devices on the network)

## Directory Structure

- `wikihow_data/`: Raw WikiHow dataset
- `wikihow_processed/`: Processed and chunked WikiHow articles
- `wikihow_index/`: FAISS index and metadata
  - `wikihow.index`: FAISS index file
  - `metadata.pkl`: Metadata and original text chunks
  - `sample_query.py`: Example script for querying the index
