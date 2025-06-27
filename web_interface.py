import os
import json
import time
import uuid
import psutil
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# Lazy import smart_draft to avoid loading heavy dependencies at startup
import importlib

app = Flask(__name__)

# Create necessary directories
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

EVALUATION_DIR = Path("evaluation")
EVALUATION_DIR.mkdir(exist_ok=True)

# Default configuration
DEFAULT_MODEL = "phi"
DEFAULT_CHUNKS = 3
AVAILABLE_MODELS = ["phi", "tinyllama", "mistral", "llama3.2"]

# Model memory requirements (approximate in GB)
MODEL_MEMORY_REQUIREMENTS = {
    "phi": 2,
    "tinyllama": 2,
    "mistral": 7,
    "llama3.2": 8
}

# Global cache for sessions to reduce disk I/O
_sessions_cache = {}
_smart_draft_module = None

# Lazy load smart_draft module
def get_smart_draft():
    global _smart_draft_module
    if _smart_draft_module is not None:
        return _smart_draft_module
    
    try:
        _smart_draft_module = importlib.import_module('smart_draft')
        return _smart_draft_module
    except ImportError as e:
        app.logger.error(f"Failed to import smart_draft module: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Error loading smart_draft module: {e}")
        return None

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
            app.logger.warning(f"Low memory warning: {model_name} requires ~{required_memory_gb}GB but only {available_memory_gb:.1f}GB available")
        
        return {
            "has_enough": has_enough_memory,
            "required": required_memory_gb,
            "available": round(available_memory_gb, 1),
            "warning": None if has_enough_memory else f"Low memory warning: {model_name} requires ~{required_memory_gb}GB but only {available_memory_gb:.1f}GB available"
        }
    
    except Exception as e:
        app.logger.error(f"Error checking memory: {e}")
        # Default to True if we can't check
        return {
            "has_enough": True,
            "required": MODEL_MEMORY_REQUIREMENTS.get(model_name, 4),
            "available": None,
            "warning": None
        }

def preload_resources():
    """Preload resources in a background thread."""
    try:
        # Get the smart_draft module
        smart_draft = get_smart_draft()
        if smart_draft:
            # Preload embedding model
            smart_draft.get_embedding_model()
            
            # Preload index and sample data
            smart_draft.load_index_and_sample()
            
            app.logger.info("Resources preloaded successfully")
    except Exception as e:
        app.logger.error(f"Error preloading resources: {e}")

# Replace before_first_request with a proper initialization
def start_background_tasks():
    """Start background tasks when the app starts."""
    app.logger.info("Starting resource preloading...")
    thread = threading.Thread(target=preload_resources)
    thread.daemon = True
    thread.start()

# Call the initialization function when the app starts
with app.app_context():
    start_background_tasks()

@app.route('/')
def index():
    """Render the main page."""
    # Get memory info for model selection guidance
    memory_info = {}
    try:
        mem = psutil.virtual_memory()
        available_memory_gb = mem.available / (1024 ** 3)
        
        for model in AVAILABLE_MODELS:
            required_memory = MODEL_MEMORY_REQUIREMENTS.get(model, 4)
            memory_info[model] = {
                "required": required_memory,
                "available": round(available_memory_gb, 1),
                "sufficient": available_memory_gb >= (required_memory * 1.2)
            }
    except Exception as e:
        app.logger.error(f"Error getting memory info: {e}")
        memory_info = {}
    
    return render_template('index.html', 
                          models=AVAILABLE_MODELS, 
                          default_model=DEFAULT_MODEL,
                          memory_info=memory_info)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a document based on the user's prompt."""
    data = request.json
    user_prompt = data.get('prompt', '')
    model_name = data.get('model', DEFAULT_MODEL)
    num_chunks = int(data.get('chunks', DEFAULT_CHUNKS))
    session_id = data.get('sessionId', str(uuid.uuid4()))
    
    if not user_prompt:
        return jsonify({
            'error': 'No prompt provided',
            'sessionId': session_id
        }), 400
    
    # Check memory requirements but don't block generation
    memory_status = check_memory_requirements(model_name)
    memory_warning = memory_status.get("warning")
    
    try:
        # Lazy load smart_draft module
        smart_draft = get_smart_draft()
        if not smart_draft:
            return jsonify({
                'error': 'Failed to load document generation module',
                'sessionId': session_id
            }), 500
        
        # Set a timeout for the generation process
        import signal
        import threading
        from contextlib import contextmanager
        
        @contextmanager
        def timeout_handler(seconds):
            if os.name != 'nt':  # Unix systems
                def handle_timeout(signum, frame):
                    raise TimeoutError(f"Document generation timed out after {seconds} seconds")
                
                original_handler = signal.signal(signal.SIGALRM, handle_timeout)
                try:
                    signal.alarm(seconds)
                    yield
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
            else:  # Windows systems
                timer = None
                timeout_occurred = False
                
                def handle_timeout():
                    nonlocal timeout_occurred
                    timeout_occurred = True
                
                timer = threading.Timer(seconds, handle_timeout)
                timer.start()
                try:
                    yield
                    if timeout_occurred:
                        raise TimeoutError(f"Document generation timed out after {seconds} seconds")
                finally:
                    timer.cancel()
        
        # Generate the document with a 4-minute timeout
        try:
            with timeout_handler(240):  # 4 minutes
                document = smart_draft.generate_document(user_prompt, model_name, num_chunks, True)
        except TimeoutError as e:
            app.logger.error(f"Timeout error: {e}")
            return jsonify({
                'error': 'Document generation timed out. Try using a smaller model or fewer chunks.',
                'sessionId': session_id
            }), 504  # Gateway Timeout
        
        # Add session ID and save timestamp
        document['sessionId'] = session_id
        document['saveTimestamp'] = datetime.now().isoformat()
        
        # Include memory warning if present
        if memory_warning:
            document['memory_warning'] = memory_warning
        
        # Save to session storage (server-side)
        session_file = OUTPUT_DIR / f"session_{session_id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(document, f, indent=2)
        
        # Update cache
        _sessions_cache[session_id] = document
        
        response_data = {
            'document': document,
            'sessionId': session_id
        }
        
        # Add memory warning to response if present
        if memory_warning:
            response_data['memory_warning'] = memory_warning
            
        return jsonify(response_data)
    
    except MemoryError:
        app.logger.error("Memory error occurred during document generation")
        return jsonify({
            'error': 'Not enough memory to generate document. Try using a smaller model or fewer chunks.',
            'sessionId': session_id
        }), 500
    except Exception as e:
        app.logger.error(f"Error generating document: {str(e)}")
        return jsonify({
            'error': str(e),
            'sessionId': session_id
        }), 500

@app.route('/save', methods=['POST'])
def save():
    """Save the current document."""
    data = request.json
    document = data.get('document', {})
    filename = data.get('filename', None)
    session_id = data.get('sessionId', str(uuid.uuid4()))
    
    if not document:
        return jsonify({
            'error': 'No document provided',
            'sessionId': session_id
        }), 400
    
    try:
        # Lazy load smart_draft module
        smart_draft = get_smart_draft()
        if not smart_draft:
            return jsonify({
                'error': 'Failed to load document saving module',
                'sessionId': session_id
            }), 500
        
        # Update document with latest timestamp
        document['saveTimestamp'] = datetime.now().isoformat()
        
        # Save the document
        saved_path = smart_draft.save_document(document, filename)
        
        # Update session storage
        session_file = OUTPUT_DIR / f"session_{session_id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(document, f, indent=2)
        
        # Update cache
        _sessions_cache[session_id] = document
        
        return jsonify({
            'path': saved_path,
            'sessionId': session_id
        })
    
    except Exception as e:
        app.logger.error(f"Error saving document: {str(e)}")
        return jsonify({
            'error': str(e),
            'sessionId': session_id
        }), 500

@app.route('/export/<session_id>', methods=['GET'])
def export_document(session_id):
    """Export the document as a markdown file."""
    try:
        # Check cache first
        if session_id in _sessions_cache:
            document = _sessions_cache[session_id]
        else:
            # Load the session file
            session_file = OUTPUT_DIR / f"session_{session_id}.json"
            if not session_file.exists():
                return jsonify({'error': 'Session not found'}), 404
            
            with open(session_file, 'r', encoding='utf-8') as f:
                document = json.load(f)
                # Update cache
                _sessions_cache[session_id] = document
        
        # Create a temporary file for download
        temp_file = OUTPUT_DIR / f"export_{session_id}.md"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(document['formatted_text'])
        
        # Generate a filename based on the prompt
        words = document['user_prompt'].split()[:5]
        filename = "_".join(words).lower() + ".md"
        filename = "".join(c if c.isalnum() or c == "_" else "_" for c in filename)
        
        return send_file(
            temp_file,
            as_attachment=True,
            download_name=filename,
            mimetype='text/markdown'
        )
    
    except Exception as e:
        app.logger.error(f"Error exporting document: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/evaluate', methods=['POST'])
def evaluate():
    """Save evaluation data."""
    data = request.json
    document = data.get('document', {})
    relevance = data.get('relevance', 0)
    time_saved = data.get('timeSaved', 0)
    session_id = data.get('sessionId', '')
    
    if not document:
        return jsonify({'error': 'No document provided'}), 400
    
    try:
        # Add evaluation metrics
        document['relevance_rating'] = relevance
        document['time_saved'] = time_saved
        document['evaluation_timestamp'] = datetime.now().isoformat()
        
        # Save evaluation data
        eval_path = EVALUATION_DIR / f"eval_{session_id}_{int(time.time())}.json"
        with open(eval_path, 'w', encoding='utf-8') as f:
            json.dump(document, f, indent=2)
        
        # Update cache if present
        if session_id in _sessions_cache:
            _sessions_cache[session_id].update({
                'relevance_rating': relevance,
                'time_saved': time_saved,
                'evaluation_timestamp': document['evaluation_timestamp']
            })
        
        return jsonify({'success': True})
    
    except Exception as e:
        app.logger.error(f"Error saving evaluation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sessions', methods=['GET'])
def list_sessions():
    """List all available sessions."""
    try:
        sessions = []
        for file in OUTPUT_DIR.glob('session_*.json'):
            try:
                session_id = file.stem.replace('session_', '')
                
                # Check cache first
                if session_id in _sessions_cache:
                    session = _sessions_cache[session_id]
                    sessions.append({
                        'sessionId': session_id,
                        'prompt': session.get('user_prompt', ''),
                        'timestamp': session.get('saveTimestamp', ''),
                        'model': session.get('model', '')
                    })
                else:
                    # Read from file
                    with open(file, 'r', encoding='utf-8') as f:
                        session = json.load(f)
                        # Update cache
                        _sessions_cache[session_id] = session
                        sessions.append({
                            'sessionId': session_id,
                            'prompt': session.get('user_prompt', ''),
                            'timestamp': session.get('saveTimestamp', ''),
                            'model': session.get('model', '')
                        })
            except Exception as e:
                app.logger.warning(f"Error reading session file {file}: {str(e)}")
                continue
        
        # Sort sessions by timestamp (newest first)
        sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({'sessions': sessions})
    
    except Exception as e:
        app.logger.error(f"Error listing sessions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session."""
    try:
        # Check cache first
        if session_id in _sessions_cache:
            document = _sessions_cache[session_id]
            return jsonify({'document': document})
        
        # Load from file if not in cache
        session_file = OUTPUT_DIR / f"session_{session_id}.json"
        if not session_file.exists():
            return jsonify({'error': 'Session not found'}), 404
        
        with open(session_file, 'r', encoding='utf-8') as f:
            document = json.load(f)
            # Update cache
            _sessions_cache[session_id] = document
        
        return jsonify({'document': document})
    
    except Exception as e:
        app.logger.error(f"Error retrieving session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Check the status of the API."""
    memory_info = {}
    try:
        mem = psutil.virtual_memory()
        memory_info = {
            "total": round(mem.total / (1024 ** 3), 1),
            "available": round(mem.available / (1024 ** 3), 1),
            "percent_used": mem.percent
        }
    except Exception as e:
        app.logger.error(f"Error getting memory info: {e}")
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'memory': memory_info,
        'cached_sessions': len(_sessions_cache)
    })

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear the server-side cache."""
    global _sessions_cache
    try:
        cache_size = len(_sessions_cache)
        _sessions_cache = {}
        return jsonify({
            'success': True,
            'message': f'Cleared {cache_size} items from cache'
        })
    except Exception as e:
        app.logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(500)
def server_error(e):
    """Handle server errors."""
    app.logger.error(f"Server error: {str(e)}")
    return jsonify({
        'error': 'An internal server error occurred',
        'message': str(e)
    }), 500

@app.errorhandler(404)
def not_found(e):
    """Handle not found errors."""
    return jsonify({
        'error': 'Resource not found',
        'message': str(e)
    }), 404

if __name__ == "__main__":
    # Start the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000) 