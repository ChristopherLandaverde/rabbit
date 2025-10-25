import { Box, Paper, Typography } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { AttributionResults } from '../types/api';

interface AttributionChartProps {
  results: AttributionResults;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658'];

export default function AttributionChart({ results }: AttributionChartProps) {
  // Handle different possible data structures
  const channel_attribution = (results as any).channel_attribution || (results as any).channel_attributions || {};
  
  // Check if we have data
  if (!channel_attribution || Object.keys(channel_attribution).length === 0) {
    return (
      <Box>
        <Typography variant="body2" color="text.secondary">
          No attribution data available
        </Typography>
      </Box>
    );
  }

  // Convert data for chart
  const chartData = Object.entries(channel_attribution).map(([name, data]: [string, any]) => ({
    name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: (data.credit || 0) * 100,
    revenue: data.revenue || 0,
    conversions: data.conversions || 0,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const value = typeof data.value === 'number' ? data.value : 0;
      const conversions = data.payload?.conversions || 0;
      const revenue = data.payload?.revenue || 0;
      
      return (
        <Paper sx={{ p: 2 }}>
          <Typography variant="body2" fontWeight="bold">
            {data.name}
          </Typography>
          <Typography variant="caption">Credit: {value.toFixed(1)}%</Typography>
          <br />
          <Typography variant="caption">
            Conversions: {conversions}
          </Typography>
          <br />
          <Typography variant="caption">
            Revenue: ${revenue.toFixed(2)}
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Attribution Credit Distribution
      </Typography>
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
            outerRadius={120}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
}
