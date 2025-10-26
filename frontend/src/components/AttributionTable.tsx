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
  Tooltip,
} from '@mui/material';
import type { AttributionResults } from '../types/api';

interface AttributionTableProps {
  results: AttributionResults;
  showKPIsOnly?: boolean;
  showTableOnly?: boolean;
}

export default function AttributionTable({ results, showKPIsOnly = false, showTableOnly = false }: AttributionTableProps) {
  // Handle different possible data structures
  const channel_attribution = (results as any).channel_attribution || (results as any).channel_attributions || {};
  
  // Get summary data from the correct location
  const total_conversions = (results as any).total_conversions || 0;
  const total_revenue = (results as any).total_revenue || 0;
  const average_journey_length = (results as any).average_journey_length || 0;
  const unique_customers = (results as any).unique_customers || 0;
  
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

  // If showing KPIs only, return just the score cards
  if (showKPIsOnly) {
    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          Key Performance Indicators
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
            <Tooltip title="The actual number of conversion events that occurred in your dataset. This is the raw count before attribution analysis." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ cursor: 'help' }}>
                Total Conversions
              </Typography>
            </Tooltip>
            <Typography variant="h5">{total_conversions}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mt: 0.5 }}>
              (Actual conversion events in your data)
            </Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
            <Tooltip title="The total revenue generated from all conversion events in your dataset." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ cursor: 'help' }}>
                Total Revenue
              </Typography>
            </Tooltip>
            <Typography variant="h5">
              ${total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
            <Tooltip title="The average number of touchpoints per customer journey in your dataset." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ cursor: 'help' }}>
                Avg Journey Length
              </Typography>
            </Tooltip>
            <Typography variant="h5">{average_journey_length.toFixed(1)}</Typography>
          </Paper>
          <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
            <Tooltip title="The number of unique customers in your dataset who had conversion events." arrow>
              <Typography variant="caption" color="text.secondary" sx={{ cursor: 'help' }}>
                Unique Customers
              </Typography>
            </Tooltip>
            <Typography variant="h5">{unique_customers}</Typography>
          </Paper>
        </Box>
      </Box>
    );
  }

  // If showing table only, return just the table
  if (showTableOnly) {
    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          Channel Attribution Results
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
          💡 These conversions are distributed based on each channel's attribution credit
        </Typography>

        <TableContainer component={Paper} sx={{ mt: 2, mb: 3 }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell><strong>Channel</strong></TableCell>
                <TableCell align="right">
                  <Tooltip title="The percentage of attribution credit assigned to this channel based on the attribution model. Higher credit means this channel played a more important role in driving conversions." arrow>
                    <strong style={{ cursor: 'help' }}>Credit (%)</strong>
                  </Tooltip>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="The number of conversions attributed to this channel. This is calculated by multiplying the channel's credit percentage by the total conversions, then rounding to the nearest whole number." arrow>
                    <div style={{ cursor: 'help' }}>
                      <strong>Conversions</strong>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.7rem' }}>
                        (Attributed)
                      </Typography>
                    </div>
                  </Tooltip>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="The revenue attributed to this channel. Calculated by multiplying the channel's credit percentage by the total revenue." arrow>
                    <strong style={{ cursor: 'help' }}>Revenue</strong>
                  </Tooltip>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="A confidence score (0-100%) indicating how reliable the attribution results are for this channel. Higher confidence means the attribution is more certain." arrow>
                    <strong style={{ cursor: 'help' }}>Confidence</strong>
                  </Tooltip>
                </TableCell>
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
              {/* Summary row */}
              <TableRow sx={{ backgroundColor: 'grey.50', fontWeight: 'bold' }}>
                <TableCell component="th" scope="row">
                  <strong>Total Attributed</strong>
                </TableCell>
                <TableCell align="right">
                  <strong>100.0%</strong>
                </TableCell>
                <TableCell align="right">
                  <strong>
                    {Object.values(channel_attribution).reduce((sum, data: any) => sum + (data.conversions || 0), 0)}
                  </strong>
                </TableCell>
                <TableCell align="right">
                  <strong>
                    ${Object.values(channel_attribution).reduce((sum, data: any) => sum + (data.revenue || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </strong>
                </TableCell>
                <TableCell align="right">
                  <strong>
                    {Object.values(channel_attribution).length > 0 
                      ? `${(Object.values(channel_attribution).reduce((sum, data: any) => sum + (data.confidence || 0), 0) / Object.values(channel_attribution).length * 100).toFixed(0)}%`
                      : '0%'
                    }
                  </strong>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    );
  }

  // Default: show both (for backward compatibility)
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
              <TableCell align="right">
                <strong>Conversions</strong>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.7rem' }}>
                  (Attributed)
                </Typography>
              </TableCell>
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
            {/* Summary row */}
            <TableRow sx={{ backgroundColor: 'grey.50', fontWeight: 'bold' }}>
              <TableCell component="th" scope="row">
                <strong>Total Attributed</strong>
              </TableCell>
              <TableCell align="right">
                <strong>100.0%</strong>
              </TableCell>
              <TableCell align="right">
                <strong>
                  {Object.values(channel_attribution).reduce((sum, data: any) => sum + (data.conversions || 0), 0)}
                </strong>
              </TableCell>
              <TableCell align="right">
                <strong>
                  ${Object.values(channel_attribution).reduce((sum, data: any) => sum + (data.revenue || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </TableCell>
              <TableCell align="right">
                <strong>
                  {Object.values(channel_attribution).length > 0 
                    ? `${(Object.values(channel_attribution).reduce((sum, data: any) => sum + (data.confidence || 0), 0) / Object.values(channel_attribution).length * 100).toFixed(0)}%`
                    : '0%'
                  }
                </strong>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Total Conversions
          </Typography>
          <Typography variant="h5">{total_conversions}</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mt: 0.5 }}>
            (Actual conversion events)
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Total Revenue
          </Typography>
          <Typography variant="h5">
            ${total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Avg Journey Length
          </Typography>
          <Typography variant="h5">{average_journey_length.toFixed(1)}</Typography>
        </Paper>
        <Paper sx={{ p: 2, flex: 1, minWidth: 200 }}>
          <Typography variant="caption" color="text.secondary">
            Unique Customers
          </Typography>
          <Typography variant="h5">{unique_customers}</Typography>
        </Paper>
      </Box>
    </Box>
  );
}
