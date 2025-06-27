/**
 * API service for SmartDraft.AI
 */

/**
 * Retry a function with exponential backoff
 * @param {Function} fn - Function to retry
 * @param {number} maxRetries - Maximum number of retries
 * @param {number} baseDelay - Base delay in ms
 * @returns {Promise<any>} - Result of the function
 */
const retryWithBackoff = async (fn, maxRetries = 3, baseDelay = 300) => {
  let retries = 0;
  
  while (true) {
    try {
      return await fn();
    } catch (error) {
      retries++;
      
      // If we've reached max retries, throw
      if (retries >= maxRetries) {
        throw error;
      }
      
      // Calculate delay with exponential backoff
      const delay = baseDelay * Math.pow(2, retries - 1);
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
};

/**
 * Generate a document based on a prompt
 * @param {string} prompt - The user's prompt
 * @param {string} model - The model to use
 * @param {number} chunks - Number of content chunks to retrieve
 * @param {string} sessionId - Optional session ID
 * @returns {Promise<Object>} - Response with document and session ID
 */
export const generateDocument = async (prompt, model, chunks, sessionId = null) => {
  try {
    const fetchFn = async () => {
      const response = await fetch('/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt,
          model,
          chunks,
          sessionId
        }),
        // Add timeout to prevent hanging requests
        signal: AbortSignal.timeout(300000) // 5 minute timeout (increased from 2 minutes)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        // Specifically handle memory errors with a clearer message
        if (errorData.error && errorData.error.includes('memory')) {
          throw new Error(`Memory Error: ${errorData.error}`);
        }
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data;
    };
    
    return await retryWithBackoff(fetchFn);
  } catch (error) {
    console.error('Error generating document:', error);
    throw error;
  }
};

/**
 * Save a document
 * @param {Object} document - The document to save
 * @param {string|null} filename - Optional filename
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} - Response with path and session ID
 */
export const saveDocument = async (document, filename = null, sessionId) => {
  try {
    const fetchFn = async () => {
      const response = await fetch('/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document,
          filename,
          sessionId
        }),
        signal: AbortSignal.timeout(30000) // 30 second timeout
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data;
    };
    
    return await retryWithBackoff(fetchFn);
  } catch (error) {
    console.error('Error saving document:', error);
    throw error;
  }
};

/**
 * Export a document as markdown
 * @param {string} sessionId - Session ID
 * @returns {Promise<void>} - Opens download in new tab
 */
export const exportDocument = async (sessionId) => {
  try {
    // Open in new tab to trigger download
    window.open(`/export/${sessionId}`, '_blank');
  } catch (error) {
    console.error('Error exporting document:', error);
    throw error;
  }
};

/**
 * Fetch all sessions
 * @returns {Promise<Array>} - List of sessions
 */
export const fetchSessions = async () => {
  try {
    const fetchFn = async () => {
      const response = await fetch('/sessions', {
        signal: AbortSignal.timeout(10000) // 10 second timeout
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data.sessions;
    };
    
    return await retryWithBackoff(fetchFn);
  } catch (error) {
    console.error('Error fetching sessions:', error);
    throw error;
  }
};

/**
 * Fetch a specific session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} - Session document
 */
export const fetchSession = async (sessionId) => {
  try {
    const fetchFn = async () => {
      const response = await fetch(`/session/${sessionId}`, {
        signal: AbortSignal.timeout(10000) // 10 second timeout
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data.document;
    };
    
    return await retryWithBackoff(fetchFn);
  } catch (error) {
    console.error('Error fetching session:', error);
    throw error;
  }
};

/**
 * Submit evaluation for a document
 * @param {Object} document - The document to evaluate
 * @param {number} relevance - Relevance rating (1-5)
 * @param {number} timeSaved - Time saved in minutes
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} - Response
 */
export const submitEvaluation = async (document, relevance, timeSaved, sessionId) => {
  try {
    const fetchFn = async () => {
      const response = await fetch('/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document,
          relevance,
          timeSaved,
          sessionId
        }),
        signal: AbortSignal.timeout(10000) // 10 second timeout
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data;
    };
    
    return await retryWithBackoff(fetchFn);
  } catch (error) {
    console.error('Error submitting evaluation:', error);
    throw error;
  }
};

/**
 * Clear the server-side cache
 * @returns {Promise<Object>} - Response
 */
export const clearCache = async () => {
  try {
    const response = await fetch('/clear-cache', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (data.error) {
      throw new Error(data.error);
    }
    
    return data;
  } catch (error) {
    console.error('Error clearing cache:', error);
    throw error;
  }
}; 