import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  TextField, 
  Button,
  CircularProgress,
  Slider,
  FormHelperText,
  Divider,
  Paper,
  Chip,
  Stack,
  Avatar,
  Tooltip,
  Alert,
  LinearProgress
} from '@mui/material';
import { 
  Create as CreateIcon,
  Tune as TuneIcon,
  Bolt as BoltIcon,
  Memory as MemoryIcon,
  Timer as TimerIcon
} from '@mui/icons-material';

const models = [
  { value: 'phi', label: 'Phi', icon: '𝚽', color: '#10b981', memory: 2 },
  { value: 'tinyllama', label: 'TinyLlama', icon: '🦙', color: '#f59e0b', memory: 2 },
  { value: 'mistral', label: 'Mistral', icon: '🌪️', color: '#6366f1', memory: 7 },
  { value: 'llama3.2', label: 'Llama 3.2', icon: '🦙', color: '#ec4899', memory: 8 }
];

const GenerateForm = ({ onGenerate, isGenerating }) => {
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState('phi');
  const [chunks, setChunks] = useState(3);
  const [memoryWarning, setMemoryWarning] = useState(false);
  const [availableMemory, setAvailableMemory] = useState(null);
  const [generationTime, setGenerationTime] = useState(0);
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false);

  useEffect(() => {
    // Check memory status from the server
    const checkMemoryStatus = async () => {
      try {
        const response = await fetch('/status');
        const data = await response.json();
        
        if (data.memory && data.memory.available) {
          setAvailableMemory(data.memory.available);
          
          // Check if selected model might have memory issues
          const selectedModel = models.find(m => m.value === model);
          if (selectedModel && selectedModel.memory * 1.2 > data.memory.available) {
            setMemoryWarning(true);
          } else {
            setMemoryWarning(false);
          }
        }
      } catch (error) {
        console.error('Error checking memory status:', error);
      }
    };
    
    checkMemoryStatus();
  }, [model]);

  // Track generation time and show warning if it's taking too long
  useEffect(() => {
    let timer = null;
    
    if (isGenerating) {
      setGenerationTime(0);
      setShowTimeoutWarning(false);
      
      timer = setInterval(() => {
        setGenerationTime(prev => {
          const newTime = prev + 1;
          // Show timeout warning after 2 minutes
          if (newTime >= 120 && !showTimeoutWarning) {
            setShowTimeoutWarning(true);
          }
          return newTime;
        });
      }, 1000);
    } else {
      setGenerationTime(0);
      setShowTimeoutWarning(false);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isGenerating]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    onGenerate(prompt, model, chunks);
  };
  
  const selectedModel = models.find(m => m.value === model);
  
  const getMemoryStatus = (modelItem) => {
    if (!availableMemory) return null;
    
    const requiredMemory = modelItem.memory;
    const hasEnoughMemory = availableMemory >= requiredMemory * 1.2;
    
    return {
      hasEnough: hasEnoughMemory,
      text: hasEnoughMemory 
        ? `${requiredMemory}GB required (${availableMemory}GB available)` 
        : `${requiredMemory}GB required but only ${availableMemory}GB available`
    };
  };

  // Format generation time as mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <BoltIcon sx={{ color: 'primary.main', mr: 1.5 }} />
        <Typography variant="h6" fontWeight={700} letterSpacing="-0.5px">
          Create Document
        </Typography>
      </Box>
      
      <Divider sx={{ mb: 3 }} />
      
      <TextField
        label="Your Request"
        multiline
        rows={4}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Enter your request here..."
        fullWidth
        margin="normal"
        variant="outlined"
        required
        disabled={isGenerating}
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: 2,
            backgroundColor: 'background.paper',
            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.03)',
          },
          mb: 3
        }}
      />
      
      {memoryWarning && (
        <Alert 
          severity="warning" 
          sx={{ 
            mb: 3, 
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'warning.main',
            backgroundColor: 'warning.light',
            fontWeight: 500
          }}
          icon={<MemoryIcon />}
        >
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>
            Memory Warning
          </Typography>
          <Typography variant="body2">
            The selected model ({selectedModel.label}) requires approximately {selectedModel.memory}GB of RAM, 
            but your system only has {availableMemory}GB available. This may cause the generation to fail.
            Consider using a smaller model.
          </Typography>
        </Alert>
      )}
      
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          mb: 3,
          borderRadius: 3,
          backgroundColor: 'rgba(99, 102, 241, 0.03)',
          border: '1px solid rgba(99, 102, 241, 0.08)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ 
          position: 'absolute', 
          top: 0, 
          left: 0, 
          right: 0, 
          height: '3px', 
          background: 'linear-gradient(to right, #6366f1, #818cf8)' 
        }} />
        
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <TuneIcon sx={{ color: 'primary.main', fontSize: '1rem', mr: 1 }} />
          <Typography variant="subtitle2" fontWeight={600}>
            Generation Settings
          </Typography>
        </Box>
        
        <Stack spacing={2.5}>
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" fontWeight={500} gutterBottom>
                Language Model
              </Typography>
              
              {availableMemory && (
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <MemoryIcon sx={{ fontSize: '0.875rem', color: 'text.secondary', mr: 0.75 }} />
                  <Typography variant="caption" color="text.secondary">
                    {availableMemory}GB RAM available
                  </Typography>
                </Box>
              )}
            </Box>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {models.map((modelOption) => {
                const memoryStatus = getMemoryStatus(modelOption);
                const hasMemoryIssue = memoryStatus && !memoryStatus.hasEnough;
                
                return (
                  <Tooltip 
                    key={modelOption.value}
                    title={memoryStatus ? memoryStatus.text : `${modelOption.memory}GB RAM required`}
                    arrow
                  >
                    <Box
                      onClick={() => !isGenerating && setModel(modelOption.value)}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        p: 1,
                        borderRadius: 2,
                        border: '1px solid',
                        borderColor: model === modelOption.value 
                          ? (hasMemoryIssue ? 'warning.main' : modelOption.color) 
                          : 'divider',
                        bgcolor: model === modelOption.value 
                          ? (hasMemoryIssue ? 'warning.light' : `${modelOption.color}10`)
                          : 'background.paper',
                        cursor: isGenerating ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s',
                        opacity: isGenerating && model !== modelOption.value ? 0.5 : 1,
                        position: 'relative',
                        '&:hover': {
                          borderColor: !isGenerating 
                            ? (hasMemoryIssue ? 'warning.main' : modelOption.color) 
                            : undefined,
                          bgcolor: !isGenerating 
                            ? (hasMemoryIssue ? 'warning.light' : `${modelOption.color}05`)
                            : undefined
                        }
                      }}
                    >
                      <Avatar
                        sx={{
                          width: 28,
                          height: 28,
                          bgcolor: `${modelOption.color}20`,
                          color: modelOption.color,
                          fontSize: '1rem',
                          fontWeight: 'bold'
                        }}
                      >
                        {modelOption.icon}
                      </Avatar>
                      <Box>
                        <Typography variant="body2" fontWeight={500}>
                          {modelOption.label}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1 }}>
                          {modelOption.memory}GB
                        </Typography>
                      </Box>
                      {hasMemoryIssue && (
                        <Box 
                          sx={{ 
                            position: 'absolute',
                            top: -5,
                            right: -5,
                            width: 16,
                            height: 16,
                            borderRadius: '50%',
                            bgcolor: 'warning.main',
                            border: '2px solid white',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                          }}
                        />
                      )}
                    </Box>
                  </Tooltip>
                );
              })}
            </Box>
          </Box>
          
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography id="chunks-slider-label" variant="body2" fontWeight={500}>
                Content Chunks
              </Typography>
              <Chip 
                label={chunks} 
                size="small" 
                color="primary" 
                variant="filled"
                sx={{ height: 22, fontWeight: 600 }}
              />
            </Box>
            <Slider
              value={chunks}
              onChange={(e, newValue) => setChunks(newValue)}
              aria-labelledby="chunks-slider-label"
              valueLabelDisplay="auto"
              step={1}
              marks
              min={1}
              max={10}
              disabled={isGenerating}
              sx={{
                color: 'primary.main',
                '& .MuiSlider-thumb': {
                  width: 14,
                  height: 14,
                }
              }}
            />
            <FormHelperText>
              Number of content chunks to retrieve
            </FormHelperText>
          </Box>
        </Stack>
      </Paper>
      
              {isGenerating && (
        <Box sx={{ mt: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2" fontWeight={500}>
              Generating document...
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <TimerIcon sx={{ fontSize: '0.875rem', color: 'text.secondary', mr: 0.75 }} />
              <Typography variant="caption" color="text.secondary">
                {formatTime(generationTime)}
              </Typography>
            </Box>
          </Box>
          <LinearProgress 
            variant="indeterminate" 
            sx={{ 
              height: 6, 
              borderRadius: 3,
              backgroundColor: 'rgba(99, 102, 241, 0.1)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: 'primary.main',
              }
            }} 
          />
          
          {showTimeoutWarning && (
            <Alert 
              severity="info" 
              sx={{ 
                mt: 2, 
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'info.main',
                backgroundColor: 'info.light',
                fontWeight: 500
              }}
            >
              <Typography variant="body2">
                Document generation is taking longer than expected. This could be due to the model size or complexity of your request.
                Please be patient or try again with a smaller model.
              </Typography>
            </Alert>
          )}
        </Box>
      )}
      
      <Button
        type="submit"
        variant="contained"
        fullWidth
        size="large"
        startIcon={isGenerating ? null : <CreateIcon />}
        disabled={isGenerating || !prompt.trim()}
        sx={{ 
          py: 1.5,
          position: 'relative',
          borderRadius: 2,
          fontWeight: 600,
          fontSize: '0.95rem',
          boxShadow: '0 4px 14px 0 rgba(99, 102, 241, 0.39)',
          '&:hover': {
            boxShadow: '0 6px 20px 0 rgba(99, 102, 241, 0.5)'
          }
        }}
      >
        {isGenerating ? (
          <CircularProgress 
            size={24} 
            sx={{ 
              color: 'primary.light',
              position: 'absolute',
              top: '50%',
              left: '50%',
              marginTop: '-12px',
              marginLeft: '-12px',
            }} 
          />
        ) : (
          <>Generate with {selectedModel?.label}</>
        )}
      </Button>
    </Box>
  );
};

export default GenerateForm; 