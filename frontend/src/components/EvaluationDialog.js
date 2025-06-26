import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Rating,
  Slider,
  Paper,
  IconButton,
  Chip
} from '@mui/material';
import { 
  Star as StarIcon, 
  Close as CloseIcon,
  AccessTime as TimeIcon,
  ThumbUp as ThumbUpIcon
} from '@mui/icons-material';

const EvaluationDialog = ({ open, onClose, onSubmit }) => {
  const [relevance, setRelevance] = useState(3);
  const [timeSaved, setTimeSaved] = useState(5);
  const [hover, setHover] = useState(-1);

  const handleSubmit = () => {
    onSubmit(relevance, timeSaved);
    resetForm();
  };

  const resetForm = () => {
    setRelevance(3);
    setTimeSaved(5);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const labels = {
    1: 'Poor',
    2: 'Fair',
    3: 'Good',
    4: 'Very Good',
    5: 'Excellent'
  };
  
  const getLabelColor = (value) => {
    const colors = {
      1: '#ef4444',
      2: '#f59e0b',
      3: '#10b981',
      4: '#3b82f6',
      5: '#6366f1'
    };
    return colors[value] || colors[3];
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          overflow: 'hidden'
        }
      }}
    >
      <DialogTitle sx={{ 
        p: 2.5,
        background: 'linear-gradient(to right, rgba(99, 102, 241, 0.05), rgba(99, 102, 241, 0.01))',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <ThumbUpIcon sx={{ color: 'primary.main', mr: 1.5 }} />
          <Typography variant="h6" fontWeight={700} letterSpacing="-0.5px">
            Rate Document Quality
          </Typography>
        </Box>
        <IconButton
          edge="end"
          color="inherit"
          onClick={handleClose}
          aria-label="close"
          size="small"
          sx={{ color: 'text.secondary' }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ p: 3 }}>
        <Paper
          elevation={0}
          sx={{ 
            p: 2.5, 
            mb: 3, 
            borderRadius: 2,
            backgroundColor: 'rgba(99, 102, 241, 0.03)',
            border: '1px solid rgba(99, 102, 241, 0.08)',
          }}
        >
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Document Relevance
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', my: 1 }}>
            <Rating
              name="relevance-rating"
              value={relevance}
              precision={1}
              size="large"
              onChange={(event, newValue) => {
                setRelevance(newValue);
              }}
              onChangeActive={(event, newHover) => {
                setHover(newHover);
              }}
              emptyIcon={<StarIcon style={{ opacity: 0.55 }} fontSize="inherit" />}
              sx={{ 
                fontSize: '2.5rem',
                '& .MuiRating-iconFilled': {
                  color: getLabelColor(hover !== -1 ? hover : relevance)
                },
                '& .MuiRating-iconHover': {
                  color: getLabelColor(hover)
                }
              }}
            />
            
            <Chip 
              label={labels[hover !== -1 ? hover : relevance]} 
              size="small" 
              sx={{ 
                mt: 1.5,
                fontWeight: 600,
                color: getLabelColor(hover !== -1 ? hover : relevance),
                bgcolor: `${getLabelColor(hover !== -1 ? hover : relevance)}15`,
                border: '1px solid',
                borderColor: `${getLabelColor(hover !== -1 ? hover : relevance)}30`,
              }}
            />
          </Box>
          
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
            How relevant was the generated document to your request?
          </Typography>
        </Paper>
        
        <Paper
          elevation={0}
          sx={{ 
            p: 2.5, 
            borderRadius: 2,
            backgroundColor: 'rgba(16, 185, 129, 0.03)',
            border: '1px solid rgba(16, 185, 129, 0.08)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <TimeIcon sx={{ color: 'success.main', mr: 1 }} />
            <Typography variant="subtitle1" fontWeight={600}>
              Time Saved
            </Typography>
          </Box>
          
          <Box sx={{ px: 2 }}>
            <Slider
              value={timeSaved}
              onChange={(e, newValue) => setTimeSaved(newValue)}
              aria-labelledby="time-saved-slider"
              valueLabelDisplay="auto"
              step={1}
              marks
              min={0}
              max={30}
              color="success"
              valueLabelFormat={(value) => `${value} min`}
            />
            
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              mt: 1
            }}>
              <Typography variant="caption" color="text.secondary">
                0 minutes
              </Typography>
              <Typography variant="caption" color="text.secondary">
                30 minutes
              </Typography>
            </Box>
          </Box>
          
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 2 }}>
            Estimate how many minutes this tool saved you compared to writing manually
          </Typography>
        </Paper>
      </DialogContent>
      
      <DialogActions sx={{ px: 3, py: 2, borderTop: '1px solid', borderColor: 'divider' }}>
        <Button 
          onClick={handleClose} 
          color="inherit"
          sx={{ fontWeight: 500 }}
        >
          Cancel
        </Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained"
          color="primary"
          sx={{ 
            px: 3,
            boxShadow: '0 4px 14px 0 rgba(99, 102, 241, 0.39)',
            '&:hover': {
              boxShadow: '0 6px 20px 0 rgba(99, 102, 241, 0.5)'
            }
          }}
        >
          Submit Feedback
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EvaluationDialog; 