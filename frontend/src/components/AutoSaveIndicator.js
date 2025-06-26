import React from 'react';
import { Box, Typography } from '@mui/material';
import { Check as CheckIcon } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const AutoSaveIndicator = ({ show }) => {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ 
            duration: 0.3,
            ease: "easeOut"
          }}
        >
          <Box
            sx={{
              position: 'fixed',
              bottom: 20,
              right: 20,
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'rgba(16, 185, 129, 0.9)',
              color: 'white',
              padding: '6px 12px',
              borderRadius: '20px',
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              zIndex: 1300,
            }}
          >
            <CheckIcon 
              sx={{ 
                mr: 0.5, 
                fontSize: '0.9rem',
                animation: 'pulse 1.5s infinite ease-in-out',
                '@keyframes pulse': {
                  '0%': { opacity: 0.7 },
                  '50%': { opacity: 1 },
                  '100%': { opacity: 0.7 },
                }
              }} 
            />
            <Typography 
              variant="body2" 
              sx={{ 
                fontWeight: 600,
                letterSpacing: '0.01em',
                fontSize: '0.85rem'
              }}
            >
              Saved
            </Typography>
          </Box>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AutoSaveIndicator; 