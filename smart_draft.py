import os
import sys
import argparse
import logging
import json
import time
import psutil
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default paths
INDEX_DIR = Path('wikihow_index')
INDEX_PATH = INDEX_DIR / 'wikihow_faiss.index'
SAMPLE_PATH = INDEX_DIR / 'wikihow_sample.json'
MODEL_NAME = 'all-MiniLM-L6-v2'

# LLM configuration
DEFAULT_MODEL = "phi"  # Default local model to use
AVAILABLE_MODELS = ["phi", "tinyllama", "mistral", "llama3.2"]  # Supported models

# Model memory requirements (approximate in GB)
MODEL_MEMORY_REQUIREMENTS = {
    "phi": 2,
    "tinyllama": 2,
    "mistral": 7,
    "llama3.2": 8
}

# Template for the LLM prompt
PROMPT_TEMPLATE = """You are SmartDraft.AI — an intelligent assistant that helps users generate structured documents based on their ideas and related content.
Generate a document with the following sections:

Summary: A brief, clear overview of the topic.

Key Insights: 2–4 bullet points capturing practical, analytical, or useful takeaways.

Conclusion: A wrap-up that encourages reflection, action, or next steps.

User Request:
{user_prompt}

Related Context:
{retrieved_chunks}

Respond clearly and concisely. Use professional, general-audience language."""

# Markdown formatting template
MARKDOWN_TEMPLATE = """# Summary
{summary}

## Key Insights
{key_insights}

## Conclusion
{conclusion}
"""

# Global variables for lazy loading
_index = None
_sample_data = None
_model = None
_embedding_cache = {}  # Cache for embeddings
_search_results_cache = {}  # Cache for search results

def check_memory_requirements(model_name: str) -> bool:
    """Check if the system has enough memory for the model."""
    try:
        # Get available memory in GB
        mem = psutil.virtual_memory()
        available_memory_gb = mem.available / (1024 ** 3)
        
        # Get model memory requirement
        required_memory_gb = MODEL_MEMORY_REQUIREMENTS.get(model_name, 4)
        
        # Check if we have enough memory (with a 20% buffer)
        has_enough_memory = available_memory_gb >= (required_memory_gb * 1.2)
        
        if not has_enough_memory:
            logger.warning(f"Low memory warning: {model_name} requires ~{required_memory_gb}GB but only {available_memory_gb:.1f}GB available")
        
        return has_enough_memory
    
    except Exception as e:
        logger.error(f"Error checking memory: {e}")
        # Default to True if we can't check
        return True

def load_index_and_sample():
    """Load the FAISS index and sample data."""
    global _index, _sample_data
    
    # Return cached data if already loaded
    if _index is not None and _sample_data is not None:
        return _index, _sample_data
    
    try:
        # Import faiss only when needed
        import faiss
        
        logger.info(f"Loading FAISS index from {INDEX_PATH}")
        _index = faiss.read_index(str(INDEX_PATH))
        
        logger.info(f"Loading sample data from {SAMPLE_PATH}")
        with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
            _sample_data = json.load(f)
        
        logger.info(f"Loaded index with {_index.ntotal} vectors and {len(_sample_data)} sample entries")
        return _index, _sample_data
    
    except ImportError:
        logger.error("Failed to import faiss. Please install it with 'pip install faiss-cpu' or 'pip install faiss-gpu'")
        raise
    except Exception as e:
        logger.error(f"Error loading index or sample data: {e}")
        raise

def get_embedding_model():
    """Lazy load the embedding model."""
    global _model
    
    if _model is not None:
        return _model
    
    try:
        # Import SentenceTransformer only when needed
        from sentence_transformers import SentenceTransformer
        
        logger.info(f"Loading sentence transformer model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        return _model
    
    except ImportError:
        logger.error("Failed to import sentence_transformers. Please install it with 'pip install sentence-transformers'")
        raise
    except Exception as e:
        logger.error(f"Error loading embedding model: {e}")
        raise

@lru_cache(maxsize=128)
def get_embedding_cached(query: str):
    """Get embedding for a query with caching."""
    model = get_embedding_model()
    return model.encode([query])[0]

def search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Search the index for similar chunks to the query."""
    # Check cache first
    cache_key = f"{query}_{k}"
    if cache_key in _search_results_cache:
        logger.info(f"Using cached search results for: '{query}'")
        return _search_results_cache[cache_key]
    
    logger.info(f"Searching for: '{query}'")
    
    try:
        # Import numpy only when needed
        import numpy as np
        import faiss
        
        # Load resources
        index, sample_data = load_index_and_sample()
        
        # Generate query embedding (using cached version if available)
        query_embedding = get_embedding_cached(query)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Search the index
        distances, indices = index.search(query_embedding.reshape(1, -1), k)
        
        # Prepare results - using sample data for display
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(sample_data):  # Use sample data directly
                sample_idx = idx
            else:  # For indices beyond sample size, use modulo to cycle through samples
                sample_idx = idx % len(sample_data)
            
            # Create a result with the sample data
            result = {
                "score": 1 - distances[0][i],  # Convert L2 distance to similarity score
                "sample_data": sample_data[sample_idx],
                "rank": i + 1,
                "actual_index": idx,
                "is_sample": idx < len(sample_data)
            }
            results.append(result)
        
        # Cache the results
        _search_results_cache[cache_key] = results
        
        # Limit cache size
        if len(_search_results_cache) > 50:
            # Remove a random old entry
            _search_results_cache.pop(next(iter(_search_results_cache)))
        
        return results
    
    except Exception as e:
        logger.error(f"Error during search: {e}")
        # Return empty results on error
        return []

def format_retrieved_chunks(results: List[Dict[str, Any]]) -> str:
    """Format the retrieved chunks for inclusion in the prompt."""
    chunks = []
    for i, result in enumerate(results):
        sample = result["sample_data"]
        text = sample.get("text", "")
        if text:
            # Truncate text if too long
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Format the chunk with metadata
            chunk = f"[CHUNK {i+1}] {sample.get('title', 'No Title')}\n{text}\n"
            chunks.append(chunk)
    
    return "\n".join(chunks)

def run_local_llm(prompt: str, model_name: str = DEFAULT_MODEL) -> str:
    """Run a local LLM using Ollama and return the generated text."""
    logger.info(f"Running local LLM: {model_name}")
    
    # Check memory requirements
    if not check_memory_requirements(model_name):
        return f"Error: Not enough memory to run {model_name}. This model requires approximately {MODEL_MEMORY_REQUIREMENTS.get(model_name, 4)}GB of RAM. Please try a smaller model or close other applications."
    
    try:
        # Check if Ollama is installed and the model is available
        import subprocess
        
        check_cmd = ["ollama", "list"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            logger.error("Ollama is not installed or not in PATH")
            return "Error: Ollama is not installed or not in PATH. Please install Ollama from https://ollama.ai/"
        
        # Run the model with the prompt
        cmd = ["ollama", "run", model_name, prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            logger.error(f"Error running Ollama: {result.stderr}")
            return f"Error running the LLM: {result.stderr}"
        
        return result.stdout.strip()
    
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error: {e}")
        return f"Error: Unicode decode error when processing model output. Try a different model or prompt."
    except Exception as e:
        logger.exception(f"Error running local LLM: {e}")
        return f"Error: {str(e)}"

def format_as_markdown(generated_text: str) -> str:
    """Format the generated text as markdown with proper sections."""
    # Try to extract sections
    try:
        # Extract summary
        summary_start = generated_text.lower().find("summary")
        if summary_start == -1:
            summary_start = 0
        else:
            summary_start = generated_text.find("\n", summary_start) + 1
        
        key_insights_start = generated_text.lower().find("key insights")
        if key_insights_start == -1:
            # Try alternate formats
            key_insights_start = generated_text.lower().find("insights")
            if key_insights_start == -1:
                key_insights_start = generated_text.lower().find("key points")
            if key_insights_start == -1:
                key_insights_start = len(generated_text)
                summary = generated_text[summary_start:key_insights_start].strip()
                key_insights = "- No key insights found"
        else:
            summary = generated_text[summary_start:key_insights_start].strip()
            key_insights_start = generated_text.find("\n", key_insights_start) + 1
        
        conclusion_start = generated_text.lower().find("conclusion")
        if conclusion_start == -1:
            conclusion_start = len(generated_text)
            key_insights = generated_text[key_insights_start:conclusion_start].strip()
            conclusion = "No conclusion found."
        else:
            key_insights = generated_text[key_insights_start:conclusion_start].strip()
            conclusion_start = generated_text.find("\n", conclusion_start) + 1
            conclusion = generated_text[conclusion_start:].strip()
        
        # Format key insights as bullet points if they aren't already
        if not key_insights.strip().startswith("-") and not key_insights.strip().startswith("*"):
            # Split by newlines and create bullet points
            insights_lines = key_insights.split("\n")
            formatted_insights = []
            for line in insights_lines:
                line = line.strip()
                if line and not line.lower().startswith(("key insights", "insights", "key points")):
                    formatted_insights.append(f"- {line}")
            key_insights = "\n".join(formatted_insights)
        
        # Apply the markdown template
        markdown_text = MARKDOWN_TEMPLATE.format(
            summary=summary,
            key_insights=key_insights,
            conclusion=conclusion
        )
        
        return markdown_text
    
    except Exception as e:
        logger.warning(f"Error formatting as markdown: {e}")
        # Return the original text if formatting fails
        return generated_text

def generate_document(user_prompt: str, model_name: str = DEFAULT_MODEL, num_chunks: int = 3, format_markdown: bool = True) -> Dict[str, Any]:
    """Generate a structured document based on the user prompt and retrieved content."""
    start_time = time.time()
    
    try:
        # Search for relevant content
        results = search(user_prompt, k=num_chunks)
        
        # Format the retrieved chunks
        retrieved_chunks = format_retrieved_chunks(results)
        
        # Create the prompt for the LLM
        prompt = PROMPT_TEMPLATE.format(
            user_prompt=user_prompt,
            retrieved_chunks=retrieved_chunks
        )
        
        # Run the LLM to generate the document
        generated_text = run_local_llm(prompt, model_name)
        
        # Format as markdown if requested
        if format_markdown:
            formatted_text = format_as_markdown(generated_text)
        else:
            formatted_text = generated_text
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        return {
            "original_text": generated_text,
            "formatted_text": formatted_text,
            "user_prompt": user_prompt,
            "generation_time": generation_time,
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "chunks_used": num_chunks
        }
    
    except Exception as e:
        logger.exception(f"Error generating document: {e}")
        return {
            "error": str(e),
            "user_prompt": user_prompt,
            "timestamp": datetime.now().isoformat()
        }

def save_document(document: Dict[str, Any], filename: Optional[str] = None) -> str:
    """Save the document to a file and return the filename."""
    if not filename:
        # Create a filename based on the first few words of the prompt
        words = document["user_prompt"].split()[:5]
        filename = "_".join(words).lower() + ".md"
        filename = "".join(c if c.isalnum() or c == "_" else "_" for c in filename)
    
    if not filename.endswith(".md"):
        filename += ".md"
    
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / filename
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(document["formatted_text"])
    
    # Save metadata for evaluation
    metadata = {
        "user_prompt": document["user_prompt"],
        "timestamp": document["timestamp"],
        "model": document.get("model", DEFAULT_MODEL),
        "chunks_used": document.get("chunks_used", 0),
        "generation_time": document.get("generation_time", 0)
    }
    
    metadata_path = output_path.with_suffix(".json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    return str(output_path)

# Preload the model and index in a background thread
def preload_resources():
    """Preload resources in a background thread."""
    try:
        # Load embedding model
        get_embedding_model()
        
        # Load index and sample data
        load_index_and_sample()
        
        logger.info("Resources preloaded successfully")
    except Exception as e:
        logger.error(f"Error preloading resources: {e}")

def main():
    """Main function to parse arguments and generate a document."""
    parser = argparse.ArgumentParser(description="SmartDraft.AI - Generate structured documents")
    parser.add_argument("prompt", nargs="?", help="User prompt for document generation")
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_MODEL, 
                        choices=AVAILABLE_MODELS, help="Local LLM to use via Ollama")
    parser.add_argument("--chunks", "-c", type=int, default=3, 
                        help="Number of content chunks to retrieve")
    parser.add_argument("--interactive", "-i", action="store_true", 
                        help="Run in interactive mode")
    parser.add_argument("--output", "-o", type=str, help="Output file for the generated document")
    parser.add_argument("--no-markdown", action="store_true", 
                        help="Disable markdown formatting")
    parser.add_argument("--evaluate", "-e", action="store_true",
                        help="Collect evaluation metrics")
    parser.add_argument("--preload", "-p", action="store_true",
                        help="Preload resources at startup")
    args = parser.parse_args()
    
    # Start preloading resources if requested
    if args.preload:
        logger.info("Preloading resources in background...")
        preload_thread = threading.Thread(target=preload_resources)
        preload_thread.daemon = True
        preload_thread.start()
    
    try:
        if args.interactive:
            print("\nSmartDraft.AI - Interactive Mode")
            print("Type 'exit' or 'quit' to end the session\n")
            
            while True:
                user_prompt = input("\nEnter your request: ")
                if user_prompt.lower() in ('exit', 'quit'):
                    break
                
                if not user_prompt.strip():
                    continue
                
                print("\nGenerating document... (this may take a moment)\n")
                
                start_time = time.time()
                document = generate_document(
                    user_prompt, 
                    args.model, 
                    args.chunks, 
                    not args.no_markdown
                )
                end_time = time.time()
                
                print("\n" + "=" * 80 + "\n")
                print(document["formatted_text"])
                print("\n" + "=" * 80 + "\n")
                
                if args.evaluate:
                    generation_time = end_time - start_time
                    print(f"Generation time: {generation_time:.2f} seconds")
                    relevance = input("Rate relevance (1-5): ")
                    document["relevance_rating"] = relevance
                
                save_option = input("Save this document? (y/n): ")
                if save_option.lower() == 'y':
                    filename = input("Enter filename (or press Enter for auto-generated): ")
                    saved_path = save_document(document, filename if filename else None)
                    print(f"Document saved to {saved_path}")
        
        elif args.prompt:
            print("\nGenerating document... (this may take a moment)\n")
            
            document = generate_document(
                args.prompt, 
                args.model, 
                args.chunks, 
                not args.no_markdown
            )
            
            if args.output:
                saved_path = save_document(document, args.output)
                print(f"Document saved to {saved_path}")
            else:
                print(document["formatted_text"])
                
                if args.evaluate:
                    print(f"\nGeneration time: {document.get('generation_time', 0):.2f} seconds")
                    relevance = input("Rate relevance (1-5): ")
                    document["relevance_rating"] = relevance
                    
                    # Save evaluation data
                    eval_dir = Path("evaluation")
                    eval_dir.mkdir(exist_ok=True)
                    eval_path = eval_dir / f"eval_{int(time.time())}.json"
                    with open(eval_path, "w", encoding="utf-8") as f:
                        json.dump(document, f, indent=2)
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\nExiting SmartDraft.AI")
    
    except Exception as e:
        logger.exception(f"Error: {e}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 