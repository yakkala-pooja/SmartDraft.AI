import React from 'react';
import { Box, Paper } from '@mui/material';

const Sidebar = ({ children }) => {
  return (
    <Box 
      component="aside" 
      sx={{ 
        width: 340,
        flexShrink: 0,
        display: { xs: 'none', md: 'block' }
      }}
    >
      <Paper 
        elevation={0}
        sx={{ 
          p: 3,
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
          height: '100%',
          backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.8), rgba(255,255,255,1))',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.05)',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '4px',
            background: 'linear-gradient(90deg, #6366f1, #818cf8)',
            borderTopLeftRadius: '12px',
            borderTopRightRadius: '12px',
          },
          '&::after': {
            content: '""',
            position: 'absolute',
            top: 20,
            right: -40,
            width: 120,
            height: 120,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, rgba(99, 102, 241, 0) 70%)',
            zIndex: 0,
          }
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          {children}
        </Box>
      </Paper>
    </Box>
  );
};

export default Sidebar; 