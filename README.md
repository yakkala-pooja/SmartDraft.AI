# SmartDraft.AI

> Transform ideas into structured documents with AI-powered semantic search and local language models.

SmartDraft.AI combines the power of semantic search with local large language models to help you generate professional, structured documents in seconds. Whether you're drafting reports, creating guides, or preparing content, SmartDraft.AI helps you go from concept to polished document with minimal effort.

![SmartDraft.AI](https://img.shields.io/badge/SmartDraft-AI-6366f1?style=for-the-badge) ![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square) ![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=flat-square) ![FAISS](https://img.shields.io/badge/FAISS-Vector_Search-green?style=flat-square) ![Ollama](https://img.shields.io/badge/Ollama-LLM_Integration-red?style=flat-square)

## Features

### Intelligent Document Generation
- **Semantic Search Engine**: Finds relevant content from a corpus of 492,887 WikiHow articles
- **Local LLM Integration**: Uses Ollama to run powerful language models locally for privacy and control (4 Models)
- **Structured Output**: Automatically formats content with summary, key insights, and conclusion
- **Memory-Efficient**: Optimized to run even on systems with limited resources

### Modern User Experience
- **Intuitive Web Interface**: Clean, responsive design with real-time document editing
- **Smart Model Selection**: Recommends appropriate models based on your system's available memory
- **Auto-Save**: Never lose your work with automatic document saving
- **Document History**: Access and continue working on previous documents
- **Export Options**: Save your documents as Markdown files

### Performance Optimizations
- **Caching System**: Reduces latency with smart caching of embeddings and search results
- **Memory Management**: Prevents crashes with intelligent memory requirement tracking
- **Background Preloading**: Speeds up initial load times by preloading resources
- **Retry Logic**: Improves reliability with automatic request retries and error handling

## Project Architecture

SmartDraft.AI consists of several integrated components:

1. **Data Processing Pipeline**: Processes and chunks WikiHow articles
2. **Vector Search Engine**: Embeds and indexes content for semantic retrieval
3. **Document Generation Engine**: Combines search results with LLM processing
4. **Web Interface**: Provides a user-friendly front-end experience

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/SmartDraft.AI.git
cd SmartDraft.AI

# Install dependencies
pip install -r requirements.txt

# Install Ollama for local LLM support
# Visit https://ollama.ai for installation instructions

# Download at least one supported model
ollama pull phi
```

## Quick Start

### Web Interface (Recommended)

```bash
# Start the web server
python web_interface.py
```

Then open your browser and navigate to: http://localhost:5000

### Command Line

```bash
# Generate a document with a specific prompt
python smart_draft.py "How to start a vegetable garden" --model phi

# Interactive mode for multiple document generation
python smart_draft.py --interactive

# Preload resources for faster startup
python smart_draft.py --interactive --preload
```

## Supported Models

SmartDraft.AI supports multiple local LLMs through Ollama:

| Model | Size | Memory Required | Best For |
|-------|------|----------------|----------|
| phi | 1.3B | 2GB | Fast drafts, limited hardware |
| tinyllama | 1.1B | 2GB | Quick generation, basic content |
| mistral | 7B | 7GB | Balanced performance and quality |
| llama3.2 | 8B | 8GB | High-quality output, complex topics |

## Behind the Scenes

SmartDraft.AI leverages several advanced technologies:

- **FAISS Vector Database**: Ultra-fast similarity search across 492,887 document chunks
- **Sentence Transformers**: High-quality semantic embeddings using all-MiniLM-L6-v2
- **React + Material UI**: Modern, responsive front-end interface
- **Flask**: Lightweight backend server with session management
- **Ollama**: Local LLM integration for privacy and control

## Challenges & Solutions

### Memory Management
**Challenge**: Running large language models locally requires significant RAM, causing crashes on systems with limited resources.

**Solution**: Implemented a memory management system that:
- Tracks RAM requirements for each model
- Checks available system memory before running models
- Provides clear warnings when memory is insufficient
- Recommends appropriate models based on available resources

### Performance Optimization
**Challenge**: Semantic search and LLM inference were causing high latency, especially on first use.

**Solution**: Developed a multi-tiered caching system:
- LRU cache for embeddings to speed up repeated queries
- Search results caching to avoid redundant vector searches
- Session caching to reduce disk I/O
- Background preloading of resources to reduce initial latency

### Error Handling
**Challenge**: Network issues, memory errors, and LLM failures were causing poor user experience.

**Solution**: Implemented comprehensive error handling:
- Retry logic with exponential backoff for API requests
- Proper timeouts to prevent hanging requests
- Detailed error messages for troubleshooting
- Graceful degradation when resources are limited

## Project Structure

```
SmartDraft.AI/
├── process_and_chunk_wikihow.py  # Data processing pipeline
├── embed_and_index.py            # Vector embedding and indexing
├── smart_draft.py                # Core document generation engine
├── web_interface.py              # Flask web server
├── search_wikihow.py             # Full-featured search tool
├── search_wikihow_lite.py        # Memory-efficient search tool
├── frontend/                     # React frontend application
├── templates/                    # HTML templates
├── wikihow_index/                # FAISS index and metadata
├── wikihow_processed/            # Processed document chunks
├── output/                       # Generated documents
└── evaluation/                   # User feedback and metrics
```

## Configuration

You can customize SmartDraft.AI by modifying these parameters:

- **Memory Requirements**: Adjust model memory settings in `smart_draft.py`
- **Caching Behavior**: Configure cache sizes and expiration in both Python and JavaScript files
- **UI Appearance**: Modify the Material UI theme in `frontend/src/App.js`
- **Search Parameters**: Change the number of chunks retrieved in document generation

## Advanced Usage

### Memory-Efficient Search

For systems with limited memory:

```bash
python search_wikihow_lite.py "How to grow tomatoes"
```

The lite version uses sample data (100 articles) for display but searches the full index (492,887 vectors) for accurate semantic matching.

### Performance Tuning

Clear the server-side cache when needed:

```bash
curl -X POST http://localhost:5000/clear-cache
```

### Document Evaluation

Collect feedback on generated documents:

```bash
python smart_draft.py --interactive --evaluate
```

## Contributing

Contributions are welcome! Here are some areas where help is needed:

- Improving memory efficiency for large indices
- Adding support for more local LLMs
- Enhancing the web UI with additional features
- Expanding the document formatting options

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The WikiHow dataset for providing rich, diverse content
- The FAISS team for their incredible vector search library
- The Sentence Transformers project for high-quality embeddings
- The Ollama project for making local LLMs accessible
