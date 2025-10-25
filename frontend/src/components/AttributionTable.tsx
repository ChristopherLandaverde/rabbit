import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  Typography,
  Chip,
} from '@mui/material';
import type { AttributionResults } from '../types/api';

interface AttributionTableProps {
  results: AttributionResults;
}

export default function AttributionTable({ results }: AttributionTableProps) {
  // Handle different possible data structures
  const channel_attribution = (results as any).channel_attribution || (results as any).channel_attributions || {};
  const summary = (results as any).summary || {};
  
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

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Channel Attribution Results
      </Typography>

      <TableContainer component={Paper} sx={{ mt: 2, mb: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Channel</strong></TableCell>
              <TableCell align="right"><strong>Credit (%)</strong></TableCell>
              <TableCell align="right"><strong>Conversions</strong></TableCell>
              <TableCell align="right"><strong>Revenue</strong></TableCell>
              <TableCell align="right"><strong>Confidence</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(channel_attribution).map(([channel, data]: [string, any]) => (
              <TableRow key={channel}>
                <TableCell component="th" scope="row">
                  {channel.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </TableCell>
                <TableCell align="right">
                  {((data.credit || 0) * 100).toFixed(1)}%
                </TableCell>
                <TableCell align="right">{data.conversions || 0}</TableCell>
                <TableCell align="right">
                  ${(data.revenue || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </TableCell>
                <TableCell align="right">
                  <Chip
                    label={`${((data.confidence || 0) * 100).toFixed(0)}%`}
                    size="small"
                    color={(data.confidence || 0) > 0.8 ? 'success' : (data.confidence || 0) > 0.6 ? 'warning' : 'error'}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Total Conversions
          </Typography>
          <Typography variant="h5">{summary.total_conversions || 0}</Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Total Revenue
          </Typography>
          <Typography variant="h5">
            ${(summary.total_revenue || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Avg Journey Length
          </Typography>
          <Typography variant="h5">{(summary.average_journey_length || 0).toFixed(1)}</Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Unique Customers
          </Typography>
          <Typography variant="h5">{summary.unique_customers || 0}</Typography>
        </Paper>
      </Box>
    </Box>
  );
}
