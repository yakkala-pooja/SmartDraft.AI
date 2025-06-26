import React, { useRef, useEffect } from 'react';
import { Box, Paper, Typography, Tabs, Tab, Chip, Tooltip, IconButton } from '@mui/material';
import { 
  Edit as EditIcon, 
  Visibility as VisibilityIcon,
  ContentCopy as ContentCopyIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const Editor = ({ value, onChange, readOnly, status }) => {
  const [tab, setTab] = React.useState(0);
  const [copied, setCopied] = React.useState(false);
  const textareaRef = useRef(null);
  
  // Focus textarea when switching to edit tab
  useEffect(() => {
    if (tab === 0 && textareaRef.current && !readOnly) {
      textareaRef.current.focus();
    }
  }, [tab, readOnly]);

  const handleTabChange = (event, newValue) => {
    setTab(newValue);
  };
  
  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Paper 
        elevation={0}
        sx={{ 
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
          overflow: 'hidden',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.05)',
          backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.8), rgba(255,255,255,1))',
        }}
      >
        <Box 
          sx={{ 
            borderBottom: 1, 
            borderColor: 'divider', 
            px: 3, 
            py: 1.5,
            background: 'rgba(249, 250, 251, 0.8)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <Tabs 
            value={tab} 
            onChange={handleTabChange} 
            aria-label="editor tabs"
            sx={{
              '& .MuiTabs-indicator': {
                backgroundColor: 'primary.main',
                height: 3,
                borderRadius: '3px 3px 0 0'
              },
              '& .MuiTab-root': {
                minWidth: 100,
                fontWeight: 600,
                fontSize: '0.875rem',
                textTransform: 'none',
                '&.Mui-selected': {
                  color: 'primary.main',
                }
              }
            }}
          >
            <Tab 
              icon={<EditIcon fontSize="small" />} 
              iconPosition="start"
              label="Edit" 
              id="editor-tab-0"
              aria-controls="editor-tabpanel-0"
              disabled={readOnly}
            />
            <Tab 
              icon={<VisibilityIcon fontSize="small" />}
              iconPosition="start"
              label="Preview" 
              id="editor-tab-1"
              aria-controls="editor-tabpanel-1"
            />
          </Tabs>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {value && (
              <Tooltip title={copied ? "Copied!" : "Copy content"}>
                <IconButton 
                  size="small" 
                  onClick={handleCopy}
                  sx={{ 
                    color: copied ? 'success.main' : 'text.secondary',
                    '&:hover': { color: copied ? 'success.main' : 'primary.main' }
                  }}
                >
                  <ContentCopyIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            
            <Chip 
              icon={<InfoIcon sx={{ fontSize: '0.75rem !important' }} />}
              label={status} 
              size="small" 
              variant="outlined"
              sx={{ 
                borderRadius: 1.5, 
                bgcolor: 'background.paper', 
                fontWeight: 500,
                fontSize: '0.75rem',
                height: 24
              }}
            />
          </Box>
        </Box>
        
        <Box 
          role="tabpanel"
          hidden={tab !== 0}
          id="editor-tabpanel-0"
          aria-labelledby="editor-tab-0"
          sx={{ 
            flexGrow: 1, 
            display: 'flex', 
            flexDirection: 'column',
            overflow: 'auto',
            bgcolor: 'background.paper'
          }}
        >
          <Box 
            component="textarea"
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={readOnly}
            placeholder={readOnly ? "Generate a document to start editing..." : "Start typing..."}
            sx={{ 
              flexGrow: 1,
              width: '100%',
              p: 3,
              border: 'none',
              outline: 'none',
              resize: 'none',
              fontFamily: '"Roboto Mono", monospace',
              fontSize: '0.9rem',
              lineHeight: 1.7,
              backgroundColor: 'background.paper',
              color: 'text.primary',
              '&:disabled': {
                backgroundColor: 'background.paper',
                color: 'text.disabled',
                cursor: 'not-allowed'
              }
            }}
          />
        </Box>
        
        <Box 
          role="tabpanel"
          hidden={tab !== 1}
          id="editor-tabpanel-1"
          aria-labelledby="editor-tab-1"
          sx={{ 
            flexGrow: 1, 
            p: 3,
            overflow: 'auto',
            backgroundColor: 'background.paper'
          }}
          className="markdown-body"
        >
          {value ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                code({node, inline, className, children, ...props}) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={atomDark}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                      customStyle={{
                        borderRadius: '8px',
                        margin: '1em 0',
                      }}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {value}
            </ReactMarkdown>
          ) : (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              height: '100%',
              color: 'text.secondary',
              opacity: 0.7
            }}>
              <VisibilityIcon sx={{ fontSize: 40, mb: 2, opacity: 0.4 }} />
              <Typography variant="body1" sx={{ fontStyle: 'italic' }}>
                No content to preview
              </Typography>
              <Typography variant="caption">
                Generate a document or start typing in the Edit tab
              </Typography>
            </Box>
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default Editor; 