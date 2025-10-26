import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Switch,
  Select,
  MenuItem,
  InputLabel,
  Divider,
  Alert,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Save as SaveIcon,
  Restore as RestoreIcon,
} from '@mui/icons-material';
import type { UserPreferences, AttributionModel } from '../types/api';

interface SettingsProps {
  open: boolean;
  onClose: () => void;
  preferences: UserPreferences;
  onSavePreferences: (preferences: Partial<UserPreferences>) => void;
  onResetSettings: () => void;
}

export default function Settings({
  open,
  onClose,
  preferences,
  onSavePreferences,
  onResetSettings,
}: SettingsProps) {
  const [tempPreferences, setTempPreferences] = React.useState<UserPreferences>(preferences);

  React.useEffect(() => {
    setTempPreferences(preferences);
  }, [preferences]);

  const handleSave = () => {
    onSavePreferences(tempPreferences);
    onClose();
  };

  const handleReset = () => {
    onResetSettings();
    onClose();
  };

  const handlePreferenceChange = (key: keyof UserPreferences, value: any) => {
    setTempPreferences(prev => ({ ...prev, [key]: value }));
  };

  const getModelDisplayName = (model: AttributionModel): string => {
    const modelNames: Record<AttributionModel, string> = {
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
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SettingsIcon color="primary" />
          <Typography variant="h6" component="div">
            Settings & Preferences
          </Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {/* Default Model */}
        <Box sx={{ mb: 3 }}>
          <FormControl fullWidth>
            <InputLabel>Default Attribution Model</InputLabel>
            <Select
              value={tempPreferences.defaultModel}
              onChange={(e) => handlePreferenceChange('defaultModel', e.target.value)}
              label="Default Attribution Model"
            >
              <MenuItem value="first_touch">{getModelDisplayName('first_touch')}</MenuItem>
              <MenuItem value="last_touch">{getModelDisplayName('last_touch')}</MenuItem>
              <MenuItem value="linear">{getModelDisplayName('linear')}</MenuItem>
              <MenuItem value="time_decay">{getModelDisplayName('time_decay')}</MenuItem>
              <MenuItem value="position_based">{getModelDisplayName('position_based')}</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            This model will be pre-selected when you start a new analysis
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Auto-save Settings */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Data Persistence
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant="body2" fontWeight="medium">
                Auto-save Progress
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Automatically save your work as you go
              </Typography>
            </Box>
            <Switch
              checked={tempPreferences.autoSave}
              onChange={(e) => handlePreferenceChange('autoSave', e.target.checked)}
            />
          </Box>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* UI Preferences */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Interface
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Box>
              <Typography variant="body2" fontWeight="medium">
                Show Advanced Options
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Display additional configuration options
              </Typography>
            </Box>
            <Switch
              checked={tempPreferences.showAdvancedOptions}
              onChange={(e) => handlePreferenceChange('showAdvancedOptions', e.target.checked)}
            />
          </Box>

          <FormControl fullWidth>
            <InputLabel>Theme</InputLabel>
            <Select
              value={tempPreferences.theme}
              onChange={(e) => handlePreferenceChange('theme', e.target.value)}
              label="Theme"
            >
              <MenuItem value="light">Light</MenuItem>
              <MenuItem value="dark">Dark</MenuItem>
              <MenuItem value="auto">Auto (System)</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Data Management */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Data Management
          </Typography>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            Your analysis history and preferences are stored locally in your browser. 
            Clear this data if you want to start fresh.
          </Alert>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>
          Cancel
        </Button>
        <Button 
          onClick={handleReset}
          color="error"
          startIcon={<RestoreIcon />}
        >
          Reset Settings
        </Button>
        <Button 
          onClick={handleSave}
          variant="contained"
          startIcon={<SaveIcon />}
        >
          Save Settings
        </Button>
      </DialogActions>
    </Dialog>
  );
}
