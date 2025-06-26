import os
import sys
import argparse
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default paths
INDEX_DIR = Path('wikihow_index')
INDEX_PATH = INDEX_DIR / 'wikihow_faiss.index'
SAMPLE_PATH = INDEX_DIR / 'wikihow_sample.json'
MODEL_NAME = 'all-MiniLM-L6-v2'

# Global variables for lazy loading
_index = None
_sample_data = None
_model = None

def load_sample_data():
    """Load only the sample data for display."""
    global _sample_data
    
    if _sample_data is not None:
        return _sample_data
    
    try:
        logger.info(f"Loading sample data from {SAMPLE_PATH}")
        with open(SAMPLE_PATH, 'r', encoding='utf-8') as f:
            _sample_data = json.load(f)
        
        logger.info(f"Loaded {len(_sample_data)} sample entries")
        return _sample_data
    
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
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

def search_with_limited_memory(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Search the index with limited memory usage."""
    logger.info(f"Searching for: '{query}'")
    
    try:
        # Import libraries only when needed
        import numpy as np
        import faiss
        
        # Load sample data for display
        sample_data = load_sample_data()
        
        # Generate query embedding
        model = get_embedding_model()
        query_embedding = model.encode([query])[0]
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Load index with read-only flag to reduce memory usage
        logger.info(f"Loading FAISS index from {INDEX_PATH}")
        index = faiss.read_index(str(INDEX_PATH), faiss.IO_FLAG_READ_ONLY)
        
        # Search the index
        distances, indices = index.search(query_embedding.reshape(1, -1), k)
        
        # Free the index memory immediately
        del index
        
        # Prepare results - using sample data for display
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(sample_data):  # Use sample data directly
                sample_idx = idx
            else:  # For indices beyond sample size, use modulo to cycle through samples
                sample_idx = idx % len(sample_data)
            
            # Create a result with the sample data
            result = {
                "score": float(1 - distances[0][i]),  # Convert L2 distance to similarity score
                "sample_data": sample_data[sample_idx],
                "rank": i + 1,
                "actual_index": int(idx),
                "is_sample": idx < len(sample_data)
            }
            results.append(result)
        
        return results
    
    except MemoryError:
        logger.error("Memory error during search. Try reducing the number of results or using a smaller model.")
        return []
    except Exception as e:
        logger.error(f"Error during search: {e}")
        return []

def display_results(results: List[Dict[str, Any]]):
    """Display search results in a readable format."""
    if not results:
        print("\nNo results found.")
        return
    
    print("\n" + "=" * 80)
    print(f"Found {len(results)} results:")
    print("=" * 80)
    
    for i, result in enumerate(results):
        sample = result["sample_data"]
        score = result["score"]
        
        print(f"\n[{i+1}] Score: {score:.4f}")
        print(f"Title: {sample.get('title', 'No Title')}")
        
        text = sample.get("text", "")
        if text:
            # Truncate text if too long
            if len(text) > 300:
                text = text[:300] + "..."
            print(f"Content: {text}")
        
        print("-" * 80)

def interactive_search():
    """Run an interactive search session."""
    print("\nWikiHow Lite Search - Interactive Mode")
    print("Type 'exit' or 'quit' to end the session\n")
    
    while True:
        query = input("\nEnter your search query: ")
        if query.lower() in ('exit', 'quit'):
            break
        
        if not query.strip():
            continue
        
        print("\nSearching... (this may take a moment)")
        
        start_time = time.time()
        results = search_with_limited_memory(query)
        end_time = time.time()
        
        display_results(results)
        print(f"\nSearch completed in {end_time - start_time:.2f} seconds")

def main():
    """Main function to parse arguments and execute search."""
    parser = argparse.ArgumentParser(description="WikiHow Lite Search - Memory-efficient semantic search")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--top", "-k", type=int, default=5, 
                        help="Number of results to return")
    parser.add_argument("--interactive", "-i", action="store_true", 
                        help="Run in interactive mode")
    args = parser.parse_args()
    
    try:
        if args.interactive:
            interactive_search()
        
        elif args.query:
            results = search_with_limited_memory(args.query, args.top)
            display_results(results)
        
        else:
            print("\nWikiHow Lite Search - Memory-efficient semantic search")
            print("\nExample queries:")
            print("  - How to grow tomatoes")
            print("  - Tips for job interviews")
            print("  - Learning to play guitar")
            print("\nUse --interactive or -i for interactive mode")
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\nSearch terminated by user")
    
    except Exception as e:
        logger.exception(f"Error: {e}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 