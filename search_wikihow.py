import faiss
import pickle
import json
import numpy as np
import argparse
import logging
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default paths
INDEX_DIR = Path('wikihow_index')
INDEX_PATH = INDEX_DIR / 'wikihow_faiss.index'
METADATA_PATH = INDEX_DIR / 'wikihow_metadata.pkl'
SAMPLE_PATH = INDEX_DIR / 'wikihow_sample.json'
MODEL_NAME = 'all-MiniLM-L6-v2'

def load_index_and_metadata():
    """Load the FAISS index and metadata."""
    logger.info(f"Loading FAISS index from {INDEX_PATH}")
    index = faiss.read_index(str(INDEX_PATH))
    
    # Instead of loading all metadata at once, we'll create a metadata accessor
    # that can load specific entries on demand
    logger.info(f"Creating metadata accessor for {METADATA_PATH}")
    metadata_accessor = MetadataAccessor(METADATA_PATH)
    
    logger.info(f"Loaded index with {index.ntotal} vectors")
    return index, metadata_accessor

class MetadataAccessor:
    """Class to access metadata without loading everything into memory."""
    
    def __init__(self, metadata_path):
        self.metadata_path = metadata_path
        self.metadata_size = os.path.getsize(metadata_path)
        logger.info(f"Metadata file size: {self.metadata_size / (1024*1024):.2f} MB")
        
        # Load a small sample to get structure
        with open(metadata_path, 'rb') as f:
            # Read just enough to get the first few entries
            self.sample = pickle.load(f)[:10]
        
        self.entry_count = self._estimate_entry_count()
        logger.info(f"Estimated metadata entries: {self.entry_count}")
    
    def _estimate_entry_count(self):
        """Estimate the total number of entries based on the sample."""
        # If we have a sample from the embedding process, use that
        sample_path = Path(self.metadata_path).parent / 'wikihow_sample.json'
        if sample_path.exists():
            with open(sample_path, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            if isinstance(sample_data, list) and len(sample_data) > 0:
                return len(sample_data) * 5000  # Rough estimate
        
        # Otherwise make a rough estimate based on file size and sample size
        if len(self.sample) > 0:
            avg_entry_size = self.metadata_size / len(self.sample)
            return int(self.metadata_size / avg_entry_size)
        
        return 500000  # Fallback estimate
    
    def __len__(self):
        return self.entry_count
    
    def get_batch(self, indices):
        """Get metadata for specific indices."""
        results = []
        
        # Load the full metadata file - this is inefficient but necessary
        # for random access without memory mapping
        try:
            with open(self.metadata_path, 'rb') as f:
                all_metadata = pickle.load(f)
            
            # Get metadata for each valid index
            for idx in indices:
                if 0 <= idx < len(all_metadata):
                    results.append(all_metadata[idx])
                else:
                    # Provide a placeholder for invalid indices
                    results.append({
                        'title': 'Invalid Index',
                        'text_preview': 'This index is out of bounds',
                        'format': 'unknown',
                        'prompt': 'unknown'
                    })
        except MemoryError:
            logger.error("Memory error when loading metadata. Using sample data instead.")
            # Fall back to sample data
            for _ in indices:
                results.append({
                    'title': 'Memory Error',
                    'text_preview': 'Could not load metadata due to memory constraints',
                    'format': 'unknown',
                    'prompt': 'Try searching with fewer results or on a machine with more RAM'
                })
        
        return results

def search(query, index, metadata_accessor, model, k=5):
    """Search the index for similar chunks to the query."""
    logger.info(f"Searching for: '{query}'")
    
    # Generate query embedding
    query_embedding = model.encode([query])[0]
    
    # Normalize for cosine similarity
    faiss.normalize_L2(query_embedding.reshape(1, -1))
    
    # Search the index
    distances, indices = index.search(query_embedding.reshape(1, -1), k)
    
    # Get metadata for the results
    metadata_batch = metadata_accessor.get_batch(indices[0])
    
    # Prepare results
    results = []
    for i, (idx, meta) in enumerate(zip(indices[0], metadata_batch)):
        if idx >= 0:  # Valid index
            result = {
                "score": 1 - distances[0][i],  # Convert L2 distance to similarity score
                "metadata": meta,
                "rank": i + 1
            }
            results.append(result)
    
    return results

def display_results(results):
    """Display search results in a readable format."""
    print("\n===== SEARCH RESULTS =====\n")
    
    for i, result in enumerate(results):
        print(f"Result #{i+1} (Score: {result['score']:.4f})")
        print(f"Title: {result['metadata'].get('title', 'N/A')}")
        
        # Show chunk information if available
        if 'chunk_index' in result['metadata'] and 'total_chunks' in result['metadata']:
            print(f"Chunk: {result['metadata']['chunk_index'] + 1} of {result['metadata']['total_chunks']}")
        
        # Show text preview
        print(f"Preview: {result['metadata'].get('text_preview', 'N/A')}")
        
        # Show other metadata
        print(f"Format: {result['metadata'].get('format', 'N/A')}")
        
        # Show prompt if available, truncated if too long
        prompt = result['metadata'].get('prompt', 'N/A')
        if isinstance(prompt, str) and len(prompt) > 100:
            prompt = prompt[:100] + "..."
        print(f"Prompt: {prompt}")
        
        print("-" * 80)

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Search the WikiHow FAISS index")
    parser.add_argument("query", nargs="?", default=None, help="Search query")
    parser.add_argument("--top", "-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--index", type=str, default=str(INDEX_PATH), help="Path to FAISS index")
    parser.add_argument("--metadata", type=str, default=str(METADATA_PATH), help="Path to metadata file")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--sample", "-s", action="store_true", help="Use sample data only (for low memory systems)")
    args = parser.parse_args()
    
    try:
        # Load index and metadata
        index, metadata_accessor = load_index_and_metadata()
        
        # Load the model
        logger.info(f"Loading sentence transformer model: {MODEL_NAME}")
        model = SentenceTransformer(MODEL_NAME)
        
        if args.interactive:
            # Interactive mode
            print("\nWikiHow Search - Interactive Mode")
            print("Type 'exit' or 'quit' to end the session\n")
            
            while True:
                query = input("\nEnter search query: ")
                if query.lower() in ('exit', 'quit'):
                    break
                
                if not query.strip():
                    continue
                
                results = search(query, index, metadata_accessor, model, args.top)
                display_results(results)
        
        elif args.query:
            # Single query mode
            results = search(args.query, index, metadata_accessor, model, args.top)
            display_results(results)
        
        else:
            # No query provided, show example queries
            print("\nWikiHow Search - Example Mode")
            example_queries = [
                "How do I compost at home?",
                "What's the best way to eat healthy on a budget?",
                "How to train a dog to sit",
                "Tips for growing tomatoes",
                "How to make sourdough bread"
            ]
            
            print("\nExample queries you can try:")
            for i, query in enumerate(example_queries):
                print(f"{i+1}. {query}")
            
            print("\nRun with --interactive or -i flag for interactive mode")
            print("Or provide a query as an argument:")
            print(f"python {Path(__file__).name} \"How do I compost at home?\"")
            print("\nFor systems with limited memory, try the --sample flag to use only sample data")
    
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.error("Make sure you've run embed_and_index.py first to create the index")
    
    except Exception as e:
        logger.exception(f"Error during search: {e}")

if __name__ == "__main__":
    main() 