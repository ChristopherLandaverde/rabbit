import { useState, useEffect, useCallback } from 'react';
import { stateManager, type AppState, type UserPreferences, type AnalysisHistoryItem } from '../utils/stateManager';
import type { AttributionResponse, AttributionModel } from '../types/api';

export interface UseAppStateReturn {
  // State
  activeStep: number;
  selectedFile: File | null;
  selectedModel: AttributionModel;
  results: AttributionResponse | null;
  error: string | null;
  loading: boolean;
  lastAnalysisTime: string | null;
  analysisHistory: AnalysisHistoryItem[];
  preferences: UserPreferences;
  
  // Actions
  setActiveStep: (step: number) => void;
  setSelectedFile: (file: File | null) => void;
  setSelectedModel: (model: AttributionModel) => void;
  setResults: (results: AttributionResponse | null) => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
  updatePreferences: (preferences: Partial<UserPreferences>) => void;
  saveAnalysisToHistory: (file: File, model: AttributionModel, results: AttributionResponse) => void;
  loadFromHistory: (historyItem: AnalysisHistoryItem) => void;
  resetState: () => void;
  hasRecoverableState: () => boolean;
  getRecoveryOptions: () => {
    hasSession: boolean;
    hasResults: boolean;
    hasHistory: boolean;
    lastAnalysisTime: string | null;
  };
}

export function useAppState(): UseAppStateReturn {
  // Initialize state from localStorage
  const [state, setState] = useState<AppState>(() => stateManager.getAppState());
  const [preferences, setPreferences] = useState<UserPreferences>(() => stateManager.getPreferences());

  // Auto-save state changes to localStorage
  useEffect(() => {
    stateManager.saveAppState(state);
  }, [state]);

  // Auto-save preferences changes to localStorage
  useEffect(() => {
    stateManager.savePreferences(preferences);
  }, [preferences]);

  // Save session state for recovery
  useEffect(() => {
    if (state.results || state.selectedFile) {
      stateManager.saveSessionState(state);
    }
  }, [state.results, state.selectedFile]);

  // State setters
  const setActiveStep = useCallback((step: number) => {
    setState(prev => ({ ...prev, activeStep: step }));
  }, []);

  const setSelectedFile = useCallback((file: File | null) => {
    setState(prev => ({ 
      ...prev, 
      selectedFile: file,
      error: file ? null : prev.error // Clear error when file is selected
    }));
  }, []);

  const setSelectedModel = useCallback((model: AttributionModel) => {
    setState(prev => ({ ...prev, selectedModel: model }));
  }, []);

  const setResults = useCallback((results: AttributionResponse | null) => {
    setState(prev => ({ 
      ...prev, 
      results,
      lastAnalysisTime: results ? new Date().toISOString() : prev.lastAnalysisTime
    }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }));
  }, []);

  const setLoading = useCallback((loading: boolean) => {
    setState(prev => ({ ...prev, loading }));
  }, []);

  const updatePreferences = useCallback((newPreferences: Partial<UserPreferences>) => {
    setPreferences(prev => ({ ...prev, ...newPreferences }));
  }, []);

  const saveAnalysisToHistory = useCallback((file: File, model: AttributionModel, results: AttributionResponse) => {
    const historyItem = stateManager.createAnalysisHistoryItem(file, model, results);
    setState(prev => ({
      ...prev,
      analysisHistory: [historyItem, ...prev.analysisHistory].slice(0, 10) // Keep last 10
    }));
    stateManager.saveAnalysisToHistory(historyItem);
  }, []);

  const loadFromHistory = useCallback((historyItem: AnalysisHistoryItem) => {
    setState(prev => ({
      ...prev,
      selectedModel: historyItem.model,
      results: historyItem.results,
      activeStep: 2, // Go to results step
      error: null
    }));
  }, []);

  const resetState = useCallback(() => {
    setState({
      activeStep: 0,
      selectedFile: null,
      selectedModel: preferences.defaultModel,
      results: null,
      error: null,
      loading: false,
      lastAnalysisTime: null,
      analysisHistory: state.analysisHistory, // Keep history
    });
    stateManager.clearSessionState();
  }, [preferences.defaultModel, state.analysisHistory]);

  const hasRecoverableState = useCallback(() => {
    return stateManager.hasRecoverableState();
  }, []);

  const getRecoveryOptions = useCallback(() => {
    return stateManager.getRecoveryOptions();
  }, []);

  return {
    // State
    activeStep: state.activeStep,
    selectedFile: state.selectedFile,
    selectedModel: state.selectedModel,
    results: state.results,
    error: state.error,
    loading: state.loading,
    lastAnalysisTime: state.lastAnalysisTime,
    analysisHistory: state.analysisHistory,
    preferences,
    
    // Actions
    setActiveStep,
    setSelectedFile,
    setSelectedModel,
    setResults,
    setError,
    setLoading,
    updatePreferences,
    saveAnalysisToHistory,
    loadFromHistory,
    resetState,
    hasRecoverableState,
    getRecoveryOptions,
  };
}

export default useAppState;
