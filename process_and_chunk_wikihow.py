import os
import json
import gzip
import re
import logging
import gc
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
import ijson
import html2text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------- CONFIG --------------------
DATA_DIR = Path('wikihow_data')       # directory containing downloaded dataset
OUTPUT_DIR = Path('wikihow_processed') # single output directory
BATCH_SIZE = 10000                    # records per output file
PROGRESS_EVERY = 10000                # log progress interval
ALLOWED_EXT = ('.json', '.jsonl', '.json.gz', '.jsonl.gz')

# Chunking configuration
MIN_CHUNK_WORDS = 150
MAX_CHUNK_WORDS = 300
WORD_COUNT_THRESHOLD = 300  # Articles with more words than this will be split

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# -------------------- TEXT PROCESSING --------------------
html_converter = html2text.HTML2Text()
html_converter.ignore_links = True
html_converter.ignore_images = True
html_converter.ignore_emphasis = True

def clean_text(text):
    """Minimal cleaning to preserve content but normalize whitespace."""
    if not isinstance(text, str):
        return ''
    
    # Convert HTML to text if needed
    if '<' in text and '>' in text:
        text = html_converter.handle(text)
    
    # Normalize whitespace but keep most punctuation
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_title_from_text(text):
    """Extract title from text content that might start with 'Title:' or similar."""
    if not text:
        return ''
    
    # Try to find explicit title
    title_match = re.search(r'Title:\s*([^\n]+)', text)
    if title_match:
        return title_match.group(1).strip()
    
    # Try first line if it's short enough to be a title
    lines = text.split('\n')
    if lines and len(lines[0]) < 100:
        return lines[0].strip()
    
    return ''

def count_words(text):
    """Count words in text, handling various whitespace."""
    return len(re.findall(r'\b\w+\b', text))

def split_into_sentences(text):
    """Split text into sentences, preserving sentence boundaries."""
    # This regex handles common sentence endings while trying to avoid splitting
    # abbreviations, numbers, etc.
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk_text(text, min_words, max_words):
    """Split text into chunks of min_words to max_words, respecting sentence boundaries."""
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for sentence in sentences:
        sentence_word_count = count_words(sentence)
        
        # If adding this sentence would exceed max_words and we already have content,
        # finish the current chunk and start a new one
        if current_word_count + sentence_word_count > max_words and current_word_count >= min_words:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_word_count = sentence_word_count
        else:
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_word_count += sentence_word_count
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# -------------------- FILE HANDLING --------------------

def open_maybe_gzip(path):
    """Open normal or gzipped file for text reading."""
    if str(path).endswith('.gz'):
        return gzip.open(path, 'rt', encoding='utf-8', errors='ignore')
    return open(path, 'r', encoding='utf-8', errors='ignore')

def iter_raw_records(file_path):
    """Yield raw JSON objects from various WikiHow shard formats."""
    # .jsonl or .jsonl.gz files are line-delimited
    if str(file_path).endswith(('.jsonl', '.jsonl.gz')):
        with open_maybe_gzip(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    else:
        # .json or .json.gz containing an array or object
        with open_maybe_gzip(file_path) as f:
            try:
                # Stream array elements if root is list
                for obj in ijson.items(f, 'item'):
                    yield obj
            except Exception as e:
                logger.warning(f'ijson streaming failed for {file_path}: {e}. Falling back to full load.')
                try:
                    f.seek(0)
                    data = json.load(f)
                    if isinstance(data, list):
                        for obj in data:
                            yield obj
                    elif isinstance(data, dict):
                        yield data
                except Exception:
                    logger.error(f'Could not parse {file_path}')

def save_batch(buffer, batch_idx):
    """Save a batch of records to a JSONL file."""
    if not buffer:
        return
    
    output_file = OUTPUT_DIR / f"wikihow_processed_{batch_idx}.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for rec in buffer:
            json.dump(rec, f, ensure_ascii=False)
            f.write('\n')
    
    logger.info(f'Saved {len(buffer)} records -> {output_file}')

# -------------------- PROCESSING PIPELINE --------------------

def process_and_chunk_article(raw_record, split_name):
    """Clean, normalize, and chunk a single article if needed."""
    # Skip non-dict items
    if not isinstance(raw_record, dict):
        return []
    
    # Extract and clean fields
    prompt = clean_text(raw_record.get('prompt', ''))
    text = raw_record.get('text', '')
    
    # Skip empty records
    if not text:
        return []
    
    # Clean text (minimal cleaning to preserve content)
    cleaned_text = clean_text(text)
    
    # Extract or generate title
    title = ''
    if 'title' in raw_record:
        title = clean_text(raw_record.get('title'))
    else:
        title = extract_title_from_text(cleaned_text)
        
    # If no title found, use prompt as title
    if not title and prompt:
        title = prompt
    
    # Skip if we still don't have text or title
    if not cleaned_text or not title:
        return []
    
    # Create base record with cleaned fields
    record = {
        'prompt': prompt,
        'text': cleaned_text,
        'title': title,
        'format': raw_record.get('format', ''),
        'split': split_name
    }
    
    # Check if we need to chunk the article
    word_count = count_words(cleaned_text)
    if word_count <= WORD_COUNT_THRESHOLD:
        # Short article, return as is
        return [record]
    
    # Long article, split into chunks
    chunks = chunk_text(cleaned_text, MIN_CHUNK_WORDS, MAX_CHUNK_WORDS)
    chunked_records = []
    
    # Create a record for each chunk
    for i, chunk_content in enumerate(chunks):
        chunk = record.copy()
        chunk['text'] = chunk_content
        chunk['chunk_index'] = i
        chunk['total_chunks'] = len(chunks)
        chunk['title'] = f"{title} (Part {i+1}/{len(chunks)})"
        chunked_records.append(chunk)
    
    return chunked_records

def main():
    """Process all WikiHow articles in one pipeline: clean, normalize, and chunk."""
    if not DATA_DIR.exists():
        logger.error(f"Input directory {DATA_DIR} not found.")
        return

    # Find all JSON files
    split_files = defaultdict(list)
    for root, _, files in os.walk(DATA_DIR):
        for fname in files:
            if any(fname.lower().endswith(ext) for ext in ALLOWED_EXT):
                fpath = Path(root) / fname
                # Determine split by parent directory name
                parts = fpath.relative_to(DATA_DIR).parts
                split = parts[0] if len(parts) > 1 else 'main'
                split_files[split].append(fpath)

    total_processed = 0
    total_chunks = 0
    batch_idx = 0
    current_batch = []
    
    for split, shards in split_files.items():
        logger.info(f'Processing split "{split}" with {len(shards)} files')
        
        for shard_path in shards:
            logger.info(f'Processing {shard_path}')
            record_count = 0
            accepted_count = 0
            
            for raw in iter_raw_records(shard_path):
                record_count += 1
                
                # Debug the first few records
                if record_count <= 3:
                    logger.info(f"Record #{record_count} keys: {list(raw.keys() if isinstance(raw, dict) else [])}")
                    if isinstance(raw, dict):
                        logger.info(f"Raw prompt: {str(raw.get('prompt', ''))[:100]}")
                        logger.info(f"Raw text: {str(raw.get('text', ''))[:100]}")
                
                # Process and chunk the article
                processed_records = process_and_chunk_article(raw, split)
                
                # Add to batch
                if processed_records:
                    current_batch.extend(processed_records)
                    accepted_count += 1
                    total_chunks += len(processed_records)
                
                # Show progress
                if record_count % PROGRESS_EVERY == 0:
                    logger.info(f'Processed {record_count} records from current shard')
                
                # Save batch when full
                if len(current_batch) >= BATCH_SIZE:
                    save_batch(current_batch, batch_idx)
                    batch_idx += 1
                    current_batch = []
                    gc.collect()
            
            total_processed += record_count
            logger.info(f'Shard stats: examined {record_count}, accepted {accepted_count}, produced {total_chunks} chunks')
        
        logger.info(f'Finished split {split}')
    
    # Save any remaining records
    if current_batch:
        save_batch(current_batch, batch_idx)
    
    logger.info(f'Processing complete. Processed {total_processed} articles, created {total_chunks} total chunks')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Interrupted by user.')
    except Exception as e:
        logger.exception(f'Fatal error: {e}') 