import os
import json
import logging
import numpy as np
from pathlib import Path
from tqdm import tqdm
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
INPUT_DIR = Path('wikihow_processed')  # Directory with processed chunks
OUTPUT_DIR = Path('wikihow_index')     # Directory to store embeddings and index
BATCH_SIZE = 1000                      # Process this many documents at once
MODEL_NAME = 'all-MiniLM-L6-v2'        # Lightweight sentence transformer model
USE_HNSW = True                        # Use HNSW index (faster search, slightly lower accuracy) instead of FlatL2

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def load_chunks(input_dir: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Load all chunks from jsonl files in the input directory."""
    all_chunks = []
    all_texts = []
    
    input_files = list(input_dir.glob('*.jsonl'))
    if not input_files:
        raise ValueError(f"No .jsonl files found in {input_dir}")
    
    logger.info(f"Loading chunks from {len(input_files)} files")
    
    for file_path in tqdm(input_files, desc="Loading files"):
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                all_chunks.append(chunk)
                all_texts.append(chunk['text'])
    
    logger.info(f"Loaded {len(all_chunks)} chunks")
    return all_chunks, all_texts

def generate_embeddings(texts: List[str], model_name: str) -> np.ndarray:
    """Generate embeddings for a list of texts using the specified model."""
    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    
    # Process in batches to avoid memory issues
    all_embeddings = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
    
    logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")
    
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Generating embeddings"):
        batch_texts = texts[i:i+BATCH_SIZE]
        batch_embeddings = model.encode(batch_texts, show_progress_bar=False)
        all_embeddings.append(batch_embeddings)
    
    # Combine all batches
    embeddings = np.vstack(all_embeddings)
    logger.info(f"Generated {embeddings.shape} embeddings")
    
    return embeddings

def build_faiss_index(embeddings: np.ndarray, use_hnsw: bool = True) -> faiss.Index:
    """Build a FAISS index from embeddings."""
    d = embeddings.shape[1]  # Embedding dimension
    
    if use_hnsw:
        # HNSW index for faster search with slight accuracy trade-off
        logger.info(f"Building HNSW index with dimension {d}")
        index = faiss.IndexHNSWFlat(d, 32)  # 32 neighbors per node
        index.hnsw.efConstruction = 200  # Higher value = more accurate but slower construction
        index.hnsw.efSearch = 128       # Higher value = more accurate but slower search
    else:
        # Flat L2 index for exact search (slower but more accurate)
        logger.info(f"Building FlatL2 index with dimension {d}")
        index = faiss.IndexFlatL2(d)
    
    # Normalize vectors to unit length (for cosine similarity)
    faiss.normalize_L2(embeddings)
    
    # Add vectors to index
    index.add(embeddings)
    logger.info(f"Added {index.ntotal} vectors to index")
    
    return index

def save_index_and_metadata(index: faiss.Index, chunks: List[Dict[str, Any]], output_dir: Path):
    """Save the FAISS index and metadata to disk."""
    # Save the FAISS index
    index_path = output_dir / "wikihow_faiss.index"
    logger.info(f"Saving FAISS index to {index_path}")
    faiss.write_index(index, str(index_path))
    
    # Extract and save metadata (everything except the text to save space)
    metadata = []
    for chunk in chunks:
        # Create a copy without the text field to save space
        meta = {k: v for k, v in chunk.items() if k != 'text'}
        # Keep a preview of the text for debugging
        meta['text_preview'] = chunk['text'][:100] + '...' if len(chunk['text']) > 100 else chunk['text']
        metadata.append(meta)
    
    metadata_path = output_dir / "wikihow_metadata.pkl"
    logger.info(f"Saving metadata to {metadata_path}")
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    
    # Save a sample of the original chunks for reference
    sample_path = output_dir / "wikihow_sample.json"
    logger.info(f"Saving sample of 100 complete chunks to {sample_path}")
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(chunks[:100], f, indent=2)

def main():
    """Main function to load chunks, generate embeddings, and build index."""
    try:
        # Load all chunks
        chunks, texts = load_chunks(INPUT_DIR)
        
        # Generate embeddings
        embeddings = generate_embeddings(texts, MODEL_NAME)
        
        # Build FAISS index
        index = build_faiss_index(embeddings, use_hnsw=USE_HNSW)
        
        # Save index and metadata
        save_index_and_metadata(index, chunks, OUTPUT_DIR)
        
        logger.info("Embedding and indexing complete!")
        logger.info(f"Index and metadata saved to {OUTPUT_DIR}")
        
        # Print some stats
        logger.info(f"Total chunks indexed: {len(chunks)}")
        logger.info(f"Embedding dimension: {embeddings.shape[1]}")
        logger.info(f"Index type: {'HNSW' if USE_HNSW else 'FlatL2'}")
        
    except Exception as e:
        logger.exception(f"Error during embedding and indexing: {e}")
        raise

if __name__ == "__main__":
    main() 