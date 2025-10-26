import { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Button,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Alert,
  Divider,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  ThemeProvider,
  createTheme,
} from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import SendIcon from '@mui/icons-material/Send';
import SettingsIcon from '@mui/icons-material/Settings';
import HistoryIcon from '@mui/icons-material/History';
import FileUpload from './components/FileUpload';
import ModelSelector from './components/ModelSelector';
import AttributionTable from './components/AttributionTable';
import AttributionChart from './components/AttributionChart';
import StateRecovery from './components/StateRecovery';
import Settings from './components/Settings';
import { useAppState } from './hooks/useAppState';
import { attributionApi } from './services/api';
import type { AttributionModel, AttributionResponse } from './types/api';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
      light: '#ff5983',
      dark: '#9a0036',
    },
    background: {
      default: '#F9FAFB',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
    },
    h2: {
      fontWeight: 600,
    },
    h3: {
      fontWeight: 600,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
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
          fontWeight: 500,
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});

const steps = ['Upload File', 'Configure Analysis', 'View Results'];

function App() {
  // Use the new state management hook
  const {
    activeStep,
    selectedFile,
    selectedModel,
    results,
    error,
    loading,
    analysisHistory,
    preferences,
    setActiveStep,
    setSelectedFile,
    setSelectedModel,
    setResults,
    setError,
    setLoading,
    saveAnalysisToHistory,
    loadFromHistory,
    resetState,
    hasRecoverableState,
    getRecoveryOptions,
    updatePreferences,
  } = useAppState();

  // UI state for dialogs
  const [showStateRecovery, setShowStateRecovery] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await attributionApi.analyzeAttribution(selectedFile, {
        model: selectedModel,
      });
      setResults(response);
      setActiveStep(2);
      
      // Save to history if auto-save is enabled
      if (preferences.autoSave) {
        saveAnalysisToHistory(selectedFile, selectedModel, response);
      }
    } catch (err: any) {
      // Handle different error formats
      let errorMessage = 'Failed to analyze attribution';
      
      if (err.response?.data) {
        const data = err.response.data;
        if (typeof data === 'string') {
          errorMessage = data;
        } else if (data.detail) {
          errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        } else if (data.message) {
          errorMessage = data.message;
        } else {
          errorMessage = JSON.stringify(data);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    resetState();
  };

  // Check for recoverable state on app load
  useEffect(() => {
    if (hasRecoverableState() && !results && !selectedFile) {
      setShowStateRecovery(true);
    }
  }, [hasRecoverableState, results, selectedFile]);

  // Recovery handlers
  const handleRecoverSession = () => {
    setShowStateRecovery(false);
    // Session recovery is handled automatically by the state manager
  };

  const handleRecoverResults = () => {
    setShowStateRecovery(false);
    setActiveStep(2);
  };

  const handleLoadFromHistory = (historyItem: any) => {
    loadFromHistory(historyItem);
    setShowStateRecovery(false);
  };

  const handleClearAll = () => {
    resetState();
    setShowStateRecovery(false);
  };

  const handleResetSettings = () => {
    updatePreferences({
      defaultModel: 'linear',
      autoSave: true,
      showAdvancedOptions: false,
      theme: 'light',
    });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div className="app-layout">
        {/* Fixed Sidebar */}
        <div className="sidebar">
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography 
              variant="h4" 
              component="h1" 
              fontWeight="bold"
              sx={{ 
                background: 'linear-gradient(45deg, #1976d2, #dc004e)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                mb: 2
              }}
            >
              Rabbit
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Attribution Analysis
            </Typography>
            
            {/* Action Buttons */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Tooltip title="View Analysis History" arrow>
                <IconButton 
                  onClick={() => setShowStateRecovery(true)}
                  color="primary"
                  sx={{ mb: 1 }}
                >
                  <HistoryIcon />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Settings & Preferences" arrow>
                <IconButton 
                  onClick={() => setShowSettings(true)}
                  color="primary"
                >
                  <SettingsIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </div>

        {/* Main Content Area */}
        <div className="main-content">
          <Container maxWidth="lg" sx={{ py: 4 }}>
            <div className="content-card">
              <Stepper 
                activeStep={activeStep} 
                sx={{ 
                  mb: 6,
                  '& .MuiStepLabel-root': {
                    '& .MuiStepLabel-label': {
                      fontSize: '0.9rem',
                      fontWeight: 500
                    }
                  }
                }}
              >
                {steps.map((label) => (
                  <Step key={label}>
                    <StepLabel>{label}</StepLabel>
                  </Step>
                ))}
              </Stepper>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {activeStep === 0 && (
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" gutterBottom fontWeight="600" color="primary">
                Step 1: Upload Your Data
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 500, mx: 'auto' }}>
                Upload a CSV, JSON, or Parquet file with your marketing touchpoint data
              </Typography>
              <Box sx={{ maxWidth: 600, mx: 'auto' }}>
                <FileUpload onFileSelect={handleFileSelect} disabled={loading} />
              </Box>
              {selectedFile && (
                <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
                  <Button
                    variant="contained"
                    size="large"
                    onClick={() => setActiveStep(1)}
                    disabled={!selectedFile}
                    sx={{ px: 4, py: 1.5 }}
                  >
                    Continue
                  </Button>
                </Box>
              )}
            </Box>
          )}

          {activeStep === 1 && (
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h4" gutterBottom fontWeight="600" color="primary">
                Step 2: Configure Analysis
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: 500, mx: 'auto' }}>
                Select an attribution model to apply to your data
              </Typography>
              <Box sx={{ maxWidth: 500, mx: 'auto', mb: 4 }}>
                <ModelSelector
                  value={selectedModel}
                  onChange={setSelectedModel}
                  disabled={loading}
                />
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 4 }}>
                <Button 
                  variant="outlined" 
                  onClick={() => setActiveStep(0)}
                  size="large"
                  sx={{ px: 4, py: 1.5 }}
                >
                  Back
                </Button>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleAnalyze}
                  disabled={loading}
                  endIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
                  sx={{ px: 4, py: 1.5 }}
                >
                  {loading ? 'Analyzing...' : 'Run Analysis'}
                </Button>
              </Box>
            </Box>
          )}

          {activeStep === 2 && results && (
            <Box>
              <Box sx={{ textAlign: 'center', mb: 4 }}>
                <Typography variant="h4" gutterBottom fontWeight="600" color="primary">
                  Step 3: Results
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Your attribution analysis results
                </Typography>
              </Box>

              <Divider sx={{ my: 4 }} />

              {/* Results Section */}
              {/* KPI Score Cards */}
              <Box sx={{ mb: 4 }}>
                <AttributionTable results={results.results} showKPIsOnly={true} />
              </Box>


              {/* Pie Chart */}
              <Box sx={{ mb: 4 }}>
                <AttributionChart results={results.results} />
              </Box>

              {/* Channel Attribution Table */}
              <Box sx={{ mb: 4 }}>
                <AttributionTable results={results.results} showTableOnly={true} />
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 6 }}>
                <Button 
                  variant="outlined" 
                  onClick={handleReset}
                  size="large"
                  sx={{ px: 4, py: 1.5 }}
                >
                  Analyze Another File
                </Button>
              </Box>
            </Box>
          )}
            </div>
          </Container>
        </div>
      </div>

      {/* State Recovery Dialog */}
      <StateRecovery
        open={showStateRecovery}
        onClose={() => setShowStateRecovery(false)}
        onRecoverSession={handleRecoverSession}
        onRecoverResults={handleRecoverResults}
        onLoadFromHistory={handleLoadFromHistory}
        onClearAll={handleClearAll}
        recoveryOptions={getRecoveryOptions()}
        analysisHistory={analysisHistory}
      />

      {/* Settings Dialog */}
      <Settings
        open={showSettings}
        onClose={() => setShowSettings(false)}
        preferences={preferences}
        onSavePreferences={updatePreferences}
        onResetSettings={handleResetSettings}
      />
    </ThemeProvider>
  );
}

export default App;
