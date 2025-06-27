import React, { useState, useEffect, useCallback } from 'react';
import { 
  ThemeProvider, 
  createTheme, 
  CssBaseline, 
  Box, 
  Container 
} from '@mui/material';
import { v4 as uuidv4 } from 'uuid';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Editor from './components/Editor';
import GenerateForm from './components/GenerateForm';
import DocumentActions from './components/DocumentActions';
import SessionsDrawer from './components/SessionsDrawer';
import EvaluationDialog from './components/EvaluationDialog';
import AutoSaveIndicator from './components/AutoSaveIndicator';
import { generateDocument, saveDocument, exportDocument } from './services/api';

// Create theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#6366f1',
      light: '#818cf8',
      dark: '#4f46e5',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#ec4899',
      light: '#f472b6',
      dark: '#db2777',
      contrastText: '#ffffff',
    },
    success: {
      main: '#10b981',
      light: '#34d399',
      dark: '#059669',
    },
    background: {
      default: '#f9fafb',
      paper: '#ffffff',
    },
    text: {
      primary: '#1f2937',
      secondary: '#6b7280',
    },
    divider: 'rgba(0, 0, 0, 0.06)',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: '-0.025em',
    },
    h2: {
      fontWeight: 700,
      letterSpacing: '-0.025em',
    },
    h6: {
      fontWeight: 600,
      letterSpacing: '-0.025em',
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
      letterSpacing: '-0.01em',
    },
    subtitle1: {
      letterSpacing: '-0.01em',
    },
    subtitle2: {
      letterSpacing: '-0.01em',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
          },
        },
        contained: {
          '&.MuiButton-containedPrimary': {
            backgroundImage: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
          },
          '&.MuiButton-containedSecondary': {
            backgroundImage: 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.03)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.03)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '& fieldset': {
              borderColor: 'rgba(0, 0, 0, 0.1)',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(0, 0, 0, 0.2)',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

function App() {
  // State
  const [sessionId, setSessionId] = useState(localStorage.getItem('currentSessionId') || null);
  const [document, setDocument] = useState(null);
  const [markdownContent, setMarkdownContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isEvaluationOpen, setIsEvaluationOpen] = useState(false);
  const [showAutoSave, setShowAutoSave] = useState(false);
  const [lastEditTime, setLastEditTime] = useState(Date.now());
  const [autoSaveTimeout, setAutoSaveTimeout] = useState(null);

  // Load document from localStorage on startup
  useEffect(() => {
    if (sessionId) {
      fetchSession(sessionId);
    }
  }, [sessionId]);
  
  const handleAutoSave = useCallback(async () => {
    if (!document || !sessionId) return;
    
    try {
      const updatedDocument = {
        ...document,
        formatted_text: markdownContent
      };
      
      await saveDocument(updatedDocument, null, sessionId);
      
      // Show auto-save indicator
      setShowAutoSave(true);
      setTimeout(() => setShowAutoSave(false), 2000);
    } catch (error) {
      console.error('Error auto-saving:', error);
    }
  }, [document, sessionId, markdownContent]);

  // Auto-save effect
  useEffect(() => {
    if (document && Date.now() - lastEditTime > 2000) {
      if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
      }
      
      const timeout = setTimeout(() => {
        handleAutoSave();
      }, 3000);
      
      setAutoSaveTimeout(timeout);
    }
    
    return () => {
      if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
      }
    };
  }, [markdownContent, lastEditTime, document, autoSaveTimeout, handleAutoSave]);

  const fetchSession = async (id) => {
    try {
      const response = await fetch(`/session/${id}`);
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      setDocument(data.document);
      setMarkdownContent(data.document.formatted_text);
    } catch (error) {
      console.error('Error fetching session:', error);
    }
  };

  const handleGenerate = async (prompt, model, chunks) => {
    setIsGenerating(true);
    
    try {
      const id = sessionId || uuidv4();
      
      const response = await generateDocument(prompt, model, chunks, id);
      
      setSessionId(response.sessionId);
      localStorage.setItem('currentSessionId', response.sessionId);
      
      setDocument(response.document);
      setMarkdownContent(response.document.formatted_text);
      
      // Show memory warning if present
      if (response.memory_warning) {
        const warningContent = `> **Memory Warning:** ${response.memory_warning}\n\n${response.document.formatted_text}`;
        setMarkdownContent(warningContent);
      }
    } catch (error) {
      console.error('Error generating document:', error);
      // Show error message to user
      setMarkdownContent(`# Error Generating Document\n\n${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleMarkdownChange = (value) => {
    setMarkdownContent(value);
    setLastEditTime(Date.now());
  };

  const handleExport = async () => {
    if (!sessionId) return;
    
    try {
      await exportDocument(sessionId);
    } catch (error) {
      console.error('Error exporting:', error);
    }
  };

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(markdownContent)
      .then(() => {
        alert('Document copied to clipboard!');
      })
      .catch(err => {
        console.error('Failed to copy:', err);
      });
  };

  const handleNewDocument = () => {
    setSessionId(null);
    setDocument(null);
    setMarkdownContent('');
    localStorage.removeItem('currentSessionId');
  };

  const handleEvaluate = () => {
    setIsEvaluationOpen(true);
  };

  const handleEvaluationSubmit = async (relevance, timeSaved) => {
    if (!document || !sessionId) return;
    
    try {
      await fetch('/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document,
          relevance,
          timeSaved,
          sessionId
        })
      });
      
      setIsEvaluationOpen(false);
    } catch (error) {
      console.error('Error submitting evaluation:', error);
    }
  };

  const handleSessionSelect = (id) => {
    setSessionId(id);
    localStorage.setItem('currentSessionId', id);
    setIsDrawerOpen(false);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header 
          onOpenSessions={() => setIsDrawerOpen(true)} 
        />
        
        <Container maxWidth="xl" sx={{ flexGrow: 1, py: 4 }}>
          <Box sx={{ display: 'flex', gap: 3 }}>
            <Sidebar>
              <GenerateForm 
                onGenerate={handleGenerate} 
                isGenerating={isGenerating} 
              />
              
              <DocumentActions 
                document={document}
                onExport={handleExport}
                onCopy={handleCopyToClipboard}
                onNew={handleNewDocument}
                onEvaluate={handleEvaluate}
              />
            </Sidebar>
            
            <Editor 
              value={markdownContent} 
              onChange={handleMarkdownChange} 
              readOnly={!document}
              status={document ? 'Document loaded' : 'No document loaded'}
            />
          </Box>
        </Container>
      </Box>
      
      <SessionsDrawer 
        open={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)} 
        onSelect={handleSessionSelect}
      />
      
      <EvaluationDialog 
        open={isEvaluationOpen} 
        onClose={() => setIsEvaluationOpen(false)} 
        onSubmit={handleEvaluationSubmit}
      />
      
      <AutoSaveIndicator show={showAutoSave} />
    </ThemeProvider>
  );
}

export default App; 