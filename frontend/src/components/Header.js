import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  Box, 
  useTheme, 
  useMediaQuery,
  Avatar,
  Chip
} from '@mui/material';
import { 
  Description as DescriptionIcon,
  Folder as FolderIcon
} from '@mui/icons-material';

const Header = ({ onOpenSessions }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <AppBar 
      position="static" 
      elevation={0} 
      sx={{ 
        backgroundImage: 'linear-gradient(to right, #6366f1, #4f46e5)',
        color: 'white',
        borderBottom: 'none',
      }}
    >
      <Toolbar sx={{ py: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Avatar 
            sx={{ 
              bgcolor: 'white', 
              color: 'primary.main', 
              width: 38, 
              height: 38, 
              mr: 1.5,
              boxShadow: '0 2px 10px rgba(0,0,0,0.12)',
              border: '2px solid rgba(255,255,255,0.8)'
            }}
          >
            <DescriptionIcon />
          </Avatar>
          <Box>
            <Typography variant="h6" component="div" sx={{ fontWeight: 700, letterSpacing: '-0.5px' }}>
              SmartDraft.AI
            </Typography>
            {!isMobile && (
              <Typography variant="caption" sx={{ opacity: 0.9, display: 'block', mt: -0.5 }}>
                AI-powered document generation
              </Typography>
            )}
          </Box>
        </Box>
        
        <Box sx={{ flexGrow: 1 }} />
        
        <Button 
          variant="contained" 
          startIcon={<FolderIcon />}
          onClick={onOpenSessions}
          size={isMobile ? 'small' : 'medium'}
          sx={{ 
            bgcolor: 'rgba(255,255,255,0.15)', 
            '&:hover': { 
              bgcolor: 'rgba(255,255,255,0.25)' 
            },
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            px: 2
          }}
        >
          {isMobile ? 'Drafts' : 'My Documents'}
        </Button>
        
        <Chip
          label="Beta"
          size="small"
          sx={{
            ml: 2,
            bgcolor: 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: 600,
            fontSize: '0.65rem',
            height: 22,
            border: '1px solid rgba(255,255,255,0.3)',
            display: { xs: 'none', sm: 'flex' }
          }}
        />
      </Toolbar>
    </AppBar>
  );
};

export default Header; 