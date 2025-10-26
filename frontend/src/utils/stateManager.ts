import type { AttributionResponse, AttributionModel } from '../types/api';

// State interfaces
export interface AppState {
  activeStep: number;
  selectedFile: File | null;
  selectedModel: AttributionModel;
  results: AttributionResponse | null;
  error: string | null;
  loading: boolean;
  lastAnalysisTime: string | null;
  analysisHistory: AnalysisHistoryItem[];
}

export interface AnalysisHistoryItem {
  id: string;
  timestamp: string;
  fileName: string;
  model: AttributionModel;
  results: AttributionResponse;
  fileSize: number;
}

export interface UserPreferences {
  defaultModel: AttributionModel;
  autoSave: boolean;
  showAdvancedOptions: boolean;
  theme: 'light' | 'dark' | 'auto';
}

// Storage keys
const STORAGE_KEYS = {
  APP_STATE: 'rabbit_app_state',
  USER_PREFERENCES: 'rabbit_user_preferences',
  ANALYSIS_HISTORY: 'rabbit_analysis_history',
  SESSION_STATE: 'rabbit_session_state',
} as const;

// Default state
const DEFAULT_APP_STATE: AppState = {
  activeStep: 0,
  selectedFile: null,
  selectedModel: 'linear',
  results: null,
  error: null,
  loading: false,
  lastAnalysisTime: null,
  analysisHistory: [],
};

const DEFAULT_PREFERENCES: UserPreferences = {
  defaultModel: 'linear',
  autoSave: true,
  showAdvancedOptions: false,
  theme: 'light',
};

// Utility functions
export const stateManager = {
  // Save state to localStorage
  saveAppState(state: Partial<AppState>): void {
    try {
      const currentState = this.getAppState();
      const newState = { ...currentState, ...state };
      localStorage.setItem(STORAGE_KEYS.APP_STATE, JSON.stringify(newState));
    } catch (error) {
      console.warn('Failed to save app state:', error);
    }
  },

  // Load state from localStorage
  getAppState(): AppState {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.APP_STATE);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...DEFAULT_APP_STATE, ...parsed };
      }
    } catch (error) {
      console.warn('Failed to load app state:', error);
    }
    return DEFAULT_APP_STATE;
  },

  // Save user preferences
  savePreferences(preferences: Partial<UserPreferences>): void {
    try {
      const currentPrefs = this.getPreferences();
      const newPrefs = { ...currentPrefs, ...preferences };
      localStorage.setItem(STORAGE_KEYS.USER_PREFERENCES, JSON.stringify(newPrefs));
    } catch (error) {
      console.warn('Failed to save preferences:', error);
    }
  },

  // Load user preferences
  getPreferences(): UserPreferences {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.USER_PREFERENCES);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...DEFAULT_PREFERENCES, ...parsed };
      }
    } catch (error) {
      console.warn('Failed to load preferences:', error);
    }
    return DEFAULT_PREFERENCES;
  },

  // Save analysis to history
  saveAnalysisToHistory(analysis: AnalysisHistoryItem): void {
    try {
      const history = this.getAnalysisHistory();
      const newHistory = [analysis, ...history].slice(0, 10); // Keep last 10 analyses
      localStorage.setItem(STORAGE_KEYS.ANALYSIS_HISTORY, JSON.stringify(newHistory));
    } catch (error) {
      console.warn('Failed to save analysis to history:', error);
    }
  },

  // Get analysis history
  getAnalysisHistory(): AnalysisHistoryItem[] {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.ANALYSIS_HISTORY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      console.warn('Failed to load analysis history:', error);
    }
    return [];
  },

  // Save session state (for recovery)
  saveSessionState(state: Partial<AppState>): void {
    try {
      const sessionState = {
        ...state,
        timestamp: new Date().toISOString(),
      };
      sessionStorage.setItem(STORAGE_KEYS.SESSION_STATE, JSON.stringify(sessionState));
    } catch (error) {
      console.warn('Failed to save session state:', error);
    }
  },

  // Get session state
  getSessionState(): Partial<AppState> | null {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEYS.SESSION_STATE);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Check if session is recent (within 1 hour)
        const timestamp = new Date(parsed.timestamp);
        const now = new Date();
        const diffHours = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60);
        
        if (diffHours < 1) {
          return parsed;
        }
      }
    } catch (error) {
      console.warn('Failed to load session state:', error);
    }
    return null;
  },

  // Clear session state
  clearSessionState(): void {
    try {
      sessionStorage.removeItem(STORAGE_KEYS.SESSION_STATE);
    } catch (error) {
      console.warn('Failed to clear session state:', error);
    }
  },

  // Reset all state
  resetAllState(): void {
    try {
      localStorage.removeItem(STORAGE_KEYS.APP_STATE);
      localStorage.removeItem(STORAGE_KEYS.ANALYSIS_HISTORY);
      sessionStorage.removeItem(STORAGE_KEYS.SESSION_STATE);
    } catch (error) {
      console.warn('Failed to reset state:', error);
    }
  },

  // Check if there's recoverable state
  hasRecoverableState(): boolean {
    const sessionState = this.getSessionState();
    const appState = this.getAppState();
    return !!(sessionState || appState.results || appState.analysisHistory.length > 0);
  },

  // Get recovery options
  getRecoveryOptions(): {
    hasSession: boolean;
    hasResults: boolean;
    hasHistory: boolean;
    lastAnalysisTime: string | null;
  } {
    const sessionState = this.getSessionState();
    const appState = this.getAppState();
    
    return {
      hasSession: !!sessionState,
      hasResults: !!appState.results,
      hasHistory: appState.analysisHistory.length > 0,
      lastAnalysisTime: appState.lastAnalysisTime,
    };
  },

  // Create analysis history item
  createAnalysisHistoryItem(
    file: File,
    model: AttributionModel,
    results: AttributionResponse
  ): AnalysisHistoryItem {
    return {
      id: `analysis_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      fileName: file.name,
      model,
      results,
      fileSize: file.size,
    };
  },
};

export default stateManager;
