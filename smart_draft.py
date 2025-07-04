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
import re

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
PROMPT_TEMPLATE = """You are SmartDraft.AI — an expert writing assistant that specializes in creating well-structured, informative documents tailored to the user's needs.

## CONTEXT
The following content has been retrieved based on the user's request. Use this information to inform your response, but do not copy it verbatim:
{retrieved_chunks}

## USER REQUEST
{user_prompt}

## INSTRUCTIONS
Create a comprehensive, well-structured document that addresses the user's request. Your response must include the following sections:

### SUMMARY (200-250 words)
- Begin with a concise yet thorough overview of the topic
- Define key concepts and establish their significance
- Highlight the practical relevance and applications
- Use precise language and specific terminology appropriate to the subject
- Avoid generalizations and vague statements

### KEY INSIGHTS (4-6 detailed points)
For each insight:
- Start with a clear, specific claim or observation
- Support with concrete examples, data points, or evidence
- Explain why this insight matters and its broader implications
- Connect to related concepts or domains when relevant
- Ensure each insight is substantive (3-4 sentences) and distinct from others

### CONCLUSION (150-200 words)
- Synthesize the main points without simply repeating them
- Offer thoughtful reflections on the significance of the topic
- Suggest specific applications or next steps for the reader
- Address potential future developments or remaining questions
- End with a memorable closing statement that reinforces the document's value

## WRITING GUIDELINES
- Use professional language that is accessible to an educated general audience
- Incorporate domain-specific terminology appropriately
- Vary sentence structure and length for readability
- Maintain logical flow between paragraphs and sections
- Use concrete examples rather than abstract generalizations
- Be precise and specific in all claims and descriptions
- Avoid unnecessary jargon, clichés, and filler content
- Ensure factual accuracy and logical consistency throughout

Your response should demonstrate depth of understanding, analytical thinking, and practical utility. Focus on delivering genuine value to the reader."""

# Markdown formatting template
MARKDOWN_TEMPLATE = """# {title}

## Summary
{summary}

## Key Insights
{key_insights}

## Conclusion
{conclusion}

---
*Generated by SmartDraft.AI using semantic search and local LLM processing*
"""

# Global variables for lazy loading
_index = None
_sample_data = None
_model = None
_embedding_cache = {}  # Cache for embeddings
_search_results_cache = {}  # Cache for search results

def check_memory_requirements(model_name: str) -> dict:
    """Check if the system has enough memory for the model and return info."""
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
        
        return {
            "has_enough": has_enough_memory,
            "required": required_memory_gb,
            "available": round(available_memory_gb, 1),
            "warning": None if has_enough_memory else f"Low memory warning: {model_name} requires ~{required_memory_gb}GB but only {available_memory_gb:.1f}GB available"
        }
    
    except Exception as e:
        logger.error(f"Error checking memory: {e}")
        # Default to True if we can't check
        return {
            "has_enough": True,
            "required": MODEL_MEMORY_REQUIREMENTS.get(model_name, 4),
            "available": None,
            "warning": None
        }

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
    if not results:
        return "No relevant information found."
        
    chunks = []
    for i, result in enumerate(results):
        sample = result["sample_data"]
        text = sample.get("text", "")
        title = sample.get("title", "No Title")
        
        if text:
            # Truncate text if too long
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Format the chunk with metadata and relevance score
            chunk = f"[CHUNK {i+1}] TITLE: {title}\n"
            chunk += f"RELEVANCE SCORE: {result['score']:.2f}\n"
            chunk += f"CONTENT: {text}\n"
            chunks.append(chunk)
    
    return "\n".join(chunks)

def run_local_llm(prompt: str, model_name: str = DEFAULT_MODEL) -> str:
    """Run a local LLM using Ollama and return the generated text."""
    logger.info(f"Running local LLM: {model_name}")
    
    # Check memory requirements but don't block execution
    memory_info = check_memory_requirements(model_name)
    if not memory_info["has_enough"]:
        logger.warning(f"Low memory warning for {model_name}. Continuing anyway but performance may be affected.")
    
    try:
        # Check if Ollama is installed and the model is available
        import subprocess
        
        check_cmd = ["ollama", "list"]
        result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            logger.error("Ollama is not installed or not in PATH")
            return "Error: Ollama is not installed or not in PATH. Please install Ollama from https://ollama.ai/"
        
        # Run the model with the prompt and a timeout
        # Increased timeout to 360 seconds (6 minutes) to accommodate more detailed prompts
        cmd = ["ollama", "run", model_name, prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=360)
        
        if result.returncode != 0:
            logger.error(f"Error running Ollama: {result.stderr}")
            return f"Error running the LLM: {result.stderr}"
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        logger.error(f"Ollama process timed out after 360 seconds")
        return "Error: The language model took too long to generate a response. Try using a smaller model or simplifying your request."
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
        # Check if the text is already well-formatted with proper markdown headers
        well_formatted = False
        
        # Look for different heading patterns
        summary_heading = re.search(r'(## Summary|### Summary)', generated_text)
        key_insights_heading = re.search(r'(## Key Insights|### Key Insights)', generated_text)
        conclusion_heading = re.search(r'(## Conclusion|### Conclusion)', generated_text)
        
        # Check if we have a properly formatted document with all sections
        if (summary_heading and 
            (key_insights_heading or "Key Insights" in generated_text) and 
            (conclusion_heading or "Conclusion" in generated_text)):
            well_formatted = True
        
        # If the text is already well-formatted, just clean it up and return
        if well_formatted:
            # Extract title if present
            title = "Generated Document"
            title_match = re.search(r'# ([^\n]+)', generated_text)
            if title_match:
                title = title_match.group(1).strip()
            
            # Find where the document should end (before any redundant sections)
            end_marker = "---"
            end_pos = generated_text.find(end_marker)
            if end_pos == -1:
                # Look for redundant sections as end markers
                redundant_markers = ["## Key Insights\n- No key insights found", 
                                    "## Conclusion\nNo conclusion found"]
                for marker in redundant_markers:
                    pos = generated_text.find(marker)
                    if pos != -1 and (end_pos == -1 or pos < end_pos):
                        end_pos = pos
            
            # If we found an end marker, trim the text
            if end_pos != -1:
                clean_text = generated_text[:end_pos].strip()
                return f"{clean_text}\n\n---\n*Generated by SmartDraft.AI using semantic search and local LLM processing*"
            
            # Check for memory warnings
            if "memory warning" in generated_text.lower():
                memory_warning_match = re.search(r'(\*\*Memory Warning:.*?available)', generated_text, re.IGNORECASE | re.DOTALL)
                if memory_warning_match:
                    warning_text = memory_warning_match.group(1)
                    return f"> {warning_text}\n\n{generated_text}"
            
            return generated_text
        
        # Try to extract title from the summary section
        title = "Generated Document"
        title_match = re.search(r'# ([^\n]+)', generated_text)
        if not title_match:
            title_match = re.search(r'\*\*([^*]+)\*\*', generated_text[:500])
        if title_match:
            title = title_match.group(1).strip()
        
        # Extract summary - look for heading markers or the word itself
        summary_patterns = ["### SUMMARY", "## SUMMARY", "# SUMMARY", "SUMMARY", "**Summary"]
        summary_start = -1
        for pattern in summary_patterns:
            pos = generated_text.find(pattern)
            if pos != -1:
                summary_start = pos
                break
        
        if summary_start == -1:
            summary_start = 0
        else:
            summary_start = generated_text.find("\n", summary_start) + 1
        
        # Look for key insights markers in the text
        key_insights_markers = [
            "key insight", "key insights", "important insight", "important insights",
            "one key insight", "another important insight", "another key insight"
        ]
        
        # Look for conclusion markers in the text
        conclusion_markers = [
            "in conclusion", "to conclude", "to sum up", "in summary", "to summarize",
            "finally,", "in the end", "ultimately", "in closing"
        ]
        
        # Find Key Insights section
        key_insights_patterns = ["### KEY INSIGHTS", "## KEY INSIGHTS", "# KEY INSIGHTS", "KEY INSIGHTS", "**Key Insights"]
        key_insights_start = -1
        for pattern in key_insights_patterns:
            pos = generated_text.find(pattern)
            if pos != -1:
                key_insights_start = pos
                break
        
        if key_insights_start == -1:
            # Try alternate formats
            alternate_patterns = ["INSIGHTS", "KEY POINTS", "MAIN POINTS"]
            for pattern in alternate_patterns:
                pos = generated_text.find(pattern)
                if pos != -1:
                    key_insights_start = pos
                    break
                    
            # If still not found, look for key insight markers in the text
            if key_insights_start == -1:
                for marker in key_insights_markers:
                    pos = generated_text.lower().find(marker)
                    if pos != -1:
                        # Found a key insight marker, but we need to find the start of the paragraph
                        paragraph_start = generated_text.rfind("\n\n", 0, pos)
                        if paragraph_start != -1:
                            key_insights_start = paragraph_start + 2  # +2 to skip the newlines
                        break
        
        # Find Conclusion section
        conclusion_patterns = ["### CONCLUSION", "## CONCLUSION", "# CONCLUSION", "CONCLUSION", "**Conclusion"]
        conclusion_start = -1
        for pattern in conclusion_patterns:
            pos = generated_text.find(pattern)
            if pos != -1:
                conclusion_start = pos
                break
        
        # Check for "Next Steps" as an alternative to Conclusion
        if conclusion_start == -1:
            next_steps_pos = generated_text.find("**Next Steps")
            if next_steps_pos == -1:
                next_steps_pos = generated_text.find("Next Steps")
            if next_steps_pos != -1:
                conclusion_start = next_steps_pos
                
            # If still not found, look for conclusion markers
            if conclusion_start == -1:
                for marker in conclusion_markers:
                    pos = generated_text.lower().find(marker)
                    if pos != -1:
                        # Found a conclusion marker, but we need to find the start of the paragraph
                        paragraph_start = generated_text.rfind("\n\n", 0, pos)
                        if paragraph_start != -1:
                            conclusion_start = paragraph_start + 2  # +2 to skip the newlines
                        break
        
        # Look for references section which often comes after conclusion
        references_pos = -1
        references_patterns = ["**References", "References:", "REFERENCES", "Bibliography", "Works Cited"]
        for pattern in references_patterns:
            pos = generated_text.find(pattern)
            if pos != -1:
                references_pos = pos
                break
        
        # Extract the sections based on found positions
        if key_insights_start == -1:
            # No key insights found
            if conclusion_start == -1:
                # No conclusion either, everything is summary
                summary = generated_text[summary_start:].strip()
                
                # Try to extract key insights and conclusion from the summary
                extracted_insights = extract_key_insights_from_text(summary)
                extracted_conclusion = extract_conclusion_from_text(summary)
                
                if extracted_insights:
                    key_insights = extracted_insights
                else:
                    key_insights = "- No key insights found"
                    
                if extracted_conclusion:
                    conclusion = extracted_conclusion
                else:
                    conclusion = "No conclusion found."
            else:
                # Found conclusion but no key insights
                summary = generated_text[summary_start:conclusion_start].strip()
                
                # Try to extract key insights from the summary
                extracted_insights = extract_key_insights_from_text(summary)
                if extracted_insights:
                    key_insights = extracted_insights
                else:
                    key_insights = "- No key insights found"
                
                if references_pos != -1 and references_pos > conclusion_start:
                    conclusion = generated_text[conclusion_start:references_pos].strip()
                else:
                    conclusion_start = generated_text.find("\n", conclusion_start) + 1
                    conclusion = generated_text[conclusion_start:].strip()
        else:
            # Found key insights
            summary = generated_text[summary_start:key_insights_start].strip()
            key_insights_start = generated_text.find("\n", key_insights_start) + 1
            
            if conclusion_start == -1:
                # No conclusion found
                if references_pos != -1 and references_pos > key_insights_start:
                    key_insights = generated_text[key_insights_start:references_pos].strip()
                else:
                    key_insights = generated_text[key_insights_start:].strip()
                
                # Try to extract conclusion from the text
                extracted_conclusion = extract_conclusion_from_text(key_insights)
                if extracted_conclusion:
                    # Remove the conclusion part from key insights
                    conclusion_marker_pos = key_insights.lower().find(next(
                        marker for marker in conclusion_markers 
                        if marker in key_insights.lower()
                    ))
                    if conclusion_marker_pos != -1:
                        key_insights = key_insights[:conclusion_marker_pos].strip()
                    conclusion = extracted_conclusion
                else:
                    conclusion = "No conclusion found."
            else:
                # Both key insights and conclusion found
                key_insights = generated_text[key_insights_start:conclusion_start].strip()
                
                if references_pos != -1 and references_pos > conclusion_start:
                    conclusion = generated_text[conclusion_start:references_pos].strip()
                else:
                    conclusion_start = generated_text.find("\n", conclusion_start) + 1
                    conclusion = generated_text[conclusion_start:].strip()
        
        # Check if key insights are already numbered (e.g., "1.", "2.", etc.)
        has_numbered_points = bool(re.search(r'^\d+\.', key_insights.strip(), re.MULTILINE))
        
        # Format key insights as bullet points if they aren't already
        if not has_numbered_points and not any(line.strip().startswith(("-", "*", "•")) for line in key_insights.split("\n") if line.strip()):
            # Split by newlines and create bullet points
            insights_lines = key_insights.split("\n")
            formatted_insights = []
            for line in insights_lines:
                line = line.strip()
                if line and not any(line.upper().startswith(pattern.upper()) for pattern in key_insights_patterns + alternate_patterns):
                    formatted_insights.append(f"- {line}")
            key_insights = "\n".join(formatted_insights)
        
        # Clean up section headers that might have been included
        summary = summary.strip()
        for pattern in summary_patterns:
            if summary.upper().startswith(pattern.upper()):
                summary = summary[len(pattern):].strip()
        
        key_insights = key_insights.strip()
        for pattern in key_insights_patterns + alternate_patterns:
            if key_insights.upper().startswith(pattern.upper()):
                key_insights = key_insights[len(pattern):].strip()
        
        conclusion = conclusion.strip()
        for pattern in conclusion_patterns:
            if conclusion.upper().startswith(pattern.upper()):
                conclusion = conclusion[len(pattern):].strip()
        
        # Apply the markdown template
        markdown_text = MARKDOWN_TEMPLATE.format(
            title=title,
            summary=summary,
            key_insights=key_insights,
            conclusion=conclusion
        )
        
        # Check if there's a memory warning in the original text
        if "memory warning" in generated_text.lower():
            memory_warning_match = re.search(r'(\*\*Memory Warning:.*?available)', generated_text, re.IGNORECASE | re.DOTALL)
            if memory_warning_match:
                warning_text = memory_warning_match.group(1)
                markdown_text = f"> {warning_text}\n\n{markdown_text}"
            else:
                # Generic memory warning if specific one not found
                markdown_text = "> **Memory Warning:** Low memory detected. Output quality may be affected.\n\n{markdown_text}"
        
        return markdown_text
    
    except Exception as e:
        logger.warning(f"Error formatting as markdown: {e}")
        # Return the original text if formatting fails
        return generated_text

def extract_key_insights_from_text(text):
    """Extract key insights from text based on common patterns."""
    insights = []
    
    # Look for phrases like "One key insight", "Another key insight", etc.
    insight_patterns = [
        r'([Oo]ne key insight is.*?\.(?:\s+[A-Z][^\.]+\.)*)',
        r'([Aa]nother (?:key|important) insight is.*?\.(?:\s+[A-Z][^\.]+\.)*)',
        r'([Aa] key insight is.*?\.(?:\s+[A-Z][^\.]+\.)*)',
        r'([Kk]ey insights?.*?:)(.*?)(?:\n\n|\Z)',
    ]
    
    for pattern in insight_patterns:
        matches = re.finditer(pattern, text, re.DOTALL)
        for match in matches:
            if len(match.groups()) > 1 and match.group(2):
                # For patterns with a header and content
                content = match.group(2).strip()
                if content:
                    insights.append(content)
            else:
                # For patterns with just content
                insights.append(match.group(1).strip())
    
    # If we found insights, format them as bullet points
    if insights:
        formatted_insights = []
        for insight in insights:
            if not insight.startswith('-'):
                formatted_insights.append(f"- {insight}")
            else:
                formatted_insights.append(insight)
        return "\n\n".join(formatted_insights)
    
    return None

def extract_conclusion_from_text(text):
    """Extract conclusion from text based on common patterns."""
    conclusion_patterns = [
        r'(?:[Ii]n conclusion|[Tt]o conclude|[Tt]o sum up|[Ii]n summary|[Tt]o summarize|[Ff]inally,|[Ii]n the end|[Uu]ltimately|[Ii]n closing)(.*?)(?:\n\n|\Z)',
        r'(?:[Cc]onclusion:)(.*?)(?:\n\n|\Z)',
    ]
    
    for pattern in conclusion_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            conclusion = match.group(1).strip()
            if conclusion:
                return conclusion
    
    return None

def generate_document(user_prompt: str, model_name: str = DEFAULT_MODEL, num_chunks: int = 5, format_markdown: bool = True) -> Dict[str, Any]:
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
    parser.add_argument("--chunks", "-c", type=int, default=5, 
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