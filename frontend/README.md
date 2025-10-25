# Multi-Touch Attribution Frontend

Modern React frontend for the Multi-Touch Attribution API built with TypeScript, Material-UI, and Recharts.

## Features

- **File Upload**: Drag-and-drop file upload with validation
- **Model Selection**: Choose from 5 different attribution models
- **Results Visualization**: Interactive charts and data tables
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Loading states and progress indicators

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Material-UI (MUI)** for UI components
- **Recharts** for data visualization
- **Axios** for API communication

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Visit `http://localhost:5173` in your browser.

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── FileUpload.tsx
│   │   ├── ModelSelector.tsx
│   │   ├── AttributionTable.tsx
│   │   └── AttributionChart.tsx
│   ├── services/         # API integration
│   │   └── api.ts
│   ├── types/           # TypeScript types
│   │   └── api.ts
│   └── App.tsx          # Main application
├── public/              # Static assets
└── package.json         # Dependencies
```

## Configuration

Set the API URL in `.env`:

```env
VITE_API_URL=http://localhost:8000
```

## Usage

1. **Upload File**: Drag and drop or click to upload a CSV, JSON, or Parquet file
2. **Select Model**: Choose an attribution model
3. **Analyze**: Click "Run Analysis" to process your data
4. **View Results**: Explore charts, tables, and statistics

## Supported File Formats

- CSV (`.csv`)
- JSON (`.json`)
- Parquet (`.parquet`)

Maximum file size: 100MB

## Attribution Models

- **First Touch**: 100% credit to first touchpoint
- **Last Touch**: 100% credit to last touchpoint
- **Linear**: Equal distribution across all touchpoints
- **Time Decay**: Recent touchpoints get more credit
- **Position Based**: 40% first, 40% last, 20% middle

## License

MIT
