import { Box, FormControl, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import type { AttributionModel } from '../types/api';

interface ModelSelectorProps {
  value: AttributionModel;
  onChange: (model: AttributionModel) => void;
  disabled?: boolean;
}

const modelDescriptions: Record<AttributionModel, string> = {
  first_touch: '100% credit to first touchpoint. Best for brand awareness campaigns.',
  last_touch: '100% credit to last touchpoint. Best for performance marketing optimization.',
  linear: 'Equal distribution across all touchpoints. Best for general attribution analysis.',
  time_decay: 'Recent touchpoints get more credit. Best for short sales cycles.',
  position_based: '40% first touch, 40% last touch, 20% middle. Best for complex B2B sales cycles.',
};

const modelLabels: Record<AttributionModel, string> = {
  first_touch: 'First Touch',
  last_touch: 'Last Touch',
  linear: 'Linear',
  time_decay: 'Time Decay',
  position_based: 'Position Based',
};

export default function ModelSelector({ value, onChange, disabled = false }: ModelSelectorProps) {
  const handleChange = (event: any) => {
    onChange(event.target.value as AttributionModel);
  };

  return (
    <Box>
      <FormControl fullWidth variant="outlined" disabled={disabled}>
        <InputLabel id="model-select-label">Attribution Model</InputLabel>
        <Select
          labelId="model-select-label"
          id="model-select"
          value={value}
          onChange={handleChange}
          label="Attribution Model"
        >
          {Object.entries(modelLabels).map(([key, label]) => (
            <MenuItem key={key} value={key}>
              <Box>
                <Typography variant="body1">{label}</Typography>
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        {modelDescriptions[value]}
      </Typography>
    </Box>
  );
}
