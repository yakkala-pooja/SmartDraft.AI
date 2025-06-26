import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Box,
  Typography,
  List,
  ListItemButton,
  Chip,
  Tooltip,
  Paper,
  IconButton,
  CircularProgress,
  Alert
} from '@mui/material';
import {
  Description as DescriptionIcon,
  Close as CloseIcon,
  FolderOpen as FolderIcon,
  AccessTime as TimeIcon
} from '@mui/icons-material';

const SessionsDrawer = ({ open, onClose, onSelect }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (open) {
      fetchSessions();
    }
  }, [open]);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/sessions');
      const data = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Sort sessions by timestamp (newest first)
      const sortedSessions = data.sessions.sort((a, b) => {
        return new Date(b.timestamp) - new Date(a.timestamp);
      });
      
      setSessions(sortedSessions);
    } catch (error) {
      console.error('Error loading sessions:', error);
      setError('Failed to load sessions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      
      // If it's today, just show the time
      const today = new Date();
      if (date.toDateString() === today.toDateString()) {
        return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      }
      
      // If it's yesterday, show "Yesterday"
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      if (date.toDateString() === yesterday.toDateString()) {
        return `Yesterday at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      }
      
      // Otherwise show full date
      return date.toLocaleDateString([], { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
      }) + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (error) {
      return dateString;
    }
  };

  const truncateText = (text, maxLength = 50) => {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };
  
  const getModelColor = (modelName) => {
    if (!modelName) return '#9ca3af';
    
    const modelColors = {
      'phi': '#10b981',
      'tinyllama': '#f59e0b',
      'mistral': '#6366f1',
      'llama3.2': '#ec4899'
    };
    
    return modelColors[modelName.toLowerCase()] || '#9ca3af';
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { 
          width: { xs: '100%', sm: 400 },
          boxShadow: '-5px 0 25px rgba(0, 0, 0, 0.1)'
        }
      }}
    >
      <Box 
        sx={{ 
          p: 2.5, 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          borderBottom: '1px solid',
          borderColor: 'divider',
          background: 'linear-gradient(to right, rgba(99, 102, 241, 0.05), rgba(99, 102, 241, 0.01))'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <FolderIcon sx={{ color: 'primary.main', mr: 1.5 }} />
          <Typography variant="h6" fontWeight={700} letterSpacing="-0.5px">
            My Documents
          </Typography>
        </Box>
        <IconButton onClick={onClose} edge="end" sx={{ color: 'text.secondary' }}>
          <CloseIcon />
        </IconButton>
      </Box>
      
      <Box sx={{ overflow: 'auto', flexGrow: 1, p: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={40} />
          </Box>
        ) : error ? (
          <Alert 
            severity="error" 
            sx={{ 
              my: 2,
              borderRadius: 2
            }}
          >
            {error}
          </Alert>
        ) : sessions.length === 0 ? (
          <Box sx={{ 
            py: 6, 
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            color: 'text.secondary'
          }}>
            <DescriptionIcon sx={{ fontSize: 48, mb: 2, opacity: 0.3 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No saved documents
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Generate your first document to see it here
            </Typography>
          </Box>
        ) : (
          <List sx={{ py: 1 }}>
            {sessions.map((session) => (
              <Paper
                key={session.sessionId}
                elevation={0}
                sx={{ 
                  mb: 2, 
                  borderRadius: 2,
                  overflow: 'hidden',
                  border: '1px solid',
                  borderColor: 'divider',
                  transition: 'all 0.2s',
                  '&:hover': {
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
                    borderColor: 'primary.main'
                  }
                }}
              >
                <ListItemButton 
                  onClick={() => onSelect(session.sessionId)}
                  sx={{ 
                    p: 0,
                    display: 'block'
                  }}
                >
                  <Box sx={{ p: 2 }}>
                    <Typography 
                      variant="subtitle1" 
                      fontWeight={600} 
                      sx={{ 
                        mb: 1,
                        lineHeight: 1.4,
                        color: 'text.primary'
                      }}
                    >
                      {truncateText(session.prompt, 70)}
                    </Typography>
                    
                    <Box sx={{ 
                      display: 'flex', 
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <TimeIcon sx={{ fontSize: '0.875rem', color: 'text.secondary', mr: 0.75 }} />
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(session.timestamp)}
                        </Typography>
                      </Box>
                      
                      {session.model && (
                        <Tooltip title="AI model used">
                          <Chip
                            label={session.model}
                            size="small"
                            sx={{
                              height: 22,
                              fontSize: '0.65rem',
                              fontWeight: 500,
                              bgcolor: `${getModelColor(session.model)}15`,
                              color: getModelColor(session.model),
                              border: '1px solid',
                              borderColor: `${getModelColor(session.model)}30`,
                            }}
                          />
                        </Tooltip>
                      )}
                    </Box>
                  </Box>
                </ListItemButton>
              </Paper>
            ))}
          </List>
        )}
      </Box>
    </Drawer>
  );
};

export default SessionsDrawer; 