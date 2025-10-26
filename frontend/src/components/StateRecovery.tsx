import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
  Divider,
} from '@mui/material';
import {
  History as HistoryIcon,
  FileUpload as FileUploadIcon,
  Assessment as AssessmentIcon,
  Restore as RestoreIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import type { AnalysisHistoryItem } from '../utils/stateManager';

interface StateRecoveryProps {
  open: boolean;
  onClose: () => void;
  onRecoverSession: () => void;
  onRecoverResults: () => void;
  onLoadFromHistory: (item: AnalysisHistoryItem) => void;
  onClearAll: () => void;
  recoveryOptions: {
    hasSession: boolean;
    hasResults: boolean;
    hasHistory: boolean;
    lastAnalysisTime: string | null;
  };
  analysisHistory: AnalysisHistoryItem[];
}

export default function StateRecovery({
  open,
  onClose,
  onRecoverSession,
  onRecoverResults,
  onLoadFromHistory,
  onClearAll,
  recoveryOptions,
  analysisHistory,
}: StateRecoveryProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const getModelDisplayName = (model: string): string => {
    const modelNames: Record<string, string> = {
      'first_touch': 'First Touch',
      'last_touch': 'Last Touch',
      'linear': 'Linear',
      'time_decay': 'Time Decay',
      'position_based': 'Position Based',
    };
    return modelNames[model] || model;
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <RestoreIcon color="primary" />
          <Typography variant="h6" component="div">
            Recover Your Work
          </Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ mb: 3 }}>
          <Typography variant="body2" color="text.secondary">
            We found some previous work that you can recover. Choose what you'd like to restore:
          </Typography>
        </Box>

        {/* Current Session Recovery */}
        {recoveryOptions.hasSession && (
          <Card sx={{ mb: 2, border: '1px solid', borderColor: 'primary.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <FileUploadIcon color="primary" />
                <Typography variant="h6" color="primary">
                  Current Session
                </Typography>
                <Chip label="Recent" size="small" color="primary" />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Continue where you left off in your current session
              </Typography>
              <Button
                variant="contained"
                onClick={onRecoverSession}
                startIcon={<RestoreIcon />}
                size="small"
              >
                Recover Session
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Results Recovery */}
        {recoveryOptions.hasResults && (
          <Card sx={{ mb: 2, border: '1px solid', borderColor: 'success.main' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <AssessmentIcon color="success" />
                <Typography variant="h6" color="success.main">
                  Previous Results
                </Typography>
                <Chip 
                  label={recoveryOptions.lastAnalysisTime ? formatDate(recoveryOptions.lastAnalysisTime) : 'Available'} 
                  size="small" 
                  color="success" 
                />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                View your most recent analysis results
              </Typography>
              <Button
                variant="contained"
                color="success"
                onClick={onRecoverResults}
                startIcon={<AssessmentIcon />}
                size="small"
              >
                View Results
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Analysis History */}
        {recoveryOptions.hasHistory && analysisHistory.length > 0 && (
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <HistoryIcon color="action" />
                <Typography variant="h6">
                  Analysis History
                </Typography>
                <Chip label={`${analysisHistory.length} saved`} size="small" />
              </Box>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Load from your previous analyses:
              </Typography>

              <List sx={{ maxHeight: 200, overflow: 'auto' }}>
                {analysisHistory.slice(0, 5).map((item, index) => (
                  <React.Fragment key={item.id}>
                    <ListItem
                      sx={{
                        cursor: 'pointer',
                        borderRadius: 1,
                        '&:hover': { backgroundColor: 'action.hover' }
                      }}
                      onClick={() => onLoadFromHistory(item)}
                    >
                      <ListItemIcon>
                        <AssessmentIcon color="action" />
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2" fontWeight="medium">
                              {item.fileName}
                            </Typography>
                            <Chip 
                              label={getModelDisplayName(item.model)} 
                              size="small" 
                              variant="outlined"
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              {formatDate(item.timestamp)} • {formatFileSize(item.fileSize)}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < Math.min(analysisHistory.length, 5) - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        )}

        {/* No Recovery Options */}
        {!recoveryOptions.hasSession && !recoveryOptions.hasResults && !recoveryOptions.hasHistory && (
          <Alert severity="info" sx={{ mb: 2 }}>
            No previous work found. You can start fresh with a new analysis.
          </Alert>
        )}

        {/* Clear All Option */}
        {(recoveryOptions.hasSession || recoveryOptions.hasResults || recoveryOptions.hasHistory) && (
          <Box sx={{ mt: 3, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Want to start completely fresh?
            </Typography>
            <Button
              variant="outlined"
              color="error"
              onClick={onClearAll}
              startIcon={<ClearIcon />}
              size="small"
            >
              Clear All Data
            </Button>
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Start Fresh
        </Button>
      </DialogActions>
    </Dialog>
  );
}
