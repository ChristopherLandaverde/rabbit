import { useState } from 'react';
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
} from '@mui/material';
import {
  ThemeProvider,
  createTheme,
} from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import SendIcon from '@mui/icons-material/Send';
import FileUpload from './components/FileUpload';
import ModelSelector from './components/ModelSelector';
import AttributionTable from './components/AttributionTable';
import AttributionChart from './components/AttributionChart';
import { attributionApi } from './services/api';
import type { AttributionModel, AttributionResponse } from './types/api';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const steps = ['Upload File', 'Configure Analysis', 'View Results'];

function App() {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedModel, setSelectedModel] = useState<AttributionModel>('linear');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<AttributionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    setSelectedFile(null);
    setSelectedModel('linear');
    setResults(null);
    setError(null);
    setActiveStep(0);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
            Multi-Touch Attribution
          </Typography>
          <Typography variant="h6" color="text.secondary">
            Analyze marketing touchpoint data and apply attribution models
          </Typography>
        </Box>

        <Paper sx={{ p: 4, mb: 4 }}>
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
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
            <Box>
              <Typography variant="h5" gutterBottom>
                Step 1: Upload Your Data
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Upload a CSV, JSON, or Parquet file with your marketing touchpoint data
              </Typography>
              <FileUpload onFileSelect={handleFileSelect} disabled={loading} />
              {selectedFile && (
                <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(1)}
                    disabled={!selectedFile}
                  >
                    Continue
                  </Button>
                </Box>
              )}
            </Box>
          )}

          {activeStep === 1 && (
            <Box>
              <Typography variant="h5" gutterBottom>
                Step 2: Configure Analysis
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Select an attribution model to apply to your data
              </Typography>
              <ModelSelector
                value={selectedModel}
                onChange={setSelectedModel}
                disabled={loading}
              />
              <Box sx={{ mt: 4, display: 'flex', justifyContent: 'space-between' }}>
                <Button onClick={() => setActiveStep(0)}>Back</Button>
                <Button
                  variant="contained"
                  onClick={handleAnalyze}
                  disabled={loading}
                  endIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
                >
                  {loading ? 'Analyzing...' : 'Run Analysis'}
                </Button>
              </Box>
            </Box>
          )}

          {activeStep === 2 && results && (
            <Box>
              <Typography variant="h5" gutterBottom>
                Step 3: Results
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Your attribution analysis results
              </Typography>

              <Divider sx={{ my: 4 }} />

              <Box sx={{ mb: 4 }}>
                <Typography variant="h6">Results Summary</Typography>
                <pre>{JSON.stringify(results.results, null, 2)}</pre>
              </Box>

              {/* <Box sx={{ mb: 4 }}>
                <AttributionChart results={results.results} />
              </Box> */}

              <Box sx={{ mb: 4 }}>
                <AttributionTable results={results.results} />
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 4 }}>
                <Button variant="outlined" onClick={handleReset}>
                  Analyze Another File
                </Button>
              </Box>
            </Box>
          )}
        </Paper>
      </Container>
    </ThemeProvider>
  );
}

export default App;
