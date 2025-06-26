import React from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Divider,
  Stack,
  Paper,
  Tooltip,
  Chip
} from '@mui/material';
import { 
  FileDownload as FileDownloadIcon,
  ContentCopy as ContentCopyIcon,
  Add as AddIcon,
  Star as StarIcon,
  Timer as TimerIcon,
  SmartToy as SmartToyIcon
} from '@mui/icons-material';

const DocumentActions = ({ document, onExport, onCopy, onNew, onEvaluate }) => {
  const isDocumentLoaded = !!document;
  
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <SmartToyIcon sx={{ color: 'secondary.main', mr: 1.5 }} />
        <Typography variant="h6" fontWeight={700} letterSpacing="-0.5px">
          Document Actions
        </Typography>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      <Stack spacing={2}>
        <Button
          variant="contained"
          color="success"
          startIcon={<FileDownloadIcon />}
          onClick={onExport}
          disabled={!isDocumentLoaded}
          fullWidth
          sx={{ 
            py: 1.2,
            borderRadius: 2,
            boxShadow: '0 4px 14px 0 rgba(16, 185, 129, 0.39)',
            '&:hover': {
              boxShadow: '0 6px 20px 0 rgba(16, 185, 129, 0.5)'
            }
          }}
        >
          Export as Markdown
        </Button>
        
        <Button
          variant="outlined"
          startIcon={<ContentCopyIcon />}
          onClick={onCopy}
          disabled={!isDocumentLoaded}
          fullWidth
          sx={{ 
            py: 1.2,
            borderRadius: 2,
            borderWidth: '1.5px',
            '&:hover': {
              borderWidth: '1.5px'
            }
          }}
        >
          Copy to Clipboard
        </Button>
        
        <Button
          variant="outlined"
          color="secondary"
          startIcon={<AddIcon />}
          onClick={onNew}
          fullWidth
          sx={{ 
            py: 1.2,
            borderRadius: 2,
            borderWidth: '1.5px',
            '&:hover': {
              borderWidth: '1.5px'
            }
          }}
        >
          New Document
        </Button>
        
        <Divider sx={{ my: 1 }}>
          <Chip 
            label="Feedback" 
            size="small" 
            sx={{ fontSize: '0.7rem', px: 0.5 }}
          />
        </Divider>
        
        <Button
          variant="outlined"
          color="info"
          startIcon={<StarIcon />}
          onClick={onEvaluate}
          disabled={!isDocumentLoaded}
          fullWidth
          sx={{ 
            py: 1.2,
            borderRadius: 2,
            borderWidth: '1.5px',
            '&:hover': {
              borderWidth: '1.5px'
            }
          }}
        >
          Rate Document Quality
        </Button>
      </Stack>
      
      {isDocumentLoaded && document.generation_time && (
        <Paper
          elevation={0}
          sx={{ 
            mt: 3, 
            p: 1.5, 
            borderRadius: 2, 
            backgroundColor: 'rgba(99, 102, 241, 0.04)',
            border: '1px solid rgba(99, 102, 241, 0.08)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
            <TimerIcon sx={{ fontSize: '0.9rem', color: 'text.secondary', mr: 1 }} />
            <Typography variant="caption" fontWeight={500}>
              Generation Details
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Time:
            </Typography>
            <Typography variant="caption" fontWeight={500}>
              {document.generation_time.toFixed(2)}s
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="caption" color="text.secondary">
              Model:
            </Typography>
            <Tooltip title="The AI model used for generation">
              <Chip
                label={document.model || 'Unknown'}
                size="small"
                variant="outlined"
                sx={{ 
                  height: 20, 
                  fontSize: '0.65rem',
                  fontWeight: 500
                }}
              />
            </Tooltip>
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default DocumentActions; 