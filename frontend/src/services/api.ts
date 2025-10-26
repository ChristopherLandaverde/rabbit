import axios from 'axios';
import type { AttributionResponse, ValidationResponse, HealthResponse, AnalysisConfig } from '../types/api';

// API URL configuration for different environments
const getApiBaseUrl = () => {
  // In production Docker environment
  if (import.meta.env.PROD && window.location.hostname !== 'localhost') {
    return window.location.origin.replace(':3000', ':8000');
  }
  
  // Development or localhost
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for file uploads
});

export const attributionApi = {
  // Health check
  async health(): Promise<HealthResponse> {
    const response = await api.get<HealthResponse>('/health');
    return response.data;
  },

  // Validate data
  async validateFile(file: File): Promise<ValidationResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<ValidationResponse>('/attribution/validate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Analyze attribution
  async analyzeAttribution(
    file: File,
    config: AnalysisConfig = {}
  ): Promise<AttributionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    // model_type is required by the API
    formData.append('model_type', config.model || 'linear');
    
    if (config.linking_method) {
      formData.append('linking_method', config.linking_method);
    }
    if (config.attribution_window) {
      formData.append('attribution_window', config.attribution_window.toString());
    }
    if (config.confidence_threshold) {
      formData.append('confidence_threshold', config.confidence_threshold.toString());
    }

    const response = await api.post<AttributionResponse>('/attribution/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          console.log(`Upload progress: ${percentCompleted}%`);
        }
      },
    });
    return response.data;
  },

  // Get available methods
  async getMethods() {
    const response = await api.get('/attribution/methods');
    return response.data;
  },
};

export default attributionApi;
